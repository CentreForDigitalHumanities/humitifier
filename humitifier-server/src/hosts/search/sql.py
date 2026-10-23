"""Composable SQL fragment model and element scoping for JSONB queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Union

from .constants import ARRAY_MARKER, SCAN_CACHE_FIELD, ValueType
from .types import SearchableField


@dataclass(frozen=True)
class SqlFragment:
    """A parameterized SQL fragment carrying its own parameters."""

    sql: str
    params: tuple[Any, ...] = ()

    @classmethod
    def join(cls, separator: str, fragments: Iterable[SqlFragment]) -> SqlFragment:
        frags = list(fragments)
        if not frags:
            return cls("", ())
        sql = separator.join(f.sql for f in frags)
        params = tuple(p for f in frags for p in f.params)
        return cls(sql, params)

    def __add__(self, other: SqlFragment) -> SqlFragment:
        return SqlFragment(f"{self.sql} {other.sql}", self.params + other.params)


@dataclass(frozen=True)
class ElementSource:
    """The LATERAL JSONB array expansion chain and type check for an array path."""

    section: str
    artefact_key: str
    array_path: tuple[str, ...]
    from_clause: SqlFragment
    type_check: SqlFragment
    element_expr: str

    @classmethod
    def create(
        cls,
        section: str,
        artefact_key: str,
        array_path: tuple[str, ...],
        table_name: str = "hosts_host",
    ) -> ElementSource:
        initial_params: list[Any] = [section, artefact_key]
        base_expression = f'"{table_name}"."{SCAN_CACHE_FIELD}"->%s->%s'
        current_expression = base_expression
        from_clauses: list[str] = []
        nesting_level = 0
        first_array_expression = None
        params_before_first_array: list[Any] = []

        for path_token in array_path:
            if path_token == ARRAY_MARKER:
                element_alias = f"e{nesting_level}"
                if first_array_expression is None:
                    first_array_expression = current_expression
                    params_before_first_array = list(initial_params)
                from_clauses.append(
                    f"jsonb_array_elements({current_expression}) AS {element_alias}"
                )
                current_expression = element_alias
                nesting_level += 1
            else:
                current_expression = f"{current_expression}->%s"
                initial_params.append(path_token)

        if not from_clauses:
            element_alias = f"e{nesting_level}"
            first_array_expression = current_expression
            params_before_first_array = list(initial_params)
            from_clauses.append(
                f"jsonb_array_elements({current_expression}) AS {element_alias}"
            )
            current_expression = element_alias

        from_sql = " CROSS JOIN LATERAL ".join(from_clauses)
        from_fragment = SqlFragment(from_sql, tuple(initial_params))

        type_check_sql = f"jsonb_typeof({first_array_expression}) = 'array'"
        type_check_fragment = SqlFragment(type_check_sql, tuple(params_before_first_array))

        return cls(
            section=section,
            artefact_key=artefact_key,
            array_path=array_path,
            from_clause=from_fragment,
            type_check=type_check_fragment,
            element_expr=current_expression,
        )


@dataclass(frozen=True)
class ElementSet:
    """An element scope with its source, value expression, and WHERE conditions."""

    source: ElementSource
    value: SqlFragment
    conditions: tuple[SqlFragment, ...] = ()
    value_type: ValueType = ValueType.STRING

    def with_condition(self, condition: SqlFragment) -> ElementSet:
        return ElementSet(
            source=self.source,
            value=self.value,
            conditions=self.conditions + (condition,),
            value_type=self.value_type,
        )

    def to_exists(self, extra_condition: SqlFragment | None = None) -> SqlFragment:
        all_conds = list(self.conditions)
        if extra_condition:
            all_conds.append(extra_condition)

        where_frags = [self.source.type_check] + all_conds
        where_joined = SqlFragment.join(" AND ", where_frags)

        sql = f"EXISTS (SELECT 1 FROM {self.source.from_clause.sql} WHERE {where_joined.sql})"
        params = self.source.from_clause.params + where_joined.params
        return SqlFragment(sql, params)


@dataclass(frozen=True)
class ScalarSql:
    """A scalar SQL fragment (e.g., from an aggregation) with its value type."""

    fragment: SqlFragment
    value_type: ValueType


CompiledExpr = Union[ElementSet, ScalarSql, SqlFragment]


class CompileContext:
    """Compilation context managing shared array element sources across expressions."""

    def __init__(self, table_name: str = "hosts_host"):
        self.table_name = table_name
        self._sources: dict[tuple[str, str, tuple[str, ...]], ElementSource] = {}

    def get_element_source(self, field: SearchableField) -> ElementSource:
        key = (field.section, field.artefact_key, field.array_path or (ARRAY_MARKER,))
        if key not in self._sources:
            self._sources[key] = ElementSource.create(
                section=field.section,
                artefact_key=field.artefact_key,
                array_path=field.array_path or (ARRAY_MARKER,),
                table_name=self.table_name,
            )
        return self._sources[key]

    def element_value(
        self, field: SearchableField, source: ElementSource | None = None
    ) -> SqlFragment:
        if source is None:
            source = self.get_element_source(field)

        element_expr = source.element_expr
        path = field.element_field_path or ()

        if not path:
            if field.value_type == ValueType.STRING:
                sql = (
                    f"CASE WHEN jsonb_typeof({element_expr})='string' "
                    f"THEN trim(both '\"' from {element_expr}::text) "
                    f"ELSE {element_expr}::text END"
                )
                return SqlFragment(sql, ())
            return SqlFragment(f"{element_expr}::text", ())

        if len(path) == 1:
            return SqlFragment(f"{element_expr}->>%s", (path[0],))

        expr = element_expr
        params = []
        for key in path[:-1]:
            expr = f"{expr}->%s"
            params.append(key)
        expr = f"{expr}->>%s"
        params.append(path[-1])
        return SqlFragment(expr, tuple(params))

    def to_element_set(self, expr: Any) -> ElementSet:
        from .nodes import FieldRef, FunctionCall

        if isinstance(expr, FieldRef):
            source = self.get_element_source(expr.field)
            value = self.element_value(expr.field, source)
            return ElementSet(
                source=source,
                value=value,
                conditions=(),
                value_type=expr.field.value_type,
            )
        if isinstance(expr, FunctionCall):
            compiled = expr.function.compile(expr.args, self)
            if isinstance(compiled, ElementSet):
                return compiled
        raise ValueError(f"Cannot convert expression {expr} to an ElementSet")
