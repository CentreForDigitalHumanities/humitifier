"""Correlated array element matching search function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..constants import Cardinality, ValueType
from ..sql import SqlFragment
from .base import Param, ParamKind, SearchFunction

if TYPE_CHECKING:
    from ..nodes import Expr, ExprType
    from ..sql import CompileContext


class MatchElements(SearchFunction):
    """Match multiple fields against patterns on the same array element."""

    name = "match"
    description = "Match multiple fields against patterns on the same array element"
    examples = (
        "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
        "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0')",
    )
    params = ()
    variadic = (
        Param("field", ParamKind.FIELD, frozenset({ValueType.STRING}), Cardinality.ELEMENTS),
        Param("pattern", ParamKind.LITERAL, frozenset({ValueType.STRING}), Cardinality.SINGLE),
    )

    @classmethod
    def validate(cls, args: tuple[Expr, ...]) -> None:
        if len(args) < 2:
            raise ValueError(
                f"Function '{cls.name}' requires at least 2 arguments (field, pattern pairs)"
            )
        super().validate(args)
        first_field = args[0].field  # type: ignore[attr-defined]
        for i in range(0, len(args), 2):
            f = args[i].field  # type: ignore[attr-defined]
            if (f.section, f.artefact_key, f.array_path) != (
                first_field.section,
                first_field.artefact_key,
                first_field.array_path,
            ):
                pos = getattr(args[i], "position", 0)
                raise ValueError(
                    f"All fields in '{cls.name}' must belong to the same array at position {pos}"
                )

    @classmethod
    def return_type(cls, args: tuple[Expr, ...]) -> ExprType:
        from ..nodes import ExprType

        return ExprType(ValueType.BOOLEAN, Cardinality.SINGLE)

    @classmethod
    def compile(cls, args: tuple[Expr, ...], ctx: CompileContext) -> SqlFragment:
        first_field = args[0].field  # type: ignore[attr-defined]
        source = ctx.get_element_source(first_field)
        conditions = []
        for i in range(0, len(args), 2):
            f = args[i].field  # type: ignore[attr-defined]
            pattern = args[i + 1].value  # type: ignore[attr-defined]
            val = ctx.element_value(f, source)
            conditions.append(
                SqlFragment(f"{val.sql} ILIKE %s", val.params + (f"%{pattern}%",))
            )
        where_parts = [source.type_check] + conditions
        where_joined = SqlFragment.join(" AND ", where_parts)
        sql = f"EXISTS (SELECT 1 FROM {source.from_clause.sql} WHERE {where_joined.sql})"
        return SqlFragment(sql, source.from_clause.params + where_joined.params)

    @classmethod
    def compile_matches(
        cls, args: tuple[Expr, ...], ctx: CompileContext
    ) -> SqlFragment | None:
        first_field = args[0].field  # type: ignore[attr-defined]
        source = ctx.get_element_source(first_field)
        conditions = []
        obj_parts = []
        obj_params = []

        for i in range(0, len(args), 2):
            f = args[i].field  # type: ignore[attr-defined]
            pattern = args[i + 1].value  # type: ignore[attr-defined]
            val = ctx.element_value(f, source)
            conditions.append(
                SqlFragment(f"{val.sql} ILIKE %s", val.params + (f"%{pattern}%",))
            )
            key = f.element_field_path[-1] if f.element_field_path else f.id
            obj_parts.append(f"%s, {val.sql}")
            obj_params.extend([key, *val.params])

        obj_sql = f"jsonb_build_object({', '.join(obj_parts)})"
        where_parts = [source.type_check] + conditions
        where_joined = SqlFragment.join(" AND ", where_parts)

        subquery_sql = (
            f"(SELECT COALESCE(jsonb_agg({obj_sql}), '[]'::jsonb) "
            f"FROM {source.from_clause.sql} WHERE {where_joined.sql})"
        )
        params = tuple(obj_params) + source.from_clause.params + where_joined.params
        return SqlFragment(subquery_sql, params)
