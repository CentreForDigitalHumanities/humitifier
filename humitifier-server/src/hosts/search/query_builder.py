"""Query building and filtering logic for host searches."""

from __future__ import annotations

from typing import Any, Mapping

from django.db.models import Q, QuerySet
from django.db.models.expressions import RawSQL

from ..models import Host
from .field_discovery import get_searchable_fields
from .types import AggregationFunction, ComplexQuery, ComparisonOperator, SearchableField, SearchCriterion


def _parse_value(value: Any, value_type: str) -> Any:
    """
    Parse and convert a search value to the appropriate Python type.

    Args:
        value: The raw value to parse (can be string, int, bool, etc.).
        value_type: The target type ("integer", "boolean", or "string").

    Returns:
        The parsed value in the appropriate type, or the original value if parsing fails.
    """
    if value_type == "integer":
        try:
            return int(value)
        except Exception:
            return value
    if value_type == "boolean":
        if isinstance(value, bool):
            return value
        string_value = str(value).strip().lower()
        if string_value in {"true", "1", "yes", "y", "on"}:
            return True
        if string_value in {"false", "0", "no", "n", "off"}:
            return False
        return value
    # string type
    return str(value)


def _operator_to_sql(operator: ComparisonOperator) -> str:
    """
    Convert a ComparisonOperator to its SQL equivalent.

    Args:
        operator: The comparison operator enum value.

    Returns:
        The SQL operator string (e.g., "=", ">", ">=", etc.).
        Defaults to "=" for unknown operators.
    """
    operator_mapping = {
        "eq": "=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "contains": "ILIKE",  # Fallback; usually handled specially for case-insensitive matching
    }
    return operator_mapping.get(operator, "=")


def _build_json_lookup_path(descriptor: SearchableField) -> str:
    """
    Build a Django JSON field lookup path from a SearchableField descriptor.

    Note: This should only be called for facts/metrics sections, not meta.

    Args:
        descriptor: The searchable field descriptor containing section, artefact, and field path.

    Returns:
        A Django ORM-compatible lookup string (e.g., "last_scan_cache__facts__cpu__count").
    """
    json_path_components = [
        "last_scan_cache",
        descriptor.section,
        descriptor.artefact_key,
        *descriptor.field_path,
    ]
    return "__".join(json_path_components)


def _apply_meta_filter(
    queryset: QuerySet[Host],
    criterion: SearchCriterion,
    descriptor: SearchableField,
    parsed_value: Any,
) -> QuerySet[Host]:
    """
    Apply a filter for meta fields (direct Host model fields).

    Args:
        queryset: The Django QuerySet to filter.
        criterion: The search criterion containing the operator.
        descriptor: The searchable field descriptor for a meta field.
        parsed_value: The value to filter by, already parsed to the correct type.

    Returns:
        Filtered QuerySet.
    """
    # Meta fields are directly on the Host model
    field_name = descriptor.field_path[0] if descriptor.field_path else None
    if not field_name:
        return queryset

    is_string_field = descriptor.value_type == "string"

    if criterion.operator == "eq":
        lookup_suffix = "__iexact" if is_string_field else ""
        return queryset.filter(**{f"{field_name}{lookup_suffix}": parsed_value})
    elif criterion.operator == "contains":
        if is_string_field:
            return queryset.filter(**{f"{field_name}__icontains": parsed_value})
        else:
            # Contains doesn't make sense for non-strings, treat as exact match
            return queryset.filter(**{field_name: parsed_value})
    elif criterion.operator == "gt":
        return queryset.filter(**{f"{field_name}__gt": parsed_value})
    elif criterion.operator == "gte":
        return queryset.filter(**{f"{field_name}__gte": parsed_value})
    elif criterion.operator == "lt":
        return queryset.filter(**{f"{field_name}__lt": parsed_value})
    elif criterion.operator == "lte":
        return queryset.filter(**{f"{field_name}__lte": parsed_value})
    else:
        # Unknown operator, treat as exact match
        return queryset.filter(**{field_name: parsed_value})


