"""Value extraction from host scan cache data.

This module provides utilities for extracting field values from Host objects'
last_scan_cache data. It supports both scalar fields (single values) and array
fields (lists of values), with flexible path navigation through nested data structures.

Main public functions:
    - get_scan_field_values: Extract multiple fields from multiple hosts (batch operation)
    - get_scan_field_value_for_object: Extract a single field from one host (convenience)

The extraction process uses SearchableField descriptors that define:
    - section: Top-level cache section (e.g., "facts", "vulnerabilities")
    - artefact_key: Key within the section (e.g., "generic", "packages")
    - field_path: For scalar fields, path through nested dictionaries
    - array_path: For array fields, path to navigate to array elements
    - element_field_path: For array fields, path to extract from each element

Example cache structure:
    {
        "facts": {
            "generic": {
                "HostnameCtl": {"os": "Linux", "kernel": "5.15"},
                "PackageList": [
                    {"name": "gcc", "version": "11.0"},
                    {"name": "python", "version": "3.9"}
                ]
            }
        }
    }
"""

from __future__ import annotations

from typing import Any, Iterable

from django.db.models import QuerySet

from ..models import Host
from .field_discovery import get_searchable_fields
from .types import SearchableField


def _get_scan_data(host: Host) -> dict | None:
    """Extract scan data dictionary from a Host object.

    Args:
        host: A Host model instance.

    Returns:
        The cache dictionary if available, otherwise None.

    Example:
        >>> host = Host(last_scan_cache={"facts": {}})
        >>> _get_scan_data(host)
        {"facts": {}}

        >>> host_without_cache = Host(last_scan_cache=None)
        >>> _get_scan_data(host_without_cache)
        None
    """
    return host.last_scan_cache


def _get_artefact_data(
    data: dict, descriptor: SearchableField
) -> Any | None:
    """Navigate cache structure to retrieve artefact data.

    Args:
        data: The scan data dictionary containing nested section data.
        descriptor: Field descriptor with section and artefact_key information.

    Returns:
        The artefact data if found, or None if the cache structure is invalid.
    """
    if not isinstance(data, dict):
        return None

    section_data = data.get(descriptor.section)
    if not isinstance(section_data, dict):
        return None

    return section_data.get(descriptor.artefact_key)


def _extract_scalar_value(
    artefact_data: Any, field_path: tuple[str, ...]
) -> Any:
    """Extract a scalar value by walking a field path through nested dictionaries.

    Args:
        artefact_data: The starting data to navigate from.
        field_path: Sequence of dictionary keys to traverse.

    Returns:
        The value at the end of the field path, or None if path is invalid.

    Example:
        _extract_scalar_value({"foo": {"bar": 42}}, ("foo", "bar")) -> 42
    """
    current_value = artefact_data
    for key in field_path:
        if not isinstance(current_value, dict):
            return None
        current_value = current_value.get(key)
    return current_value


def _expand_array_nodes(current_nodes: list[Any], path_token: str) -> list[Any]:
    """Expand a list of nodes by applying a single array path token.

    Args:
        current_nodes: List of data nodes to expand.
        path_token: Either "[]" to flatten arrays, or a dictionary key to navigate.

    Returns:
        Expanded list of nodes after applying the token operation.

    Example:
        _expand_array_nodes([{"items": [1, 2]}], "items") -> [1, 2]
        _expand_array_nodes([[1, 2], [3, 4]], "[]") -> [1, 2, 3, 4]
    """
    expanded_nodes: list[Any] = []

    if path_token == "[]":
        # Flatten arrays: extend with array contents
        for node in current_nodes:
            if isinstance(node, list):
                expanded_nodes.extend(node)
    else:
        # Dictionary navigation: extract values by key
        for node in current_nodes:
            if isinstance(node, dict):
                expanded_nodes.append(node.get(path_token))

    return expanded_nodes


def _extract_array_elements(
    artefact_data: Any, array_path: tuple[str, ...] | None
) -> list[Any]:
    """Navigate through artefact data using array path to extract array elements.

    Args:
        artefact_data: The starting data structure.
        array_path: Sequence of tokens describing how to traverse arrays/dicts.
                   None defaults to ("[]",) for top-level array expansion.

    Returns:
        List of extracted elements (non-None values only).

    Example:
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        _extract_array_elements(data, ("users", "[]")) -> [{"name": "Alice"}, {"name": "Bob"}]
    """
    nodes: list[Any] = [artefact_data]

    path_tokens = array_path or ("[]",)
    for token in path_tokens:
        nodes = _expand_array_nodes(nodes, token)
        # Filter out None values after each expansion
        nodes = [node for node in nodes if node is not None]

    return nodes


