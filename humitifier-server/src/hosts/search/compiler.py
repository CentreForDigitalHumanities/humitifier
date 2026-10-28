"""AST compiler to Django Q expressions and host search queryset filtering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import BooleanField, Q, QuerySet
from django.db.models.expressions import RawSQL
from humitifier_common.artefacts import registry as artefact_registry

from .constants import FieldKind, LogicalOperator, Section
from .nodes import BoolNode, Comparison, FieldRef, FunctionCall, Logical
from .sql import CompileContext, ElementSet, ScalarSql, SqlFragment

if TYPE_CHECKING:
    from ..models import Host


def compile_comparison(comp: Comparison, ctx: CompileContext) -> Q:
    """Compile a Comparison node to a Django Q object."""
    lhs = comp.lhs
    op = comp.operator
    rhs = comp.rhs

    if isinstance(lhs, FieldRef):
        field = lhs.field

        # Meta fields: Host model attributes
        if field.section == Section.META:
            field_name = field.field_path[0]
            lookup = op.to_lookup(field.value_type)
            lookup_suffix = f"__{lookup}" if lookup != "exact" else ""
            q = Q(**{f"{field_name}{lookup_suffix}": rhs.value})
            return ~q if getattr(op, "negated", False) else q

        # Alert fields: Alert model attributes
        if field.section == Section.ALERTS:
            from alerting.models import Alert, AlertAcknowledgment
            from django.db.models import Exists, OuterRef

            field_name = field.field_path[0]
            ack_exists = Exists(
                AlertAcknowledgment.objects.filter(
                    Q(_alert=OuterRef("pk"))
                    | Q(
                        host=OuterRef("host_id"),
                        _creator=OuterRef("_creator"),
                        custom_identifier=OuterRef("custom_identifier"),
                    )
                )
            )

            if field_name == "acknowledged":
                is_acknowledged = rhs.value if not getattr(op, "negated", False) else (not rhs.value)
                if is_acknowledged:
                    subq = Alert.objects.filter(ack_exists, host=OuterRef("pk"))
                else:
                    subq = Alert.objects.filter(~ack_exists, host=OuterRef("pk"))
                return Q(Exists(subq))

            orm_field = "_creator" if field_name == "creator" else field_name
            lookup = op.to_lookup(field.value_type)
            lookup_suffix = f"__{lookup}" if lookup != "exact" else ""
            filter_kwargs = {
                f"{orm_field}{lookup_suffix}": rhs.value,
            }
            subq = Alert.objects.filter(
                ~ack_exists,
                host=OuterRef("pk"),
                **filter_kwargs,
            )
            q = Q(Exists(subq))
            return ~q if getattr(op, "negated", False) else q

        # Scalar JSON fields in last_scan_cache
        if field.kind == FieldKind.SCALAR:
            lookup = op.to_lookup(field.value_type)
            lookup_suffix = f"__{lookup}" if lookup != "exact" else ""
            field_path_str = "__".join(field.field_path)
            lookup_path = f"last_scan_cache__{field.section}__{field.artefact_key}__{field_path_str}"
            q = Q(**{f"{lookup_path}{lookup_suffix}": rhs.value})
            return ~q if getattr(op, "negated", False) else q

        # Array fields in last_scan_cache without aggregation (element match)
        if field.kind == FieldKind.ARRAY:
            elem_set = ctx.to_element_set(lhs)
            cond = op.to_sql(elem_set.value, rhs.value, field.value_type)
            exists_frag = elem_set.to_exists(extra_condition=cond)
            return Q(RawSQL(exists_frag.sql, exists_frag.params, output_field=BooleanField()))

    if isinstance(lhs, FunctionCall):
        compiled = lhs.function.compile(lhs.args, ctx)
        if isinstance(compiled, ElementSet):
            cond = op.to_sql(compiled.value, rhs.value, compiled.value_type)
            exists_frag = compiled.to_exists(extra_condition=cond)
            return Q(RawSQL(exists_frag.sql, exists_frag.params, output_field=BooleanField()))
        elif isinstance(compiled, ScalarSql):
            cond = op.to_sql(compiled.fragment, rhs.value, compiled.value_type)
            return Q(RawSQL(cond.sql, cond.params, output_field=BooleanField()))
        elif isinstance(compiled, SqlFragment):
            cond = op.to_sql(compiled, rhs.value, lhs.expr_type.value_type)
            return Q(RawSQL(cond.sql, cond.params, output_field=BooleanField()))

    raise ValueError(f"Unsupported comparison LHS: {type(lhs)}")


def compile_node(node: BoolNode, ctx: CompileContext) -> Q:
    """Recursively compile a BoolNode to a Django Q object."""
    if isinstance(node, Comparison):
        return compile_comparison(node, ctx)

    if isinstance(node, Logical):
        if node.operator == LogicalOperator.AND:
            q = Q()
            for child in node.children:
                q &= compile_node(child, ctx)
            return q
        elif node.operator == LogicalOperator.OR:
            if not node.children:
                return Q()
            q = compile_node(node.children[0], ctx)
            for child in node.children[1:]:
                q |= compile_node(child, ctx)
            return q
        elif node.operator == LogicalOperator.NOT:
            if not node.children:
                return Q()
            if len(node.children) == 1:
                return ~compile_node(node.children[0], ctx)
            q = Q()
            for child in node.children:
                q &= compile_node(child, ctx)
            return ~q

    if isinstance(node, FunctionCall):
        compiled = node.function.compile(node.args, ctx)
        if isinstance(compiled, ElementSet):
            exists_frag = compiled.to_exists()
            return Q(RawSQL(exists_frag.sql, exists_frag.params, output_field=BooleanField()))
        elif isinstance(compiled, SqlFragment):
            return Q(RawSQL(compiled.sql, compiled.params, output_field=BooleanField()))
        elif isinstance(compiled, ScalarSql):
            return Q(RawSQL(compiled.fragment.sql, compiled.fragment.params, output_field=BooleanField()))

    raise ValueError(f"Unsupported AST node: {type(node)}")


def search_hosts_by_scan_fields(
    queryset: QuerySet[Host],
    criteria: BoolNode | None = None,
) -> QuerySet[Host]:
    """Filter a Host queryset by searching values within Host model fields and last_scan_cache.

    Args:
        queryset: The initial Host QuerySet to filter.
        criteria: Root BoolNode of the parsed query AST, or None for no filtering.

    Returns:
        Filtered QuerySet of Host objects matching the criteria and format version.
    """
    if criteria is None:
        return queryset

    from ..models import Host

    ctx = CompileContext(table_name=Host._meta.db_table)
    q = compile_node(criteria, ctx)
    version_filter = Q(last_scan_cache__version=artefact_registry.latest_version)
    return queryset.filter(q).filter(version_filter)