def _apply_scalar_filter(
    queryset: QuerySet[Host],
    criterion: SearchCriterion,
    descriptor: SearchableField,
    parsed_value: Any,
) -> QuerySet[Host]:
    """
    Apply a filter for scalar (non-array) fields using Django ORM lookups.

    Args:
        queryset: The Django QuerySet to filter.
        criterion: The search criterion containing the operator.
        descriptor: The searchable field descriptor.
        parsed_value: The value to filter by, already parsed to the correct type.

    Returns:
        Filtered QuerySet.
    """
    lookup_path = _build_json_lookup_path(descriptor)
    is_string_field = descriptor.value_type == "string"

    if criterion.operator == "eq":
        lookup_suffix = "__iexact" if is_string_field else ""
        return queryset.filter(**{f"{lookup_path}{lookup_suffix}": parsed_value})
    elif criterion.operator == "contains":
        if is_string_field:
            return queryset.filter(**{f"{lookup_path}__icontains": parsed_value})
        else:
            # Contains doesn't make sense for non-strings, treat as exact match
            return queryset.filter(**{lookup_path: parsed_value})
    elif criterion.operator == "gt":
        return queryset.filter(**{f"{lookup_path}__gt": parsed_value})
    elif criterion.operator == "gte":
        return queryset.filter(**{f"{lookup_path}__gte": parsed_value})
    elif criterion.operator == "lt":
        return queryset.filter(**{f"{lookup_path}__lt": parsed_value})
    elif criterion.operator == "lte":
        return queryset.filter(**{f"{lookup_path}__lte": parsed_value})
    else:
        # Unknown operator, treat as exact match
        return queryset.filter(**{lookup_path: parsed_value})


def _build_array_expansion_clauses(
    array_path: tuple[str, ...],
    initial_params: list[Any],
) -> tuple[list[str], str, int]:
    """
    Build SQL FROM clauses for expanding JSONB arrays at multiple levels.

    This function generates the necessary LATERAL joins to expand nested JSON arrays,
    allowing queries to search within array elements at any depth.

    Args:
        array_path: Tuple of path tokens, where "[]" indicates array expansion.
        initial_params: List to append parameter values to for the SQL query.

    Returns:
        Tuple of (from_clauses, final_expression, nesting_level):
        - from_clauses: List of SQL FROM clause strings for LATERAL joins.
        - final_expression: The SQL expression after all expansions.
        - nesting_level: The depth of array nesting.
    """
    base_expression = "\"hosts_host\".\"last_scan_cache\"->%s->%s"
    current_expression = base_expression
    from_clauses: list[str] = []
    nesting_level = 0

    for path_token in array_path:
        if path_token == "[]":
            # Expand the current expression as a JSONB array
            element_alias = f"e{nesting_level}"
            from_clauses.append(f"jsonb_array_elements({current_expression}) AS {element_alias}")
            current_expression = element_alias
            nesting_level += 1
        else:
            # Navigate deeper into the JSON structure
            current_expression = f"{current_expression}->%s"
            initial_params.append(path_token)

    # Ensure at least one array expansion exists
    if not from_clauses:
        element_alias = f"e{nesting_level}"
        from_clauses.append(f"jsonb_array_elements({current_expression}) AS {element_alias}")
        current_expression = element_alias

    return from_clauses, current_expression, nesting_level


def _build_element_field_expression(
    element_expression: str,
    element_field_path: tuple[str, ...],
    sql_params: list[Any],
) -> str:
    """
    Build a SQL expression to extract a specific field from a JSONB array element.

    Args:
        element_expression: The SQL expression representing the current array element.
        element_field_path: Path to navigate within the array element to reach the target field.
        sql_params: List to append parameter values to for the SQL query.

    Returns:
        SQL expression that extracts the field value as text.
    """
    if not element_field_path:
        # Element itself is a primitive value
        return f"{element_expression}::text"

    if len(element_field_path) == 1:
        # Single-level access: element->>'field'
        sql_params.append(element_field_path[0])
        return f"{element_expression}->>%s"

    # Multi-level access: element->'a'->'b'->>'c'
    current_expr = element_expression
    for field_key in element_field_path[:-1]:
        current_expr = f"{current_expr}->%s"
        sql_params.append(field_key)

    sql_params.append(element_field_path[-1])
    return f"{current_expr}->>%s"


