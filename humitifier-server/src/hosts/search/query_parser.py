"""Query parser for converting query strings into ComplexQuery objects."""

from __future__ import annotations

from typing import Any

from .field_discovery import get_searchable_fields
from .types import AggregationFunction, ComplexQuery, ComparisonOperator, SearchCriterion


def parse_query(query_string: str) -> ComplexQuery:
    """
    Parse a query string into a ComplexQuery object.

    Supported syntax:
    - Basic: field_id = "value"
    - Operators: =, >, >=, <, <=, contains
    - Logical operators: AND, OR
    - Brackets for grouping: {expr}
    - Quoted strings: "value" or 'value'
    - Unquoted values for numbers and booleans: 42, true, false
    - Aggregations for array fields: min(field[]), max(field[]), sum(field[]), concat(field[]), count(field[])
    - Filters for array fields: filter(field[], "pattern")

    Examples:
        - 'facts.cpu.count = 4'
        - 'facts.os.name = "Ubuntu" AND facts.cpu.count >= 4'
        - '{facts.os.name = "Ubuntu" OR facts.os.name = "Debian"} AND facts.cpu.count > 2'
        - 'facts.hostname contains "web"'
        - 'count(facts.packages[].name) > 100'
        - 'max(facts.memory[].size) >= 8192'
        - 'filter(facts.packages[].name, "^lib") contains "ssl"'
        - 'count(filter(facts.services[].name, "ssh")) > 0'

    Args:
        query_string: The query string to parse.

    Returns:
        A ComplexQuery object representing the parsed query.

    Raises:
        ValueError: If the query string is invalid, cannot be parsed, or contains invalid field IDs.
    """
    # Get allowed field IDs
    allowed_fields = {field.id for field in get_searchable_fields()}

    tokens = _tokenize(query_string)
    parser = _QueryParser(tokens, allowed_fields)
    return parser.parse()


def _tokenize(query_string: str) -> list[str]:
    """
    Tokenize a query string into a list of tokens.

    Handles quoted strings, operators, brackets, and identifiers.
    """
    tokens = []
    i = 0
    length = len(query_string)

    while i < length:
        char = query_string[i]

        # Skip whitespace
        if char.isspace():
            i += 1
            continue

        # Handle quoted strings
        if char in ('"', "'"):
            quote_char = char
            i += 1
            start = i
            while i < length and query_string[i] != quote_char:
                if query_string[i] == '\\' and i + 1 < length:
                    i += 2  # Skip escaped character
                else:
                    i += 1
            if i >= length:
                raise ValueError(f"Unterminated string starting at position {start - 1}")
            tokens.append(query_string[start:i])
            i += 1  # Skip closing quote
            continue

        # Handle brackets, parentheses, and commas
        if char in ('{', '}', '(', ')', ','):
            tokens.append(char)
            i += 1
            continue

        # Handle operators (=, >, >=, <, <=)
        if char in ('=', '>', '<'):
            start = i
            i += 1
            if i < length and query_string[i] == '=':
                i += 1
            tokens.append(query_string[start:i])
            continue

        # Handle identifiers and keywords
        IDENTIFIER_CHARS = ('_', '.', '[', ']')
        if char.isalnum() or char in IDENTIFIER_CHARS:
            start = i
            while i < length and (query_string[i].isalnum() or query_string[i] in IDENTIFIER_CHARS):
                i += 1
            token = query_string[start:i]

            # Check for aggregation functions and filter
            if token.lower() in ('min', 'max', 'sum', 'concat', 'count', 'filter'):
                tokens.append(token.lower())
            else:
                tokens.append(token)
            continue

        raise ValueError(f"Unexpected character '{char}' at position {i}")

    return tokens


