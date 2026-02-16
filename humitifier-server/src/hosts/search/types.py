"""Type definitions for host search functionality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


# Where the field lives: "facts" and "metrics" are in last_scan_cache, "meta" is on the Host model itself
ArtefactSection = Literal["facts", "metrics", "meta"]

# Comparison operators for search criteria
ComparisonOperator = Literal["eq", "gt", "gte", "lt", "lte", "contains"]

# Aggregation functions for array fields
AggregationFunction = Literal["min", "max", "sum", "concat", "count"]


@dataclass(frozen=True)
class SearchableField:
    """
    A single searchable field descriptor.

    id: stable identifier to be used in search criteria.
        Example: "facts.generic.HostnameCtl.os"
    label: human readable label.
    value_type: one of "string", "integer", "boolean"; used to choose operators.
    section: whether this field is in facts or metrics.
    kind: "scalar" for plain objects; "array" when the target lives inside a list
          at any nesting depth.
    artefact_key: the key inside last_scan_cache[section] (e.g. "generic.HostnameCtl").
    field_path: for kind="scalar": the JSON path within the artefact object to the value.
               for kind="array": this is not used (kept for backward-compat only).
    array_path: for kind="array": path tokens from the artefact root to the array.
                Tokens are field names and the marker "[]" where an array must be expanded.
                Example: ("hardware", "memory", "[]")
                Top-level list artefacts use ("[]",)
    element_field_path: for kind="array": path inside each element to a primitive value.
                        Empty tuple means the element itself is primitive (e.g., list[str]).
    """

    id: str
    label: str
    value_type: Literal["string", "integer", "boolean"]
    section: ArtefactSection
    kind: Literal["scalar", "array"]
    artefact_key: str
    field_path: tuple[str, ...]
    array_path: tuple[str, ...] | None = None
    element_field_path: tuple[str, ...] | None = None


@dataclass(frozen=True)
class SearchCriterion:
    """
    A single search criterion with an operator.

    field_id: the SearchableField.id to search
    operator: comparison operator (eq, gt, gte, lt, lte, contains)
    value: the value to compare against
    aggregation: optional aggregation function for array fields (min, max, sum, concat, count)
    filter_pattern: optional regex pattern to filter array elements before comparison/aggregation
    """
    field_id: str
    operator: ComparisonOperator
    value: Any
    aggregation: AggregationFunction | None = None
    filter_pattern: str | None = None


@dataclass(frozen=True)
class ComplexQuery:
    """
    Represents a complex query with AND/OR combinations.

    Can be either:
    - A single criterion
    - A conjunction (AND) of sub-queries
    - A disjunction (OR) of sub-queries
    """
    type: Literal["criterion", "and", "or"]
    criterion: SearchCriterion | None = None
    children: list[ComplexQuery] | None = None