def _build_array_where_clause(
    criterion: SearchCriterion,
    descriptor: SearchableField,
    text_expression: str,
    element_expression: str,
    has_element_field_path: bool,
    parsed_value: Any,
    sql_params: list[Any],
) -> str:
    """
    Build the WHERE clause for array field searches based on the operator and value type.

    Args:
        criterion: The search criterion containing the operator.
        descriptor: The searchable field descriptor.
        text_expression: SQL expression for extracting the field value as text.
        element_expression: SQL expression for the current array element.
        has_element_field_path: Whether we're accessing a nested field within elements.
        parsed_value: The search value, already parsed to the correct type.
        sql_params: List to append parameter values to for the SQL query.

    Returns:
        SQL WHERE clause string.
    """
    is_string_field = descriptor.value_type == "string"

    if is_string_field:
        if not has_element_field_path:
            # For primitive string elements, strip JSON quotes if present
            comparison_expression = (
                f"CASE WHEN jsonb_typeof({element_expression})='string' "
                f"THEN trim(both '" + '"' + f"' from {element_expression}::text) "
                f"ELSE {element_expression}::text END"
            )

            if criterion.operator == "contains":
                sql_params.append(f"%{parsed_value}%")
                return f"{comparison_expression} ILIKE %s"
            elif criterion.operator == "eq":
                sql_params.append(str(parsed_value))
                return f"LOWER({comparison_expression}) = LOWER(%s)"
            else:
                sql_params.append(str(parsed_value))
                sql_operator = _operator_to_sql(criterion.operator)
                return f"{comparison_expression} {sql_operator} %s"
        else:
            # For nested fields within elements
            if criterion.operator == "contains":
                sql_params.append(f"%{parsed_value}%")
                return f"{text_expression} ILIKE %s"
            elif criterion.operator == "eq":
                sql_params.append(str(parsed_value))
                return f"LOWER({text_expression}) = LOWER(%s)"
            else:
                sql_params.append(str(parsed_value))
                sql_operator = _operator_to_sql(criterion.operator)
                return f"{text_expression} {sql_operator} %s"
    else:
        # For integer/boolean fields
        if criterion.operator == "contains":
            # Contains doesn't make sense for non-strings, treat as exact match
            sql_params.append(str(parsed_value))
            return f"{text_expression} = %s"
        else:
            sql_params.append(str(parsed_value))
            sql_operator = _operator_to_sql(criterion.operator)
            return f"{text_expression} {sql_operator} %s"


def _build_aggregation_expression(
    aggregation: AggregationFunction,
    element_expr: str,
    element_field_path: tuple[str, ...],
    sql_params: list[Any],
    value_type: str,
) -> str:
    """
    Build a SQL aggregation expression for an array field.

    Args:
        aggregation: The aggregation function to apply (min, max, sum, concat, count)
        element_expr: The SQL expression representing the current array element
        element_field_path: Path to navigate within the array element to reach the target field
        sql_params: List to append parameter values to for the SQL query
        value_type: The value type of the field (string, integer, boolean)

    Returns:
        SQL expression that performs the aggregation
    """
    # Build expression to access field value
    if not element_field_path:
        # Element itself is a primitive value
        field_value_expr = f"{element_expr}::text"
    elif len(element_field_path) == 1:
        sql_params.append(element_field_path[0])
        field_value_expr = f"{element_expr}->>%s"
    else:
        current_expr = element_expr
        for field_key in element_field_path[:-1]:
            current_expr = f"{current_expr}->%s"
            sql_params.append(field_key)
        sql_params.append(element_field_path[-1])
        field_value_expr = f"{current_expr}->>%s"

    # Apply aggregation based on function and type
    if aggregation == "count":
        return f"COUNT({field_value_expr})"
    elif aggregation == "min":
        if value_type == "integer":
            return f"MIN(({field_value_expr})::numeric)"
        else:
            return f"MIN({field_value_expr})"
    elif aggregation == "max":
        if value_type == "integer":
            return f"MAX(({field_value_expr})::numeric)"
        else:
            return f"MAX({field_value_expr})"
    elif aggregation == "sum":
        if value_type == "integer":
            return f"SUM(({field_value_expr})::numeric)"
        else:
            raise ValueError(f"SUM aggregation only supported for integer fields")
    elif aggregation == "concat":
        if value_type == "string":
            return f"STRING_AGG({field_value_expr}, ', ')"
        else:
            raise ValueError(f"CONCAT aggregation only supported for string fields")
    else:
        raise ValueError(f"Unknown aggregation function: {aggregation}")