def _extract_field_from_element(
    element: Any, element_field_path: tuple[str, ...] | None
) -> Any | None:
    """Extract a field value from an array element using field path.

    Args:
        element: The array element to extract from.
        element_field_path: Path of keys to navigate within the element.
                           None means use the element itself.

    Returns:
        The extracted value, or None if path is invalid or value doesn't exist.

    Example:
        _extract_field_from_element({"id": 1, "data": {"value": 42}}, ("data", "value")) -> 42
    """
    if element_field_path is None:
        return element

    current_value = element
    for key in element_field_path:
        if not isinstance(current_value, dict):
            return None
        current_value = current_value.get(key)

    return current_value


def _extract_array_field_values(
    artefact_data: Any,
    array_path: tuple[str, ...] | None,
    element_field_path: tuple[str, ...] | None,
) -> list[Any]:
    """Extract values from array-type fields within artefact data.

    Args:
        artefact_data: The artefact data containing arrays to process.
        array_path: Path describing how to navigate to array elements.
        element_field_path: Path to extract specific fields from each element.

    Returns:
        List of extracted values (non-None only).

    Example:
        data = {"packages": [{"name": "gcc", "version": "11"}, {"name": "python"}]}
        _extract_array_field_values(data, ("packages", "[]"), ("name",))
            -> ["gcc", "python"]
    """
    array_elements = _extract_array_elements(artefact_data, array_path)

    extracted_values: list[Any] = []
    for element in array_elements:
        field_value = _extract_field_from_element(element, element_field_path)
        if field_value is not None:
            extracted_values.append(field_value)

    return extracted_values


def _extract_from_scan_data(data: dict, descriptor: SearchableField) -> Any:
    """Extract a field value from a last_scan_cache dict using a SearchableField.

    This is the main entry point for extracting values from cached scan data.
    Handles both scalar fields (single values) and array fields (lists of values).
    Note: This should only be called for facts/metrics sections, not meta.

    Args:
        data: The scan cache dictionary with nested structure.
        descriptor: Metadata describing the field to extract, including:
                   - kind: "scalar" or "array"
                   - section: Top-level cache section (facts or metrics)
                   - artefact_key: Key within the section
                   - field_path: For scalars, path through nested dicts
                   - array_path: For arrays, path to navigate to array elements
                   - element_field_path: For arrays, path to extract from each element

    Returns:
        - For scalar fields: single value or None if not found
        - For array fields: list of values (possibly empty, never None)

    Example:
        Scalar: cache = {"facts": {"generic": {"HostnameCtl": {"os": "Linux"}}}}
                descriptor with field_path=("os",) -> "Linux"

        Array: cache = {"facts": {"generic": {"PackageList": [{"name": "gcc"}, {"name": "vim"}]}}}
               descriptor with array_path=("[]",), element_field_path=("name",) -> ["gcc", "vim"]
    """
    artefact_data = _get_artefact_data(data, descriptor)

    # Handle invalid cache structure
    if artefact_data is None:
        return None if descriptor.kind == "scalar" else []

    # Extract based on field kind
    if descriptor.kind == "scalar":
        return _extract_scalar_value(artefact_data, descriptor.field_path)
    else:
        return _extract_array_field_values(
            artefact_data, descriptor.array_path, descriptor.element_field_path
        )


def _build_field_descriptor_map(
    field_ids: Iterable[str],
) -> dict[str, SearchableField]:
    """Build a mapping of field IDs to their SearchableField descriptors.

    Args:
        field_ids: Collection of field identifiers to look up.

    Returns:
        Dictionary mapping each valid field ID to its descriptor.
        Invalid field IDs are silently omitted.
    """
    all_searchable_fields = {field.id: field for field in get_searchable_fields()}
    return {
        field_id: all_searchable_fields[field_id]
        for field_id in field_ids
        if field_id in all_searchable_fields
    }


