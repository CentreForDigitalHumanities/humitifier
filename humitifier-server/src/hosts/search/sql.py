"""Composable SQL fragment model and element scoping for JSONB queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Union

from .constants import ARRAY_MARKER, SCAN_CACHE_FIELD, Section, ValueType
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
        unacknowledged_only: bool = True,
    ) -> ElementSource:
        if section == Section.ALERTS:
            from_sql = (
                '"alerting_alert" a LEFT JOIN "alerting_alertacknowledgment" ack '
                'ON (ack."_alert_id" = a."id" OR (ack."host_id" = a."host_id" AND ack."_creator" = a."_creator" AND ack."custom_identifier" = a."custom_identifier"))'
            )
            if unacknowledged_only:
                type_check_sql = (
                    f'a."host_id" = "{table_name}"."id" AND ack."id" IS NULL'
                )
            else:
                type_check_sql = f'a."host_id" = "{table_name}"."id"'
            return cls(
                section=section,
                artefact_key=artefact_key,
                array_path=array_path,
                from_clause=SqlFragment(from_sql, ()),
                type_check=SqlFragment(type_check_sql, ()),
                element_expr="a",
            )

        current_frag = SqlFragment(
            f'"{table_name}"."{SCAN_CACHE_FIELD}"->%s->%s',
            (section, artefact_key),
        )
        from_clauses: list[SqlFragment] = []
        nesting_level = 0
        first_array_frag: SqlFragment | None = None

        for path_token in array_path:
            if path_token == ARRAY_MARKER:
                element_alias = f"e{nesting_level}"
                if first_array_frag is None:
                    first_array_frag = current_frag
                clause_sql = (
                    f"jsonb_array_elements(CASE WHEN jsonb_typeof({current_frag.sql}) = 'array' "
                    f"THEN {current_frag.sql} ELSE '[]'::jsonb END) AS {element_alias}"
                )
                from_clauses.append(
                    SqlFragment(clause_sql, current_frag.params + current_frag.params)
                )
                current_frag = SqlFragment(element_alias, ())
                nesting_level += 1
            else:
                current_frag = SqlFragment(
                    f"{current_frag.sql}->%s",
                    current_frag.params + (path_token,),
                )

        if not from_clauses:
            element_alias = f"e{nesting_level}"
            first_array_frag = current_frag
            clause_sql = (
                f"jsonb_array_elements(CASE WHEN jsonb_typeof({current_frag.sql}) = 'array' "
                f"THEN {current_frag.sql} ELSE '[]'::jsonb END) AS {element_alias}"
            )
            from_clauses.append(
                SqlFragment(clause_sql, current_frag.params + current_frag.params)
            )
            current_frag = SqlFragment(element_alias, ())

        from_fragment = SqlFragment.join(" CROSS JOIN LATERAL ", from_clauses)

        type_check_sql = f"jsonb_typeof({first_array_frag.sql}) = 'array'"
        type_check_fragment = SqlFragment(type_check_sql, first_array_frag.params)

        return cls(
            section=section,
            artefact_key=artefact_key,
            array_path=array_path,
            from_clause=from_fragment,
            type_check=type_check_fragment,
            element_expr=current_frag.sql,
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
        is_alert_ack = (
            field.section == Section.ALERTS
            and bool(field.field_path)
            and field.field_path[0] == "acknowledged"
        )
        unack = not is_alert_ack
        key = (
            field.section,
            field.artefact_key,
            field.array_path or (ARRAY_MARKER,),
            unack,
        )
        if key not in self._sources:
            self._sources[key] = ElementSource.create(
                section=field.section,
                artefact_key=field.artefact_key,
                array_path=field.array_path or (ARRAY_MARKER,),
                table_name=self.table_name,
                unacknowledged_only=unack,
            )
        return self._sources[key]

    def element_value(
        self, field: SearchableField, source: ElementSource | None = None
    ) -> SqlFragment:
        if source is None:
            source = self.get_element_source(field)

        if field.section == Section.ALERTS:
            field_name = field.field_path[0] if field.field_path else ""
            if field_name == "acknowledged":
                return SqlFragment('(ack."id" IS NOT NULL)', ())
            col = "_creator" if field_name == "creator" else field_name
            return SqlFragment(f'{source.element_expr}."{col}"', ())

        element_expr = source.element_expr
        path = field.element_field_path or ()

        if not path:
            if field.value_type == ValueType.STRING:
                sql = f"{element_expr} #>> '{{}}'"
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