class _QueryParser:
    """
    Recursive descent parser for query strings.

    Grammar:
        query := or_expr
        or_expr := and_expr (OR and_expr)*
        and_expr := primary (AND primary)*
        primary := "{" or_expr "}" | criterion
        criterion := [aggregation "("] [filter_expr] [")"] operator value
        filter_expr := ["filter" "("] field_id ["," pattern ")"]
        aggregation := "min" | "max" | "sum" | "concat" | "count"
        operator := "=" | ">" | ">=" | "<" | "<=" | "contains"
    """

    def __init__(self, tokens: list[str], allowed_fields: set[str]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.allowed_fields = allowed_fields

    def parse(self) -> ComplexQuery:
        """Parse the token stream into a ComplexQuery."""
        if not self.tokens:
            raise ValueError("Empty query string")
        result = self._parse_or_expr()
        if self.pos < len(self.tokens):
            raise ValueError(f"Unexpected token: {self.tokens[self.pos]}")
        return result

    def _current_token(self) -> str | None:
        """Get the current token without consuming it."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _consume_token(self) -> str:
        """Consume and return the current token."""
        if self.pos >= len(self.tokens):
            raise ValueError("Unexpected end of query")
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _parse_or_expr(self) -> ComplexQuery:
        """Parse OR expressions (lowest precedence)."""
        left = self._parse_and_expr()

        children = [left]
        while self._current_token() == "OR":
            self._consume_token()  # Consume "OR"
            children.append(self._parse_and_expr())

        if len(children) == 1:
            return children[0]
        return ComplexQuery(type="or", children=children)

    def _parse_and_expr(self) -> ComplexQuery:
        """Parse AND expressions (higher precedence than OR)."""
        left = self._parse_primary()

        children = [left]
        while self._current_token() == "AND":
            self._consume_token()  # Consume "AND"
            children.append(self._parse_primary())

        if len(children) == 1:
            return children[0]
        return ComplexQuery(type="and", children=children)

    def _parse_primary(self) -> ComplexQuery:
        """Parse primary expressions (bracketed expressions or criteria)."""
        token = self._current_token()

        if token == "{":
            self._consume_token()  # Consume "{"
            result = self._parse_or_expr()
            if self._current_token() != "}":
                raise ValueError("Expected closing bracket")
            self._consume_token()  # Consume "}"
            return result

        return self._parse_criterion()

    def _parse_criterion(self) -> ComplexQuery:
        """Parse a single criterion (field operator value) with optional aggregation and filter."""
        # Check if we have an aggregation function
        aggregation = None
        filter_pattern = None
        first_token = self._current_token()

        if first_token and first_token.lower() in ('min', 'max', 'sum', 'concat', 'count'):
            aggregation = first_token.lower()
            self._consume_token()  # Consume aggregation function

            # Expect opening parenthesis
            if self._current_token() != '(':
                raise ValueError(f"Expected '(' after aggregation function '{aggregation}'")
            self._consume_token()  # Consume '('

            # Check if next token is 'filter'
            if self._current_token() == 'filter':
                self._consume_token()  # Consume 'filter'

                # Expect opening parenthesis
                if self._current_token() != '(':
                    raise ValueError("Expected '(' after 'filter'")
                self._consume_token()  # Consume '('

                # Parse field_id
                field_id = self._consume_token()

                # Validate that the field_id is allowed
                if field_id not in self.allowed_fields:
                    raise ValueError(f"Invalid field ID: '{field_id}'. Not a searchable field.")

                # Expect comma
                if self._current_token() != ',':
                    raise ValueError("Expected ',' after field in filter")
                self._consume_token()  # Consume ','

                # Parse pattern (must be a string)
                pattern_token = self._consume_token()
                filter_pattern = self._parse_literal_value(pattern_token)

                # Expect closing parenthesis for filter
                if self._current_token() != ')':
                    raise ValueError("Expected ')' after pattern in filter")
                self._consume_token()  # Consume ')'
            else:
                # No filter, just parse field_id
                field_id = self._consume_token()

                # Validate that the field_id is allowed
                if field_id not in self.allowed_fields:
                    raise ValueError(f"Invalid field ID: '{field_id}'. Not a searchable field.")

            # Expect closing parenthesis for aggregation
            if self._current_token() != ')':
                raise ValueError(f"Expected ')' after aggregation content")
            self._consume_token()  # Consume ')'

        elif first_token == 'filter':
            # Standalone filter without aggregation
            self._consume_token()  # Consume 'filter'

            # Expect opening parenthesis
            if self._current_token() != '(':
                raise ValueError("Expected '(' after 'filter'")
            self._consume_token()  # Consume '('

            # Parse field_id
            field_id = self._consume_token()

            # Validate that the field_id is allowed
            if field_id not in self.allowed_fields:
                raise ValueError(f"Invalid field ID: '{field_id}'. Not a searchable field.")

            # Expect comma
            if self._current_token() != ',':
                raise ValueError("Expected ',' after field in filter")
            self._consume_token()  # Consume ','

            # Parse pattern (must be a string)
            pattern_token = self._consume_token()
            filter_pattern = self._parse_literal_value(pattern_token)

            # Expect closing parenthesis
            if self._current_token() != ')':
                raise ValueError("Expected ')' after pattern in filter")
            self._consume_token()  # Consume ')'
        else:
            # No aggregation or filter, just parse field_id
            field_id = self._consume_token()

            # Validate that the field_id is allowed
            if field_id not in self.allowed_fields:
                raise ValueError(f"Invalid field ID: '{field_id}'. Not a searchable field.")

        operator_token = self._consume_token()
        operator = self._parse_operator(operator_token)

        value_token = self._consume_token()
        value = self._parse_literal_value(value_token)

        criterion = SearchCriterion(
            field_id=field_id,
            operator=operator,
            value=value,
            aggregation=aggregation,  # type: ignore[arg-type]
            filter_pattern=filter_pattern,
        )
        return ComplexQuery(type="criterion", criterion=criterion)

    def _parse_operator(self, token: str) -> ComparisonOperator:
        """Parse an operator token into a ComparisonOperator."""
        operator_map = {
            "=": "eq",
            ">": "gt",
            ">=": "gte",
            "<": "lt",
            "<=": "lte",
            "contains": "contains",
        }
        operator = operator_map.get(token)
        if operator is None:
            raise ValueError(f"Invalid operator: {token}")
        return operator  # type: ignore[return-value]

    def _parse_literal_value(self, token: str) -> Any:
        """Parse a literal value (string, number, or boolean)."""
        # Try to parse as boolean
        if token.lower() == "true":
            return True
        if token.lower() == "false":
            return False

        # Try to parse as integer
        try:
            return int(token)
        except ValueError:
            pass

        # Try to parse as float
        try:
            return float(token)
        except ValueError:
            pass

        # Return as string
        return token