def _apply_array_aggregation_filter(
    queryset: QuerySet[Host],
    criterion: SearchCriterion,
    descriptor: SearchableField,
    parsed_value: Any,
) -> QuerySet[Host]:
    """
    Apply a filter for array fields with aggregation functions using raw SQL.

    This function handles aggregations like min(), max(), sum(), concat(), count()
    on array fields by constructing a subquery with appropriate aggregation.

    Args:
        queryset: The Django QuerySet to filter.
        criterion: The search criterion containing the operator and aggregation.
        descriptor: The searchable field descriptor for an array field.
        parsed_value: The value to filter by, already parsed to the correct type.

    Returns:
        Filtered QuerySet using a RawSQL annotation.
    """
    section_name = descriptor.section
    artefact_name = descriptor.artefact_key
    array_path = descriptor.array_path or ("[]",)
    element_field_path = descriptor.element_field_path or ()
    aggregation = criterion.aggregation

    if not aggregation:
        raise ValueError("_apply_array_aggregation_filter called without aggregation")

    # Initialize SQL parameters with section and artefact
    sql_params: list[Any] = [section_name, artefact_name]

    # Build the LATERAL join clauses for array expansion
    from_clauses, element_expr, _ = _build_array_expansion_clauses(array_path, sql_params)

    # Build the aggregation expression
    agg_expr = _build_aggregation_expression(
        aggregation,
        element_expr,
        element_field_path,
        sql_params,
        descriptor.value_type,
    )

    # Build the comparison
    sql_operator = _operator_to_sql(criterion.operator)

    # For string comparisons (concat result), use case-insensitive comparison
    if aggregation == "concat" and criterion.operator == "eq":
        sql_params.append(str(parsed_value))
        having_clause = f"LOWER({agg_expr}) = LOWER(%s)"
    elif aggregation == "concat" and criterion.operator == "contains":
        sql_params.append(f"%{parsed_value}%")
        having_clause = f"{agg_expr} ILIKE %s"
    else:
        sql_params.append(str(parsed_value))
        having_clause = f"{agg_expr} {sql_operator} %s"

    # Construct the complete SQL subquery with GROUP BY and HAVING
    from_sql = " CROSS JOIN LATERAL ".join(from_clauses)
    subquery = f"SELECT 1 FROM {from_sql} GROUP BY \"hosts_host\".\"id\" HAVING {having_clause} LIMIT 1"

    return queryset.annotate(_match=RawSQL(subquery, sql_params)).filter(_match__isnull=False)


def _apply_array_filter(
    queryset: QuerySet[Host],
    criterion: SearchCriterion,
    descriptor: SearchableField,
    parsed_value: Any,
) -> QuerySet[Host]:
    """
    Apply a filter for array fields using raw SQL with LATERAL joins.

    This function handles searching within JSON arrays, including nested arrays,
    by constructing a subquery with appropriate LATERAL joins and WHERE conditions.
    If the criterion includes an aggregation, it delegates to _apply_array_aggregation_filter.

    Args:
        queryset: The Django QuerySet to filter.
        criterion: The search criterion containing the operator.
        descriptor: The searchable field descriptor for an array field.
        parsed_value: The value to filter by, already parsed to the correct type.

    Returns:
        Filtered QuerySet using a RawSQL annotation.
    """
    # Check if this is an aggregation query
    if criterion.aggregation:
        return _apply_array_aggregation_filter(queryset, criterion, descriptor, parsed_value)

    section_name = descriptor.section
    artefact_name = descriptor.artefact_key
    array_path = descriptor.array_path or ("[]",)
    element_field_path = descriptor.element_field_path or ()

    # Initialize SQL parameters with section and artefact
    sql_params: list[Any] = [section_name, artefact_name]

    # Build the LATERAL join clauses for array expansion
    from_clauses, element_expr, _ = _build_array_expansion_clauses(array_path, sql_params)

    # Build expression to access the target field within array elements
    text_expr = _build_element_field_expression(element_expr, element_field_path, sql_params)

    # Build the WHERE clause based on the operator and value type
    where_clause = _build_array_where_clause(
        criterion,
        descriptor,
        text_expr,
        element_expr,
        bool(element_field_path),
        parsed_value,
        sql_params,
    )

    # Construct the complete SQL subquery
    from_sql = " CROSS JOIN LATERAL ".join(from_clauses)
    subquery = f"SELECT 1 FROM {from_sql} WHERE {where_clause} LIMIT 1"

    return queryset.annotate(_match=RawSQL(subquery, sql_params)).filter(_match__isnull=False)


