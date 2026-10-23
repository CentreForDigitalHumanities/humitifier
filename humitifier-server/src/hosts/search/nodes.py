"""AST node definitions for search query expressions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Union

from .constants import Cardinality, FieldKind, LogicalOperator, ValueType
from .types import SearchableField

if TYPE_CHECKING:
    from .functions.base import SearchFunction
    from .operators import ComparisonOperator


@dataclass(frozen=True)
class ExprType:
    """Type specification of an expression (value type and cardinality)."""

    value_type: ValueType
    cardinality: Cardinality


class Node:
    """Base AST node carrying source position."""

    position: int


class Expr(Node):
    """Base class for value-producing expressions."""

    @property
    def expr_type(self) -> ExprType:
        raise NotImplementedError


@dataclass(frozen=True)
class FieldRef(Expr):
    """Reference to a SearchableField."""

    field: SearchableField
    position: int = 0

    @property
    def expr_type(self) -> ExprType:
        cardinality = (
            Cardinality.ELEMENTS
            if self.field.kind == FieldKind.ARRAY
            else Cardinality.SINGLE
        )
        return ExprType(self.field.value_type, cardinality)


@dataclass(frozen=True)
class Literal(Expr):
    """Literal constant value (string, integer, boolean)."""

    value: Any
    value_type: ValueType
    position: int = 0

    @property
    def expr_type(self) -> ExprType:
        return ExprType(self.value_type, Cardinality.SINGLE)


@dataclass(frozen=True)
class FunctionCall(Expr):
    """Function call expression."""

    function: type[SearchFunction]
    args: tuple[Expr, ...]
    position: int = 0

    @property
    def expr_type(self) -> ExprType:
        return self.function.return_type(self.args)


class BoolExpr(Node):
    """Base class for boolean conditions."""

    pass


@dataclass(frozen=True)
class Comparison(BoolExpr):
    """Comparison between an expression, an operator, and a literal."""

    lhs: Expr
    operator: type[ComparisonOperator]
    rhs: Literal
    position: int = 0


@dataclass(frozen=True)
class Logical(BoolExpr):
    """Logical conjunction (AND) or disjunction (OR) of boolean expressions."""

    operator: LogicalOperator
    children: tuple[BoolNode, ...]
    position: int = 0


BoolNode = Union[Comparison, Logical, FunctionCall]
