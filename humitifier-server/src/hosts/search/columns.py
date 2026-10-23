"""Column specification, expression compilation, and value formatting for host search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable

from django.db.models import JSONField
from django.db.models.expressions import RawSQL
from humitifier_common.artefacts import registry as artefact_registry

from .constants import (
    MATCH_COLUMN_PREFIX,
    SCAN_CACHE_FIELD,
    Cardinality,
    FieldKind,
    LogicalOperator,
    Section,
    ValueType,
)
from .functions.base import SearchFunction
from .nodes import (
    BoolNode,
    Comparison,
    Expr,
    FieldRef,
    FunctionCall,
    Literal,
    Logical,
)
from .sql import CompileContext, ElementSet, ScalarSql, SqlFragment

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from ..models import Host


@dataclass(frozen=True)
class ColumnSpec:
    """Specification of a column to project in search results.

    Attributes:
        source: Original text representation of the column expression.
        expr: AST expression node (Expr or BoolNode for match columns).
        alias: Optional column label alias specified via AS "Label".
        derived: Whether this column was automatically derived (e.g. show matches).
    """

    source: str
    expr: Expr | BoolNode
    alias: str | None = None
    derived: bool = False

    @property
    def label(self) -> str:
        """Return the effective header label for the column."""
        base = self.alias if self.alias is not None else format_expr(self.expr)
        if self.derived:
            if base.startswith(MATCH_COLUMN_PREFIX):
                return base
            return f"{MATCH_COLUMN_PREFIX}{base}"
        return base


def format_expr(node: Expr | BoolNode) -> str:
    """Format an Expr or BoolNode into a canonical search expression string."""
    if isinstance(node, FieldRef):
        return node.field.id
    if isinstance(node, Literal):
        if node.value_type == ValueType.STRING:
            val = str(node.value).replace('"', '\\"')
            return f'"{val}"'
        if node.value_type == ValueType.BOOLEAN:
            return "true" if node.value else "false"
        return str(node.value)
    if isinstance(node, FunctionCall):
        args_str = ", ".join(format_expr(a) for a in node.args)
        return f"{node.function.name}({args_str})"
    if isinstance(node, Comparison):
        return f"{format_expr(node.lhs)} {node.operator.symbol} {format_expr(node.rhs)}"
    if isinstance(node, Logical):
        if node.operator == LogicalOperator.NOT:
            if len(node.children) == 1:
                return f"NOT {format_expr(node.children[0])}"
            inner = " AND ".join(format_expr(c) for c in node.children)
            return f"NOT ({inner})"
        op_str = f" {node.operator.value} "
        return op_str.join(format_expr(c) for c in node.children)
    raise ValueError(f"Unknown expression node type: {type(node)}")


def _wrap_version_check(subquery: SqlFragment, ctx: CompileContext) -> SqlFragment:
    """Wrap a jsonb subquery in a CASE statement checking the cache format version."""
    sql = (
        f'CASE WHEN "{ctx.table_name}"."{SCAN_CACHE_FIELD}"->>\'version\' = %s '
        f'THEN {subquery.sql} END'
    )
    params = (str(artefact_registry.latest_version),) + subquery.params
    return SqlFragment(sql, params)


def _compile_element_set_column(elem_set: ElementSet, ctx: CompileContext) -> SqlFragment:
    """Compile an ElementSet into a jsonb array aggregation subquery."""
    from_clause = elem_set.source.from_clause
    where_parts = [elem_set.source.type_check] + list(elem_set.conditions)
    where_joined = SqlFragment.join(" AND ", where_parts)

    val_sql = elem_set.value.sql
    val_params = elem_set.value.params

    if elem_set.value_type == ValueType.INTEGER:
        val_expr = f"({val_sql})::numeric"
    elif elem_set.value_type == ValueType.BOOLEAN:
        val_expr = f"({val_sql})::boolean"
    else:
        val_expr = val_sql

    where_clause = f" WHERE {where_joined.sql}" if where_joined.sql else ""
    subquery_sql = (
        f"(SELECT COALESCE(jsonb_agg({val_expr}), '[]'::jsonb) "
        f"FROM {from_clause.sql}{where_clause})"
    )
    subquery_params = val_params + from_clause.params + where_joined.params
    subquery = SqlFragment(subquery_sql, subquery_params)
    return _wrap_version_check(subquery, ctx)


def compile_column_expr(expr: Expr | BoolNode | Any, ctx: CompileContext) -> SqlFragment:
    """Compile a column expression AST node into a jsonb-returning SqlFragment.

    Args:
        expr: AST expression node to compile.
        ctx: Compilation context containing table name and element state.

    Returns:
        SqlFragment producing a jsonb scalar or null for the host row.
    """
    if isinstance(expr, FieldRef):
        field = expr.field

        if field.section == Section.META:
            from ..models import Host

            field_name = field.field_path[0]
            model_col = Host._meta.get_field(field_name).column
            return SqlFragment(f'to_jsonb("{ctx.table_name}"."{model_col}")', ())

        if field.kind == FieldKind.SCALAR:
            path = [field.section, field.artefact_key] + list(field.field_path)
            inner_sql = f'("{ctx.table_name}"."{SCAN_CACHE_FIELD}" #> %s)'
            inner_frag = SqlFragment(inner_sql, (list(path),))
            return _wrap_version_check(inner_frag, ctx)

        if field.kind == FieldKind.ARRAY:
            elem_set = ctx.to_element_set(expr)
            return _compile_element_set_column(elem_set, ctx)

    if isinstance(expr, FunctionCall):
        if (
            getattr(expr.function, "compile_matches", None) is not None
            and expr.function.compile_matches is not SearchFunction.compile_matches
        ):
            matches_frag = expr.function.compile_matches(expr.args, ctx)
            if matches_frag is not None:
                return _wrap_version_check(matches_frag, ctx)

        compiled = expr.function.compile(expr.args, ctx)
        if isinstance(compiled, ElementSet):
            return _compile_element_set_column(compiled, ctx)
        if isinstance(compiled, ScalarSql):
            subquery = SqlFragment(f"to_jsonb({compiled.fragment.sql})", compiled.fragment.params)
            return _wrap_version_check(subquery, ctx)
        if isinstance(compiled, SqlFragment):
            subquery = SqlFragment(f"to_jsonb({compiled.sql})", compiled.params)
            return _wrap_version_check(subquery, ctx)
        raise ValueError(f"Unsupported compiled function result type: {type(compiled)}")

    if isinstance(expr, ElementSet):
        return _compile_element_set_column(expr, ctx)

    if isinstance(expr, ScalarSql):
        subquery = SqlFragment(f"to_jsonb({expr.fragment.sql})", expr.fragment.params)
        return _wrap_version_check(subquery, ctx)

    if isinstance(expr, SqlFragment):
        subquery = SqlFragment(f"to_jsonb({expr.sql})", expr.params)
        return _wrap_version_check(subquery, ctx)

    if isinstance(expr, Comparison):
        lhs = expr.lhs
        op = expr.operator
        rhs = expr.rhs
        if isinstance(lhs, FieldRef) and lhs.field.kind == FieldKind.ARRAY:
            elem_set = ctx.to_element_set(lhs)
            cond = op.to_sql(elem_set.value, rhs.value, lhs.field.value_type)
            return _compile_element_set_column(elem_set.with_condition(cond), ctx)
        if isinstance(lhs, FunctionCall):
            compiled = lhs.function.compile(lhs.args, ctx)
            if isinstance(compiled, ElementSet):
                cond = op.to_sql(compiled.value, rhs.value, compiled.value_type)
                return _compile_element_set_column(compiled.with_condition(cond), ctx)

    raise ValueError(f"Unsupported column expression: {type(expr)}")


def derive_match_columns(node: BoolNode | None) -> list[ColumnSpec]:
    """Extract derived match columns from query AST array conditions.

    Walks the AST skipping NOT subtrees, extracting array comparisons,
    ElementSet function comparisons, and match functions. Deduplicates by label.
    """
    if node is None:
        return []

    found: list[ColumnSpec] = []

    def _walk(current: BoolNode) -> None:
        if isinstance(current, Logical):
            if current.operator == LogicalOperator.NOT:
                return  # Skip NOT subtrees entirely
            for child in current.children:
                _walk(child)
            return

        if isinstance(current, Comparison):
            lhs = current.lhs
            if isinstance(lhs, FieldRef) and lhs.field.kind == FieldKind.ARRAY:
                found.append(
                    ColumnSpec(
                        source=format_expr(current),
                        expr=current,
                        derived=True,
                    )
                )
            elif (
                isinstance(lhs, FunctionCall)
                and lhs.expr_type.cardinality == Cardinality.ELEMENTS
            ):
                found.append(
                    ColumnSpec(
                        source=format_expr(current),
                        expr=current,
                        derived=True,
                    )
                )
            return

        if isinstance(current, FunctionCall):
            if (
                getattr(current.function, "compile_matches", None) is not None
                and current.function.compile_matches is not SearchFunction.compile_matches
            ):
                found.append(
                    ColumnSpec(
                        source=format_expr(current),
                        expr=current,
                        derived=True,
                    )
                )
            return

    _walk(node)

    seen_labels: set[str] = set()
    deduped: list[ColumnSpec] = []
    for col in found:
        lbl = col.label
        if lbl not in seen_labels:
            seen_labels.add(lbl)
            deduped.append(col)

    return deduped


def evaluate_columns(
    qs: QuerySet[Host],
    columns: list[ColumnSpec],
) -> list[dict[str, Any]]:
    """Evaluate column expressions for all hosts in the queryset in a single query.

    Args:
        qs: The filtered Host queryset.
        columns: List of ColumnSpec instances to evaluate.

    Returns:
        List of dicts, one per host: [{"object": host, "fields": {label: value, ...}}]
    """
    if not columns:
        return [{"object": host, "fields": {}} for host in qs]

    from ..models import Host

    ctx = CompileContext(table_name=Host._meta.db_table)
    annotations: dict[str, RawSQL] = {}
    for i, col in enumerate(columns):
        frag = compile_column_expr(col.expr, ctx)
        annotations[f"col_{i}"] = RawSQL(frag.sql, frag.params, output_field=JSONField())

    annotated_qs = qs.annotate(**annotations)
    results: list[dict[str, Any]] = []
    for host in annotated_qs:
        fields: dict[str, Any] = {}
        for i, col in enumerate(columns):
            fields[col.label] = getattr(host, f"col_{i}")
        results.append({"object": host, "fields": fields})

    return results


def format_value(value: Any) -> str:
    """Format a column value for display in HTML templates and CSV export.

    - None -> ""
    - boolean -> "True" or "False"
    - list -> comma-separated elements (e.g. "a, b")
    - dict -> key-value pairs joined with semicolons (e.g. "name: php; version: 7.4")
    - other scalar -> string representation
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, list):
        return ", ".join(format_value(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{k}: {format_value(v)}" for k, v in value.items())
    return str(value)