def _apply_criterion_to_queryset(
    queryset: QuerySet[Host],
    criterion: SearchCriterion,
    descriptor: SearchableField,
) -> QuerySet[Host]:
    """
    Apply a single search criterion to a QuerySet, supporting meta fields, scalar, and array fields.

    This function routes to the appropriate filter implementation based on whether
    the field is a meta field (direct Host model field), a scalar JSON field, or an array field.

    Args:
        queryset: The Django QuerySet to filter.
        criterion: The search criterion containing field_id, operator, and value.
        descriptor: The searchable field descriptor containing field metadata.

    Returns:
        Filtered QuerySet with the criterion applied.
    """
    # Validate aggregation usage
    if criterion.aggregation and descriptor.kind != "array":
        raise ValueError(
            f"Aggregation functions can only be used with array fields. "
            f"Field '{criterion.field_id}' is a {descriptor.kind} field."
        )

    parsed_value = _parse_value(criterion.value, descriptor.value_type)

    # Handle meta fields (direct Host model fields)
    if descriptor.section == "meta":
        return _apply_meta_filter(queryset, criterion, descriptor, parsed_value)
    # Handle scan cache fields
    elif descriptor.kind == "scalar":
        return _apply_scalar_filter(queryset, criterion, descriptor, parsed_value)
    else:
        return _apply_array_filter(queryset, criterion, descriptor, parsed_value)


def _combine_q_objects_with_or(q_objects: list[Q]) -> Q:
    """
    Combine multiple Django Q objects using OR logic.

    Args:
        q_objects: List of Q objects to combine.

    Returns:
        A single Q object representing the OR combination of all input Q objects.
    """
    if not q_objects:
        raise ValueError("Cannot combine empty list of Q objects")

    combined_q = q_objects[0]
    for q_object in q_objects[1:]:
        combined_q |= q_object
    return combined_q


def _apply_or_query(
    queryset: QuerySet[Host],
    query: ComplexQuery,
    fields_by_id: dict[str, SearchableField],
) -> QuerySet[Host]:
    """
    Apply an OR query by evaluating each child query and combining results.

    This function evaluates each child query independently to get matching host IDs,
    then combines them using OR logic (union of results).

    Args:
        queryset: The Django QuerySet to filter.
        query: The ComplexQuery object with type="or".
        fields_by_id: Mapping of field IDs to their descriptors.

    Returns:
        Filtered QuerySet containing hosts that match any of the child queries.
    """
    if not query.children:
        return queryset

    q_objects = []
    for child_query in query.children:
        # Evaluate each child query independently to get matching IDs
        child_queryset = _apply_complex_query_to_queryset(
            Host.objects.all(), child_query, fields_by_id
        )
        matching_ids = list(child_queryset.values_list('id', flat=True))
        if matching_ids:
            q_objects.append(Q(id__in=matching_ids))

    if q_objects:
        combined_q = _combine_q_objects_with_or(q_objects)
        return queryset.filter(combined_q)

    return queryset.none()


def _apply_and_query(
    queryset: QuerySet[Host],
    query: ComplexQuery,
    fields_by_id: dict[str, SearchableField],
) -> QuerySet[Host]:
    """
    Apply an AND query by evaluating each child query sequentially.

    Each child query filters the queryset further, ensuring all conditions are met.

    Args:
        queryset: The Django QuerySet to filter.
        query: The ComplexQuery object with type="and".
        fields_by_id: Mapping of field IDs to their descriptors.

    Returns:
        Filtered QuerySet containing hosts that match all child queries.
    """
    if not query.children:
        return queryset

    for child_query in query.children:
        queryset = _apply_complex_query_to_queryset(queryset, child_query, fields_by_id)

    return queryset


