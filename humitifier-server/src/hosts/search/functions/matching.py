"""Correlated array element matching search function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..constants import Cardinality, ValueType
from ..sql import SqlFragment
from .base import Param, ParamKind, SearchFunction

if TYPE_CHECKING:
    from ..nodes import Expr, ExprType
    from ..sql import CompileContext


def _build_match_condition(
    val: SqlFragment, pattern: Any, val_type: ValueType
) -> SqlFragment:
    if val_type == ValueType.STRING:
        return SqlFragment(f"{val.sql} ILIKE %s", val.params + (f"%{pattern}%",))
    if val_type == ValueType.BOOLEAN:
        bool_val = (
            str(pattern).lower() if isinstance(pattern, bool) else str(pattern).lower()
        )
        return SqlFragment(f"{val.sql} = %s", val.params + (bool_val,))
    return SqlFragment(f"{val.sql} = %s", val.params + (str(pattern),))


class MatchElements(SearchFunction):
    """Match multiple fields against patterns on the same array element."""

    name = "match"
    description = "Match multiple fields against patterns on the same array element"
    examples = (
        "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
        "facts.generic.PackageManagerInfo.installed_packages[].current_version, '7.0')",
        "match(facts.generic.PackageManagerInfo.installed_packages[].name, 'php', "
        "facts.generic.PackageManagerInfo.installed_packages[].upgrade_available, true)",
    )
    params = ()
    variadic = (
        Param(
            "field",
            ParamKind.FIELD,
            frozenset({ValueType.STRING, ValueType.INTEGER, ValueType.BOOLEAN}),
            Cardinality.ELEMENTS,
        ),
        Param(
            "pattern",
            ParamKind.LITERAL,
            frozenset({ValueType.STRING, ValueType.INTEGER, ValueType.BOOLEAN}),
            Cardinality.SINGLE,
        ),
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
            field_type = args[i].expr_type.value_type
            pattern_type = args[i + 1].expr_type.value_type
            if field_type != pattern_type:
                pos = getattr(args[i + 1], "position", 0)
                raise ValueError(
                    f"Type mismatch: cannot match {field_type.value} field with {pattern_type.value} literal at position {pos}"
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
            conditions.append(_build_match_condition(val, pattern, f.value_type))
        where_parts = [source.type_check] + conditions
        where_joined = SqlFragment.join(" AND ", where_parts)
        sql = (
            f"EXISTS (SELECT 1 FROM {source.from_clause.sql} WHERE {where_joined.sql})"
        )
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
            conditions.append(_build_match_condition(val, pattern, f.value_type))
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