def _extract_field_values_for_host(
    host: Host,
    field_descriptors: dict[str, SearchableField],
) -> dict[str, Any]:
    """Extract all requested field values from a single host's scan cache and meta fields.

    Args:
        host: The host object to extract field values from.
        field_descriptors: Mapping of field IDs to their descriptors.

    Returns:
        Dictionary containing the host object and extracted field values.
        Structure: {"object": host, "fields": {field_id: value, ...}}
    """
    host_data: dict[str, Any] = {"object": host, "fields": {}}
    scan_cache = _get_scan_data(host)

    for field_id, field_descriptor in field_descriptors.items():
        # Handle meta fields directly from Host model
        if field_descriptor.section == "meta":
            # Meta fields are directly on the Host model
            field_name = field_descriptor.field_path[0] if field_descriptor.field_path else None
            if field_name:
                host_data["fields"][field_id] = getattr(host, field_name, None)
            else:
                host_data["fields"][field_id] = None
        elif scan_cache is None:
            # No cache available: return appropriate empty value
            default_value = None if field_descriptor.kind == "scalar" else []
            host_data["fields"][field_id] = default_value
        else:
            # Extract value from cache
            host_data["fields"][field_id] = _extract_from_scan_data(
                scan_cache, field_descriptor
            )

    return host_data


def get_scan_field_values(
    hosts: Iterable[Host] | QuerySet[Host],
    field_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Collect field values for multiple host objects from their scan caches.

    This function efficiently extracts multiple field values from each host's
    last_scan_cache data. Field descriptors are looked up once and reused for
    all hosts.

    Args:
        hosts: Collection of Host objects to extract field values from.
        field_ids: Collection of field identifiers to extract (e.g.,
                  "facts.generic.HostnameCtl.os" or "facts.generic.PackageList[]->name").

    Returns:
        List of dictionaries, one per host. Each dictionary contains:
        - "object": The original Host object reference
        - "fields": Dictionary mapping field IDs to their extracted values
          - Scalar fields: single value or None if not found
          - Array fields: list of values (possibly empty)

    Example:
        >>> hosts = [host1, host2]
        >>> field_ids = ["facts.generic.HostnameCtl.os", "facts.generic.PackageList[]->name"]
        >>> result = get_scan_field_values(hosts, field_ids)
        >>> result[0]
        {
            "object": <Host: host1>,
            "fields": {
                "facts.generic.HostnameCtl.os": "Linux",
                "facts.generic.PackageList[]->name": ["openssl", "vim", "gcc"]
            }
        }
    """
    field_descriptors = _build_field_descriptor_map(field_ids)

    results: list[dict[str, Any]] = []
    for host in hosts:
        host_field_data = _extract_field_values_for_host(host, field_descriptors)
        results.append(host_field_data)

    return results


def get_scan_field_value_for_object(
    host: Host, field_id: str
) -> Any:
    """Get the value for a single field from a host object.

    This convenience function extracts a single field value from a Host
    model instance. Useful for one-off field lookups.

    Args:
        host: A Host model instance to extract the field from.
        field_id: The field identifier to extract (e.g., "facts.generic.HostnameCtl.os" or "meta.fqdn").

    Returns:
        - For scalar fields: the extracted value or None if not found
        - For array fields: list of extracted values (possibly empty, never None)
        - For unknown field IDs: None

    Example:
        >>> host = Host.objects.get(pk=1)
        >>> get_scan_field_value_for_object(host, "facts.generic.HostnameCtl.os")
        "Linux"

        >>> get_scan_field_value_for_object(host, "meta.fqdn")
        "server01.example.com"
    """
    # Look up field descriptor
    field_map = {field.id: field for field in get_searchable_fields()}
    field_descriptor = field_map.get(field_id)

    if field_descriptor is None:
        # Unknown field ID
        return None

    # Handle meta fields
    if field_descriptor.section == "meta":
        field_name = field_descriptor.field_path[0] if field_descriptor.field_path else None
        if field_name:
            return getattr(host, field_name, None)
        return None

    # Get data from object
    scan_data = _get_scan_data(host)
    if scan_data is None:
        # No data available: return appropriate empty value
        return None if field_descriptor.kind == "scalar" else []

    # Extract and return value
    return _extract_from_scan_data(scan_data, field_descriptor)