def _apply_criterion_query(
    queryset: QuerySet[Host],
    query: ComplexQuery,
    fields_by_id: dict[str, SearchableField],
) -> QuerySet[Host]:
    """
    Apply a criterion query (leaf node in the query tree).

    Args:
        queryset: The Django QuerySet to filter.
        query: The ComplexQuery object with type="criterion".
        fields_by_id: Mapping of field IDs to their descriptors.

    Returns:
        Filtered QuerySet with the criterion applied, or the original queryset if invalid.
    """
    if query.criterion is None:
        return queryset

    field_descriptor = fields_by_id.get(query.criterion.field_id)
    if field_descriptor is None:
        return queryset

    return _apply_criterion_to_queryset(queryset, query.criterion, field_descriptor)


def _apply_complex_query_to_queryset(
    queryset: QuerySet[Host],
    query: ComplexQuery,
    fields_by_id: dict[str, SearchableField],
) -> QuerySet[Host]:
    """
    Recursively apply a complex query structure to a QuerySet.

    This function handles the three types of query nodes:
    - "criterion": A single search condition (leaf node)
    - "and": Logical AND of multiple child queries
    - "or": Logical OR of multiple child queries

    Args:
        queryset: The Django QuerySet to filter.
        query: The ComplexQuery object representing the query structure.
        fields_by_id: Mapping of field IDs to their searchable field descriptors.

    Returns:
        Filtered QuerySet matching the complex query criteria.
    """
    if query.type == "criterion":
        return _apply_criterion_query(queryset, query, fields_by_id)
    elif query.type == "and":
        return _apply_and_query(queryset, query, fields_by_id)
    elif query.type == "or":
        return _apply_or_query(queryset, query, fields_by_id)
    else:
        return queryset


def search_hosts_by_scan_fields(
    queryset: QuerySet[Host],
    criteria: Mapping[str, Any] | ComplexQuery | None = None,
) -> QuerySet:
    """
    Filter a Host queryset by searching values within Host model fields and last_scan_cache JSON fields.

    This function supports searching across three sections:
    - "meta": Direct Host model fields (e.g., "meta.fqdn", "meta.department")
    - "facts": Fields from last_scan_cache facts section
    - "metrics": Fields from last_scan_cache metrics section

    Supports three input formats:

    1. Simple dict (backward compatible): mapping from SearchableField.id to value.
       All criteria are combined using AND semantics.
       - string values: case-insensitive substring match (contains)
       - integer/bool: exact match (eq)
       Example: {"facts.cpu.count": 4, "meta.department": "Engineering"}

    2. Dict with operators: mapping from SearchableField.id to dict with "operator" and "value".
       Example: {"facts.cpu.count": {"operator": "gte", "value": 4}, "meta.archived": {"operator": "eq", "value": False}}

    3. ComplexQuery object: for advanced AND/OR combinations.
       Example: ComplexQuery(type="or", children=[
           ComplexQuery(type="criterion", criterion=SearchCriterion(...)),
           ComplexQuery(type="and", children=[...])
       ])

    Args:
        queryset: The initial Host QuerySet to filter.
        criteria: The search criteria (dict or ComplexQuery), or None for no filtering.

    Returns:
        Filtered QuerySet of Host objects matching the criteria.
    """
    if criteria is None or (isinstance(criteria, dict) and not criteria):
        return queryset

    # Build a mapping from field ID to descriptor for efficient lookup
    fields_by_id = {field.id: field for field in get_searchable_fields()}

    # Handle ComplexQuery directly (format 3)
    if isinstance(criteria, ComplexQuery):
        return _apply_complex_query_to_queryset(queryset, criteria, fields_by_id)

    # Handle dict-based criteria (formats 1 and 2)
    for field_id, raw_value in criteria.items():
        field_descriptor = fields_by_id.get(field_id)
        if field_descriptor is None:
            # Unknown field ID; skip silently to allow partial matches
            continue

        # Determine operator and value based on input format
        if isinstance(raw_value, dict) and "operator" in raw_value and "value" in raw_value:
            # Format 2: Explicit operator specification
            search_operator = raw_value["operator"]
            search_value = raw_value["value"]
        else:
            # Format 1: Simple value with default operator
            search_value = raw_value
            search_operator = "contains" if field_descriptor.value_type == "string" else "eq"

        # Create a SearchCriterion and apply it to the queryset
        criterion = SearchCriterion(
            field_id=field_id,
            operator=search_operator,  # type: ignore[arg-type]
            value=search_value,
        )
        queryset = _apply_criterion_to_queryset(queryset, criterion, field_descriptor)

    return queryset
