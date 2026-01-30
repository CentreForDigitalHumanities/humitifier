"""Query building and filtering logic for host searches."""

from __future__ import annotations

from typing import Any, Mapping

from django.db.models import Q, QuerySet
from django.db.models.expressions import RawSQL

from ..models import Host
from .field_discovery import get_searchable_fields
from .types import ComplexQuery, ComparisonOperator, SearchableField, SearchCriterion


def _parse_value(value: Any, value_type: str) -> Any:
    """Parse and convert a value to the appropriate type."""
    if value_type == "integer":
        try:
            return int(value)
        except Exception:
            return value
    if value_type == "boolean":
        if isinstance(value, bool):
            return value
        sval = str(value).strip().lower()
        if sval in {"true", "1", "yes", "y", "on"}:
            return True
        if sval in {"false", "0", "no", "n", "off"}:
            return False
        return value
    # string
    return str(value)


def _operator_to_sql(operator: ComparisonOperator) -> str:
    """Convert ComparisonOperator to SQL operator."""
    mapping = {
        "eq": "=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "contains": "ILIKE",  # fallback, usually handled specially
    }
    return mapping.get(operator, "=")


def _apply_criterion_to_queryset(
    qs: QuerySet[Host],
    criterion: SearchCriterion,
    descriptor: SearchableField,
) -> QuerySet[Host]:
    """Apply a single search criterion with an operator to a QuerySet."""
    value = _parse_value(criterion.value, descriptor.value_type)

    if descriptor.kind == "scalar":
        # Build Django JSON lookup path
        json_lookup = [
            "last_scan_cache",
            descriptor.section,
            descriptor.artefact_key,
            *descriptor.field_path,
        ]
        lookup = "__".join(json_lookup)

        # Apply operator
        if criterion.operator == "eq":
            if descriptor.value_type == "string":
                return qs.filter(**{f"{lookup}__iexact": value})
            else:
                return qs.filter(**{lookup: value})
        elif criterion.operator == "contains":
            if descriptor.value_type == "string":
                return qs.filter(**{f"{lookup}__icontains": value})
            else:
                # contains doesn't make sense for non-strings, treat as eq
                return qs.filter(**{lookup: value})
        elif criterion.operator == "gt":
            return qs.filter(**{f"{lookup}__gt": value})
        elif criterion.operator == "gte":
            return qs.filter(**{f"{lookup}__gte": value})
        elif criterion.operator == "lt":
            return qs.filter(**{f"{lookup}__lt": value})
        elif criterion.operator == "lte":
            return qs.filter(**{f"{lookup}__lte": value})
        else:
            # Unknown operator, treat as eq
            return qs.filter(**{lookup: value})
    else:
        # Array search: support arrays at any depth (including nested arrays)
        section = descriptor.section
        artefact = descriptor.artefact_key
        array_path = descriptor.array_path or ("[]",)
        elem_field_path = descriptor.element_field_path or ()

        # Build FROM clause(s) by progressively expanding arrays
        params: list[Any] = [section, artefact]
        expr = "\"hosts_host\".\"last_scan_cache\"->%s->%s"
        from_clauses: list[str] = []
        level = 0
        for token in array_path:
            if token == "[]":
                alias = f"e{level}"
                from_clauses.append(f"jsonb_array_elements({expr}) AS {alias}")
                expr = alias
                level += 1
            else:
                expr = f"{expr}->%s"
                params.append(token)

        # Ensure at least one array expansion (in case array_path omitted [] by mistake)
        if not from_clauses:
            alias = f"e{level}"
            from_clauses.append(f"jsonb_array_elements({expr}) AS {alias}")
            expr = alias

        # Navigate inside element if needed
        text_expr: str
        if elem_field_path:
            # Build elem->'a'->'b' and then ->>lastkey for text
            if len(elem_field_path) == 1:
                text_expr = f"{expr}->>%s"
                params.append(elem_field_path[0])
            else:
                # Build chain elem->'a'->'b' then ->>'c'
                for key in elem_field_path[:-1]:
                    expr = f"{expr}->%s"
                    params.append(key)
                text_expr = f"{expr}->>%s"
                params.append(elem_field_path[-1])
        else:
            # Element itself is primitive
            text_expr = f"{expr}::text"

        # Build WHERE clause based on operator
        if descriptor.value_type == "string":
            if not elem_field_path:
                # primitive element: strip quotes when it's a JSON string
                text_for_compare = (
                    f"CASE WHEN jsonb_typeof({expr})='string' "
                    f"THEN trim(both '" + '"' + f"' from {expr}::text) "
                    f"ELSE {expr}::text END"
                )
                if criterion.operator == "contains":
                    where = f"{text_for_compare} ILIKE %s"
                    params.append(f"%{value}%")
                elif criterion.operator == "eq":
                    where = f"LOWER({text_for_compare}) = LOWER(%s)"
                    params.append(str(value))
                else:
                    # Comparison operators for strings
                    where = f"{text_for_compare} {_operator_to_sql(criterion.operator)} %s"
                    params.append(str(value))
            else:
                if criterion.operator == "contains":
                    where = f"{text_expr} ILIKE %s"
                    params.append(f"%{value}%")
                elif criterion.operator == "eq":
                    where = f"LOWER({text_expr}) = LOWER(%s)"
                    params.append(str(value))
                else:
                    where = f"{text_expr} {_operator_to_sql(criterion.operator)} %s"
                    params.append(str(value))
        else:
            # Integer/boolean: use operator directly
            if criterion.operator == "contains":
                # contains doesn't make sense for non-strings, treat as eq
                where = f"{text_expr} = %s"
            else:
                where = f"{text_expr} {_operator_to_sql(criterion.operator)} %s"
            params.append(str(value))

        from_sql = " CROSS JOIN LATERAL ".join(from_clauses)
        query = f"SELECT 1 FROM {from_sql} WHERE {where} LIMIT 1"
        return qs.annotate(_match=RawSQL(query, params)).filter(_match__isnull=False)


