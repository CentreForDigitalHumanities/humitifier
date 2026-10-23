"""Host search functionality for searching within last_scan_cache JSON fields.

This module provides the ability to discover searchable fields from registered
artefacts and build complex queries to filter hosts based on their scan data.
"""

from .columns import (
    ColumnSpec,
    compile_column_expr,
    derive_match_columns,
    evaluate_columns,
    format_expr,
    format_value,
)
from .compiler import search_hosts_by_scan_fields
from .field_discovery import get_searchable_fields
from .parser import parse_column, parse_query
from .spec import get_language_spec
from .types import (
    ComparisonOperator,
    ComplexQuery,
    SearchCriterion,
    SearchableField,
)
from .value_extraction import (
    get_scan_field_value_for_object,
    get_scan_field_values,
)

__all__ = [
    "ColumnSpec",
    "ComparisonOperator",
    "ComplexQuery",
    "SearchCriterion",
    "SearchableField",
    "compile_column_expr",
    "derive_match_columns",
    "evaluate_columns",
    "format_expr",
    "format_value",
    "get_language_spec",
    "get_scan_field_value_for_object",
    "get_scan_field_values",
    "get_searchable_fields",
    "parse_column",
    "parse_query",
    "search_hosts_by_scan_fields",
]
