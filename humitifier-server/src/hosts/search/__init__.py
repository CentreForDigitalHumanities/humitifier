"""Host search functionality for searching within last_scan_cache JSON fields.

This module provides the ability to discover searchable fields from registered
artefacts and build complex queries to filter hosts based on their scan data.
"""

from .field_discovery import get_searchable_fields
from .query_builder import search_hosts_by_scan_fields
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
    "ComparisonOperator",
    "ComplexQuery",
    "SearchCriterion",
    "SearchableField",
    "get_scan_field_value_for_object",
    "get_scan_field_values",
    "get_searchable_fields",
    "search_hosts_by_scan_fields",
]
