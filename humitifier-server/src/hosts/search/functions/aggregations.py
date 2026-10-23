"""Array aggregation search functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..constants import Cardinality, ValueType
from ..sql import ScalarSql, SqlFragment
from .base import Param, ParamKind, SearchFunction

if TYPE_CHECKING:
    from ..nodes import Expr, ExprType
    from ..sql import CompileContext


class Min(SearchFunction):
    """Minimum value aggregation for integer array fields."""

    name = "min"
    description = "minimum value (integer fields)"
    examples = ("min(facts.generic.Hardware.memory[].size) >= 4000000000",)
    params = (
        Param(
            "field",
            ParamKind.FIELD,
            frozenset({ValueType.INTEGER}),
            Cardinality.ELEMENTS,
        ),
    )

    @classmethod
    def return_type(cls, args: tuple[Expr, ...]) -> ExprType:
        from ..nodes import ExprType

        return ExprType(ValueType.INTEGER, Cardinality.SINGLE)

    @classmethod
    def compile(cls, args: tuple[Expr, ...], ctx: CompileContext) -> ScalarSql:
        elem_set = ctx.to_element_set(args[0])
        from_clause = elem_set.source.from_clause
        where_parts = [elem_set.source.type_check] + list(elem_set.conditions)
        where_joined = SqlFragment.join(" AND ", where_parts)

        sql = f"SELECT MIN(({elem_set.value.sql})::numeric) FROM {from_clause.sql} WHERE {where_joined.sql}"
        params = elem_set.value.params + from_clause.params + where_joined.params
        return ScalarSql(SqlFragment(f"({sql})", params), ValueType.INTEGER)


class Max(SearchFunction):
    """Maximum value aggregation for integer array fields."""

    name = "max"
    description = "maximum value (integer fields)"
    examples = ("max(facts.generic.Hardware.memory[].size) >= 4000000000",)
    params = (
        Param(
            "field",
            ParamKind.FIELD,
            frozenset({ValueType.INTEGER}),
            Cardinality.ELEMENTS,
        ),
    )

    @classmethod
    def return_type(cls, args: tuple[Expr, ...]) -> ExprType:
        from ..nodes import ExprType

        return ExprType(ValueType.INTEGER, Cardinality.SINGLE)

    @classmethod
    def compile(cls, args: tuple[Expr, ...], ctx: CompileContext) -> ScalarSql:
        elem_set = ctx.to_element_set(args[0])
        from_clause = elem_set.source.from_clause
        where_parts = [elem_set.source.type_check] + list(elem_set.conditions)
        where_joined = SqlFragment.join(" AND ", where_parts)

        sql = f"SELECT MAX(({elem_set.value.sql})::numeric) FROM {from_clause.sql} WHERE {where_joined.sql}"
        params = elem_set.value.params + from_clause.params + where_joined.params
        return ScalarSql(SqlFragment(f"({sql})", params), ValueType.INTEGER)


class Sum(SearchFunction):
    """Sum aggregation for integer array fields."""

    name = "sum"
    description = "sum of values (integer fields)"
    examples = ("sum(facts.generic.Hardware.memory[].size) >= 8000000000",)
    params = (
        Param(
            "field",
            ParamKind.FIELD,
            frozenset({ValueType.INTEGER}),
            Cardinality.ELEMENTS,
        ),
    )

    @classmethod
    def return_type(cls, args: tuple[Expr, ...]) -> ExprType:
        from ..nodes import ExprType

        return ExprType(ValueType.INTEGER, Cardinality.SINGLE)

    @classmethod
    def compile(cls, args: tuple[Expr, ...], ctx: CompileContext) -> ScalarSql:
        elem_set = ctx.to_element_set(args[0])
        from_clause = elem_set.source.from_clause
        where_parts = [elem_set.source.type_check] + list(elem_set.conditions)
        where_joined = SqlFragment.join(" AND ", where_parts)

        sql = f"SELECT SUM(({elem_set.value.sql})::numeric) FROM {from_clause.sql} WHERE {where_joined.sql}"
        params = elem_set.value.params + from_clause.params + where_joined.params
        return ScalarSql(SqlFragment(f"({sql})", params), ValueType.INTEGER)


class Concat(SearchFunction):
    """String concatenation aggregation for string array fields."""

    name = "concat"
    description = "concatenate strings (string fields)"
    examples = ('concat(facts.generic.Users[].name) contains "root"',)
    params = (
        Param(
            "field",
            ParamKind.FIELD,
            frozenset({ValueType.STRING}),
            Cardinality.ELEMENTS,
        ),
    )

    @classmethod
    def return_type(cls, args: tuple[Expr, ...]) -> ExprType:
        from ..nodes import ExprType

        return ExprType(ValueType.STRING, Cardinality.SINGLE)

    @classmethod
    def compile(cls, args: tuple[Expr, ...], ctx: CompileContext) -> ScalarSql:
        elem_set = ctx.to_element_set(args[0])
        from_clause = elem_set.source.from_clause
        where_parts = [elem_set.source.type_check] + list(elem_set.conditions)
        where_joined = SqlFragment.join(" AND ", where_parts)

        sql = f"SELECT STRING_AGG({elem_set.value.sql}, ', ') FROM {from_clause.sql} WHERE {where_joined.sql}"
        params = elem_set.value.params + from_clause.params + where_joined.params
        return ScalarSql(SqlFragment(f"({sql})", params), ValueType.STRING)


class Count(SearchFunction):
    """Count aggregation for any array field or filtered array elements."""

    name = "count"
    description = "count array elements (all array fields)"
    examples = (
        "count(facts.generic.Users[].name) >= 2",
        'count(filter(facts.generic.PackageManagerInfo.installed_packages[].name, "ssh")) > 0',
    )
    params = (
        Param(
            "target",
            ParamKind.EXPR,
            None,
            Cardinality.ELEMENTS,
        ),
    )

    @classmethod
    def return_type(cls, args: tuple[Expr, ...]) -> ExprType:
        from ..nodes import ExprType

        return ExprType(ValueType.INTEGER, Cardinality.SINGLE)

    @classmethod
    def compile(cls, args: tuple[Expr, ...], ctx: CompileContext) -> ScalarSql:
        elem_set = ctx.to_element_set(args[0])
        from_clause = elem_set.source.from_clause
        where_parts = [elem_set.source.type_check] + list(elem_set.conditions)
        where_joined = SqlFragment.join(" AND ", where_parts)

        sql = f"SELECT COUNT({elem_set.value.sql}) FROM {from_clause.sql} WHERE {where_joined.sql}"
        params = elem_set.value.params + from_clause.params + where_joined.params
        return ScalarSql(SqlFragment(f"({sql})", params), ValueType.INTEGER)
