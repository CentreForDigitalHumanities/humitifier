"""Query building and filtering logic for host searches."""

from __future__ import annotations

from typing import Any

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
) -> tuple[list[str], str, int, str | None, list[Any]]:
    """
    Build SQL FROM clauses for expanding JSONB arrays at multiple levels.

    This function generates the necessary LATERAL joins to expand nested JSON arrays,
    allowing queries to search within array elements at any depth.

    Args:
        array_path: Tuple of path tokens, where "[]" indicates array expansion.
        initial_params: List to append parameter values to for the SQL query.

    Returns:
        Tuple of (from_clauses, final_expression, nesting_level, type_check_clause, type_check_params):
        - from_clauses: List of SQL FROM clause strings for LATERAL joins.
        - final_expression: The SQL expression after all expansions.
        - nesting_level: The depth of array nesting.
        - type_check_clause: Optional WHERE clause to ensure the first expression is an array.
        - type_check_params: Parameters needed for the type_check_clause.
    """
    base_expression = "\"hosts_host\".\"last_scan_cache\"->%s->%s"
    current_expression = base_expression
    from_clauses: list[str] = []
    nesting_level = 0
    type_check_clause = None
    type_check_params: list[Any] = []
    first_array_expression = None
    params_before_first_array: list[Any] = []

    for path_token in array_path:
        if path_token == "[]":
            # Expand the current expression as a JSONB array
            element_alias = f"e{nesting_level}"
            # Track the first array expression for type checking
            if first_array_expression is None:
                first_array_expression = current_expression
                # Save the parameters accumulated so far for the type check
                params_before_first_array = initial_params.copy()
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
        first_array_expression = current_expression
        params_before_first_array = initial_params.copy()
        from_clauses.append(f"jsonb_array_elements({current_expression}) AS {element_alias}")
        current_expression = element_alias

    # Add type check for the first array expression to prevent scalar errors
    if first_array_expression:
        type_check_clause = f"jsonb_typeof({first_array_expression}) = 'array'"
        type_check_params = params_before_first_array

    return from_clauses, current_expression, nesting_level, type_check_clause, type_check_params


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
    element_field_path: tuple[str, ...] | None = None,
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
        element_field_path: The field path for rebuilding text expression params if needed.

    Returns:
        SQL WHERE clause string.
    """
    is_string_field = descriptor.value_type == "string"
    where_clauses = []

    # Add filter pattern clause if provided
    if criterion.filter_pattern:
        sql_params.append(criterion.filter_pattern)
        where_clauses.append(f"{text_expression} ~ %s")

        # If we're using the filter, we'll use text_expression again in the comparison below
        # So we need to add its parameters again
        if element_field_path:
            # Re-add the field path parameters for the second use of text_expression
            if len(element_field_path) == 1:
                sql_params.append(element_field_path[0])
            else:
                for field_key in element_field_path:
                    sql_params.append(field_key)

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
                where_clauses.append(f"{comparison_expression} ILIKE %s")
            elif criterion.operator == "eq":
                sql_params.append(str(parsed_value))
                where_clauses.append(f"LOWER({comparison_expression}) = LOWER(%s)")
            else:
                sql_params.append(str(parsed_value))
                sql_operator = _operator_to_sql(criterion.operator)
                where_clauses.append(f"{comparison_expression} {sql_operator} %s")
        else:
            # For nested fields within elements
            if criterion.operator == "contains":
                sql_params.append(f"%{parsed_value}%")
                where_clauses.append(f"{text_expression} ILIKE %s")
            elif criterion.operator == "eq":
                sql_params.append(str(parsed_value))
                where_clauses.append(f"LOWER({text_expression}) = LOWER(%s)")
            else:
                sql_params.append(str(parsed_value))
                sql_operator = _operator_to_sql(criterion.operator)
                where_clauses.append(f"{text_expression} {sql_operator} %s")
    else:
        # For integer/boolean fields
        if criterion.operator == "contains":
            # Contains doesn't make sense for non-strings, treat as exact match
            sql_params.append(str(parsed_value))
            where_clauses.append(f"{text_expression} = %s")
        else:
            sql_params.append(str(parsed_value))
            sql_operator = _operator_to_sql(criterion.operator)
            where_clauses.append(f"{text_expression} {sql_operator} %s")

    return " AND ".join(where_clauses)


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
    from_clauses, element_expr, _, type_check, type_check_params = _build_array_expansion_clauses(array_path, sql_params)

    # Prepare list to collect WHERE clause params in order
    where_params: list[Any] = []
    where_clauses = []

    # Add type check to prevent scalar errors
    if type_check:
        where_clauses.append(type_check)
        where_params.extend(type_check_params)

    if criterion.filter_pattern:
        # Build text expression for filtering (this adds params to a temp list)
        temp_params: list[Any] = []
        text_expr_for_filter = _build_element_field_expression(element_expr, element_field_path, temp_params)
        where_clauses.append(f"{text_expr_for_filter} ~ %s")
        where_params.extend(temp_params)
        where_params.append(criterion.filter_pattern)

    # Build the aggregation expression (this also adds params to a temp list)
    agg_params: list[Any] = []
    agg_expr = _build_aggregation_expression(
        aggregation,
        element_expr,
        element_field_path,
        agg_params,
        descriptor.value_type,
    )

    # Build the comparison
    sql_operator = _operator_to_sql(criterion.operator)

    # For string comparisons (concat result), use case-insensitive comparison
    if aggregation == "concat" and criterion.operator == "eq":
        having_clause = f"LOWER({agg_expr}) = LOWER(%s)"
        having_params = agg_params + [str(parsed_value)]
    elif aggregation == "concat" and criterion.operator == "contains":
        having_clause = f"{agg_expr} ILIKE %s"
        having_params = agg_params + [f"%{parsed_value}%"]
    else:
        having_clause = f"{agg_expr} {sql_operator} %s"
        having_params = agg_params + [str(parsed_value)]

    # Construct the complete SQL subquery with GROUP BY and HAVING
    # Final param order: FROM params, WHERE params, HAVING params
    final_params = sql_params + where_params + having_params
    from_sql = " CROSS JOIN LATERAL ".join(from_clauses)
    if where_clauses:
        where_sql = " AND ".join(where_clauses)
        subquery = f"SELECT 1 FROM {from_sql} WHERE {where_sql} GROUP BY \"hosts_host\".\"id\" HAVING {having_clause} LIMIT 1"
    else:
        subquery = f"SELECT 1 FROM {from_sql} GROUP BY \"hosts_host\".\"id\" HAVING {having_clause} LIMIT 1"

    return queryset.annotate(_match=RawSQL(subquery, final_params)).filter(_match__isnull=False)


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
    from_clauses, element_expr, _, type_check, type_check_params = _build_array_expansion_clauses(array_path, sql_params)

    # Prepare list to collect WHERE clause params in order
    where_params: list[Any] = []

    # Add type check params first if needed
    if type_check:
        where_params.extend(type_check_params)

    # Build expression to access the target field within array elements
    # Pass where_params so text_expr params get added directly
    text_expr = _build_element_field_expression(element_expr, element_field_path, where_params)

    # Build the WHERE clause based on the operator and value type
    # Note: where_clause may use text_expr multiple times (for filter AND for comparison)
    # so we need to track how many times it's used and duplicate the parameters
    where_clause = _build_array_where_clause(
        criterion,
        descriptor,
        text_expr,
        element_expr,
        bool(element_field_path),
        parsed_value,
        where_params,
        element_field_path,  # Pass this so we can rebuild the expression params if needed
    )

    # Combine params: FROM params, WHERE params (which includes type check + text expr + where clause params)
    final_params = sql_params + where_params

    # Add type check to prevent scalar errors
    if type_check:
        where_clause = f"{type_check} AND ({where_clause})"

    # Construct the complete SQL subquery
    from_sql = " CROSS JOIN LATERAL ".join(from_clauses)
    subquery = f"SELECT 1 FROM {from_sql} WHERE {where_clause} LIMIT 1"

    return queryset.annotate(_match=RawSQL(subquery, final_params)).filter(_match__isnull=False)


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
    criteria: ComplexQuery | None = None,
) -> QuerySet:
    """
    Filter a Host queryset by searching values within Host model fields and last_scan_cache JSON fields.

    This function supports searching across three sections:
    - "meta": Direct Host model fields (e.g., "meta.fqdn", "meta.department")
    - "facts": Fields from last_scan_cache facts section
    - "metrics": Fields from last_scan_cache metrics section

    Args:
        queryset: The initial Host QuerySet to filter.
        criteria: The search criteria as a ComplexQuery object, or None for no filtering.
                  Use parse_query() to convert a query string into a ComplexQuery.

    Returns:
        Filtered QuerySet of Host objects matching the criteria.

    Example:
        from hosts.search import parse_query, search_hosts_by_scan_fields
        query = parse_query("facts.generic.HostnameCtl.os contains 'Ubuntu'")
        results = search_hosts_by_scan_fields(Host.objects.all(), query)
    """
    if criteria is None:
        return queryset

    # Build a mapping from field ID to descriptor for efficient lookup
    fields_by_id = {field.id: field for field in get_searchable_fields()}

    return _apply_complex_query_to_queryset(queryset, criteria, fields_by_id)
