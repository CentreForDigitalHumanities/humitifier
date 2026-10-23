"""Self-registering comparison operator classes and operator registry."""

from __future__ import annotations

from typing import Any, ClassVar

from .constants import ValueType
from .sql import SqlFragment


class ComparisonOperator:
    """Base class for search comparison operators."""

    abstract: ClassVar[bool] = True
    symbol: ClassVar[str]
    keyword: ClassVar[bool] = False
    description: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.__dict__.get("abstract", False):
            operator_registry.register(cls)

    @classmethod
    def to_lookup(cls, value_type: ValueType) -> str:
        """Return the Django ORM lookup name (e.g. 'iexact', 'gt')."""
        raise NotImplementedError

    @classmethod
    def to_sql(cls, lhs: SqlFragment, rhs: Any, value_type: ValueType) -> SqlFragment:
        """Compile comparison to a SqlFragment."""
        raise NotImplementedError


class _OperatorRegistry:
    """Registry of comparison operators."""

    def __init__(self) -> None:
        self._operators: dict[str, type[ComparisonOperator]] = {}

    def register(self, op_cls: type[ComparisonOperator]) -> None:
        self._operators[op_cls.symbol.upper()] = op_cls

    def unregister(self, op_cls: type[ComparisonOperator]) -> None:
        self._operators.pop(op_cls.symbol.upper(), None)

    def get(self, symbol: str) -> type[ComparisonOperator] | None:
        return self._operators.get(symbol.upper())

    def all(self) -> list[type[ComparisonOperator]]:
        return list(self._operators.values())


operator_registry = _OperatorRegistry()


class Equals(ComparisonOperator):
    symbol = "="
    keyword = False
    description = "equals (case-insensitive for strings)"

    @classmethod
    def to_lookup(cls, value_type: ValueType) -> str:
        if value_type == ValueType.STRING:
            return "iexact"
        return "exact"

    @classmethod
    def to_sql(cls, lhs: SqlFragment, rhs: Any, value_type: ValueType) -> SqlFragment:
        if value_type == ValueType.STRING:
            return SqlFragment(f"LOWER({lhs.sql}) = LOWER(%s)", lhs.params + (str(rhs),))
        val = str(rhs).lower() if isinstance(rhs, bool) else rhs
        return SqlFragment(f"{lhs.sql} = %s", lhs.params + (val,))


class GreaterThan(ComparisonOperator):
    symbol = ">"
    keyword = False
    description = "greater than"

    @classmethod
    def to_lookup(cls, value_type: ValueType) -> str:
        return "gt"

    @classmethod
    def to_sql(cls, lhs: SqlFragment, rhs: Any, value_type: ValueType) -> SqlFragment:
        return SqlFragment(f"{lhs.sql} > %s", lhs.params + (rhs,))


class GreaterOrEqual(ComparisonOperator):
    symbol = ">="
    keyword = False
    description = "greater than or equal"

    @classmethod
    def to_lookup(cls, value_type: ValueType) -> str:
        return "gte"

    @classmethod
    def to_sql(cls, lhs: SqlFragment, rhs: Any, value_type: ValueType) -> SqlFragment:
        return SqlFragment(f"{lhs.sql} >= %s", lhs.params + (rhs,))


class LessThan(ComparisonOperator):
    symbol = "<"
    keyword = False
    description = "less than"

    @classmethod
    def to_lookup(cls, value_type: ValueType) -> str:
        return "lt"

    @classmethod
    def to_sql(cls, lhs: SqlFragment, rhs: Any, value_type: ValueType) -> SqlFragment:
        return SqlFragment(f"{lhs.sql} < %s", lhs.params + (rhs,))


class LessOrEqual(ComparisonOperator):
    symbol = "<="
    keyword = False
    description = "less than or equal"

    @classmethod
    def to_lookup(cls, value_type: ValueType) -> str:
        return "lte"

    @classmethod
    def to_sql(cls, lhs: SqlFragment, rhs: Any, value_type: ValueType) -> SqlFragment:
        return SqlFragment(f"{lhs.sql} <= %s", lhs.params + (rhs,))


class Contains(ComparisonOperator):
    symbol = "CONTAINS"
    keyword = True
    description = "substring match (case-insensitive)"

    @classmethod
    def to_lookup(cls, value_type: ValueType) -> str:
        return "icontains"

    @classmethod
    def to_sql(cls, lhs: SqlFragment, rhs: Any, value_type: ValueType) -> SqlFragment:
        return SqlFragment(f"{lhs.sql} ILIKE %s", lhs.params + (f"%{rhs}%",))