def _apply_complex_query_to_queryset(
    qs: QuerySet[Host],
    query: ComplexQuery,
    fields_by_id: dict[str, SearchableField],
) -> QuerySet[Host]:
    """Recursively apply a complex query to a QuerySet."""
    if query.type == "criterion":
        if query.criterion is None:
            return qs
        descriptor = fields_by_id.get(query.criterion.field_id)
        if descriptor is None:
            return qs
        return _apply_criterion_to_queryset(qs, query.criterion, descriptor)
    elif query.type == "and":
        if not query.children:
            return qs
        for child in query.children:
            qs = _apply_complex_query_to_queryset(qs, child, fields_by_id)
        return qs
    elif query.type == "or":
        if not query.children:
            return qs
        # Build Q objects for OR combination
        q_objects = []
        for child in query.children:
            # Get filtered IDs for this child
            child_qs = _apply_complex_query_to_queryset(Host.objects.all(), child, fields_by_id)
            child_ids = list(child_qs.values_list('id', flat=True))
            if child_ids:
                q_objects.append(Q(id__in=child_ids))
        if q_objects:
            combined_q = q_objects[0]
            for q_obj in q_objects[1:]:
                combined_q |= q_obj
            return qs.filter(combined_q)
        return qs.none()
    else:
        return qs


def search_hosts_by_scan_fields(
    qs: QuerySet[Host],
    criteria: Mapping[str, Any] | ComplexQuery | None = None,
) -> QuerySet:
    """
    Filter a Host queryset by searching values within last_scan_cache JSON fields.

    Supports three input formats:

    1. Simple dict (backward compatible): mapping from SearchableField.id to value.
       All criteria are combined using AND semantics.
       - string values: case-insensitive substring match (contains)
       - integer/bool: exact match (eq)
       Example: {"facts.cpu.count": 4, "facts.os.name": "Ubuntu"}

    2. Dict with operators: mapping from SearchableField.id to dict with "operator" and "value".
       Example: {"facts.cpu.count": {"operator": "gte", "value": 4}}

    3. ComplexQuery object: for advanced AND/OR combinations.
       Example: ComplexQuery(type="or", children=[
           ComplexQuery(type="criterion", criterion=SearchCriterion(...)),
           ComplexQuery(type="and", children=[...])
       ])
    """
    if criteria is None or (isinstance(criteria, dict) and not criteria):
        return qs

    # Build a map from id to descriptor for quick lookup
    fields_by_id = {field.id: field for field in get_searchable_fields()}

    # Handle ComplexQuery directly
    if isinstance(criteria, ComplexQuery):
        return _apply_complex_query_to_queryset(qs, criteria, fields_by_id)

    # Handle dict-based criteria (simple or with operators)
    for field_id, raw_value in criteria.items():
        descriptor = fields_by_id.get(field_id)
        if descriptor is None:
            # Unknown field id; ignore silently
            continue

        # Determine operator and value
        if isinstance(raw_value, dict) and "operator" in raw_value and "value" in raw_value:
            # Format: {"operator": "gte", "value": 4}
            operator = raw_value["operator"]
            value = raw_value["value"]
        else:
            # Simple format: use default operators
            value = raw_value
            operator = "contains" if descriptor.value_type == "string" else "eq"

        # Create criterion and apply
        criterion = SearchCriterion(
            field_id=field_id,
            operator=operator,  # type: ignore[arg-type]
            value=value,
        )
        qs = _apply_criterion_to_queryset(qs, criterion, descriptor)

    return qs
