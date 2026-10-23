"""Generic recursive-descent parser for search queries producing a typed AST."""

from __future__ import annotations

from typing import Iterable

from .constants import LogicalOperator, TokenType, ValueType
from .field_discovery import get_searchable_fields
from .functions import function_registry
from .lexer import Token, tokenize
from .nodes import (
    BoolNode,
    Comparison,
    Expr,
    FieldRef,
    FunctionCall,
    Literal,
    Logical,
)
from .operators import NotEquals, operator_registry
from .types import SearchableField


class _Parser:
    """Internal recursive-descent parser."""

    def __init__(
        self, tokens: list[Token], fields_by_id: dict[str, SearchableField]
    ) -> None:
        self.tokens = tokens
        self.pos = 0
        self.fields = fields_by_id

    def current(self) -> Token | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek(self, offset: int = 1) -> Token | None:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return None

    def advance(self) -> Token:
        tok = self.current()
        if tok is None:
            raise ValueError("Unexpected end of query")
        self.pos += 1
        return tok

    def match(self, token_type: TokenType) -> Token | None:
        tok = self.current()
        if tok is not None and tok.type == token_type:
            self.pos += 1
            return tok
        return None

    def expect(self, token_type: TokenType, error_message: str) -> Token:
        tok = self.current()
        if tok is None or tok.type != token_type:
            pos = tok.position if tok is not None else (self.tokens[-1].position + 1 if self.tokens else 0)
            raise ValueError(f"{error_message} at position {pos}")
        self.pos += 1
        return tok

    def parse(self) -> BoolNode:
        result = self.parse_or()
        if self.pos < len(self.tokens):
            tok = self.tokens[self.pos]
            raise ValueError(
                f"Unexpected token '{tok.value}' at position {tok.position}"
            )
        return result

    def parse_or(self) -> BoolNode:
        left = self.parse_and()
        children = [left]

        while (
            self.current() is not None
            and self.current().type == TokenType.LOGICAL
            and self.current().value == LogicalOperator.OR
        ):
            self.advance()
            children.append(self.parse_and())

        if len(children) > 1:
            return Logical(
                operator=LogicalOperator.OR,
                children=tuple(children),
                position=children[0].position,
            )
        return left

    def parse_and(self) -> BoolNode:
        left = self.parse_not()
        children = [left]

        while (
            self.current() is not None
            and self.current().type == TokenType.LOGICAL
            and self.current().value == LogicalOperator.AND
        ):
            self.advance()
            children.append(self.parse_not())

        if len(children) > 1:
            return Logical(
                operator=LogicalOperator.AND,
                children=tuple(children),
                position=children[0].position,
            )
        return left

    def parse_not(self) -> BoolNode:
        tok = self.current()
        if (
            tok is not None
            and tok.type == TokenType.LOGICAL
            and tok.value == LogicalOperator.NOT
        ):
            self.advance()
            child = self.parse_not()
            return Logical(
                operator=LogicalOperator.NOT,
                children=(child,),
                position=tok.position,
            )
        return self.parse_factor()

    def parse_factor(self) -> BoolNode:
        tok = self.current()
        if tok is not None and tok.type == TokenType.LBRACE:
            lbrace = self.advance()
            inner = self.parse_or()
            self.expect(
                TokenType.RBRACE, f"Unclosed '{{' starting at position {lbrace.position}"
            )
            return inner

        return self.parse_condition()

    def parse_condition(self) -> BoolNode:
        lhs = self.parse_expr()
        next_tok = self.current()

        negated = False
        negated_pos = 0
        if (
            next_tok is not None
            and next_tok.type == TokenType.LOGICAL
            and next_tok.value == LogicalOperator.NOT
        ):
            neg_tok = self.advance()
            negated = True
            negated_pos = neg_tok.position
            next_tok = self.current()

        if next_tok is not None and next_tok.type == TokenType.OPERATOR:
            op_tok = self.advance()
            op_cls = operator_registry.get(str(op_tok.value))
            if op_cls is None:
                raise ValueError(
                    f"Unknown operator '{op_tok.value}' at position {op_tok.position}"
                )

            rhs = self.parse_literal()

            lhs_type = lhs.expr_type.value_type
            rhs_type = rhs.value_type
            if lhs_type != rhs_type:
                raise ValueError(
                    f"Type mismatch: cannot compare {lhs_type.value} with {rhs_type.value} at position {rhs.position}"
                )

            if op_cls.symbol == "CONTAINS" and lhs_type != ValueType.STRING:
                raise ValueError(
                    f"CONTAINS operator requires string type at position {op_tok.position}"
                )

            comp = Comparison(
                lhs=lhs,
                operator=op_cls,
                rhs=rhs,
                position=lhs.position,
            )
            if negated:
                return Logical(
                    operator=LogicalOperator.NOT,
                    children=(comp,),
                    position=negated_pos,
                )
            return comp

        if negated:
            if next_tok is not None and next_tok.type in (
                TokenType.STRING,
                TokenType.NUMBER,
                TokenType.BOOLEAN,
            ):
                rhs = self.parse_literal()
                lhs_type = lhs.expr_type.value_type
                rhs_type = rhs.value_type
                if lhs_type != rhs_type:
                    raise ValueError(
                        f"Type mismatch: cannot compare {lhs_type.value} with {rhs_type.value} at position {rhs.position}"
                    )
                return Comparison(
                    lhs=lhs,
                    operator=NotEquals,
                    rhs=rhs,
                    position=lhs.position,
                )
            raise ValueError(
                f"Expected comparison operator after NOT at position {negated_pos}"
            )

        # Standalone predicate function call
        from .constants import Cardinality

        if (
            isinstance(lhs, FunctionCall)
            and lhs.expr_type.value_type == ValueType.BOOLEAN
            and lhs.expr_type.cardinality == Cardinality.SINGLE
        ):
            return lhs

        pos = next_tok.position if next_tok else lhs.position
        raise ValueError(
            f"Expected comparison operator after expression at position {pos}"
        )

    def parse_expr(self) -> Expr:
        tok = self.current()
        if tok is None:
            raise ValueError("Unexpected end of query")

        if tok.type == TokenType.IDENT:
            peek_tok = self.peek(1)
            if peek_tok is not None and peek_tok.type == TokenType.LPAREN:
                return self.parse_function_call()
            return self.parse_field_ref()

        raise ValueError(
            f"Expected field or function call at position {tok.position}"
        )

    def parse_function_call(self) -> FunctionCall:
        id_tok = self.advance()
        func_cls = function_registry.get(str(id_tok.value))
        if func_cls is None:
            raise ValueError(
                f"Unknown function '{id_tok.value}' at position {id_tok.position}"
            )

        self.expect(
            TokenType.LPAREN,
            f"Expected '(' after function name at position {id_tok.position}",
        )
        args: list[Expr] = []

        if self.match(TokenType.RPAREN) is None:
            while True:
                args.append(self.parse_expr_arg())
                if self.match(TokenType.COMMA) is not None:
                    continue
                elif self.match(TokenType.RPAREN) is not None:
                    break
                else:
                    curr = self.current()
                    pos = curr.position if curr else id_tok.position
                    raise ValueError(f"Expected ',' or ')' at position {pos}")

        func_cls.validate(tuple(args))
        return FunctionCall(
            function=func_cls,
            args=tuple(args),
            position=id_tok.position,
        )

    def parse_field_ref(self) -> FieldRef:
        id_tok = self.advance()
        field_id = str(id_tok.value)
        if field_id not in self.fields:
            raise ValueError(
                f"Unknown field '{field_id}' at position {id_tok.position}"
            )
        return FieldRef(field=self.fields[field_id], position=id_tok.position)

    def parse_expr_arg(self) -> Expr:
        tok = self.current()
        if tok is None:
            raise ValueError("Unexpected end of query in function arguments")

        if tok.type in (TokenType.STRING, TokenType.NUMBER, TokenType.BOOLEAN):
            return self.parse_literal()

        if tok.type == TokenType.IDENT:
            peek_tok = self.peek(1)
            if peek_tok is not None and peek_tok.type == TokenType.LPAREN:
                return self.parse_function_call()
            return self.parse_field_ref()

        raise ValueError(
            f"Unexpected token '{tok.value}' in function argument at position {tok.position}"
        )

    def parse_literal(self) -> Literal:
        tok = self.current()
        if tok is None:
            pos = self.tokens[-1].position + 1 if self.tokens else 0
            raise ValueError(f"Expected literal value at position {pos}")

        self.advance()
        if tok.type == TokenType.STRING:
            return Literal(tok.value, ValueType.STRING, tok.position)
        if tok.type == TokenType.NUMBER:
            return Literal(tok.value, ValueType.INTEGER, tok.position)
        if tok.type == TokenType.BOOLEAN:
            return Literal(tok.value, ValueType.BOOLEAN, tok.position)

        raise ValueError(f"Expected literal value at position {tok.position}")


def parse_query(
    query_string: str | None,
    fields: Iterable[SearchableField] | None = None,
) -> BoolNode | None:
    """Parse a search query string into an AST.

    Args:
        query_string: The query string to parse, or None/empty for no query.
        fields: Optional collection of SearchableField descriptors to validate against.
                Defaults to get_searchable_fields().

    Returns:
        The root BoolNode of the parsed query AST, or None if the query is empty.

    Raises:
        ValueError: On lexer or parser errors (syntax, unknown fields/functions, type mismatches).
    """
    if not query_string or not query_string.strip():
        return None

    tokens = tokenize(query_string)
    if not tokens:
        return None

    fields_by_id = {f.id: f for f in (fields if fields is not None else get_searchable_fields())}
    parser = _Parser(tokens, fields_by_id)
    return parser.parse()
