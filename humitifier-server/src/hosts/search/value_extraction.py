"""Value extraction from host scan cache data."""

from __future__ import annotations

from typing import Any, Iterable

from django.db.models import QuerySet

from ..models import Host
from .field_discovery import get_searchable_fields
from .types import SearchableField


def _get_cache_from_obj(obj: Any) -> dict | None:
    """Best-effort to get a last_scan_cache-like dict from an input object.

    Accepts either a Django model instance with attribute `last_scan_cache` or a raw
    dict that already represents the cache. Returns None when unavailable.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        # Heuristic: treat as cache dict directly
        return obj
    # Django model instance (or any object) with attribute
    return getattr(obj, "last_scan_cache", None)


def _extract_from_cache(cache: dict, descriptor: SearchableField) -> Any:
    """Extract a field value from a last_scan_cache dict using a SearchableField.

    - For scalar artefacts, returns a single value (or None if not present).
    - For array artefacts, returns a list of values (possibly empty). None values
      are filtered out from the resulting list.
    """
    if not isinstance(cache, dict):
        return None

    section_data = cache.get(descriptor.section)
    if not isinstance(section_data, dict):
        return None if descriptor.kind == "scalar" else []

    artefact_data = section_data.get(descriptor.artefact_key)

    if descriptor.kind == "scalar":
        cur = artefact_data
        for key in descriptor.field_path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(key)
        return cur

    # Array kind: artefact_data contains nested structures; walk array_path
    def expand(current_nodes: list[Any], token: str) -> list[Any]:
        out: list[Any] = []
        if token == "[]":
            for node in current_nodes:
                if isinstance(node, list):
                    out.extend(node)
        else:
            for node in current_nodes:
                if isinstance(node, dict):
                    out.append(node.get(token))
        return out

    nodes: list[Any] = [artefact_data]
    for token in (descriptor.array_path or ("[]",)):
        nodes = expand(nodes, token)
        # flatten one level if nested containers like dict returned
        nodes = [n for n in nodes if n is not None]

    # Now nodes are the array elements
    results: list[Any] = []
    if descriptor.element_field_path:
        for elem in nodes:
            cur = elem
            ok = True
            for key in descriptor.element_field_path:
                if not isinstance(cur, dict):
                    ok = False
                    break
                cur = cur.get(key)
            if ok and cur is not None:
                results.append(cur)
    else:
        for elem in nodes:
            if elem is not None:
                results.append(elem)
    return results


def get_scan_field_values(
    objs: Iterable[Host] | QuerySet[Host],
    field_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Collect field values for multiple objects.

    Returns a list with one dict per object. Each dict contains:
      - "object": the original object reference
      - one key per requested field id with its corresponding value(s)

    Example element:
      {"object": host, "facts.generic.HostnameCtl.os": "Linux", "facts.generic.PackageList[]->name": ["openssl", ...]}
    """
    # Prepare field descriptors once
    all_fields = {f.id: f for f in get_searchable_fields()}
    requested_ids = list(field_ids)
    descriptors: dict[str, SearchableField] = {
        fid: all_fields[fid] for fid in requested_ids if fid in all_fields
    }

    results: list[dict[str, Any]] = []
    for obj in objs:
        row: dict[str, Any] = {"object": obj, "fields": {}}
        cache = _get_cache_from_obj(obj)
        for fid, desc in descriptors.items():
            if cache is None:
                row["fields"][fid] = None if desc.kind == "scalar" else []
            else:
                row["fields"][fid] = _extract_from_cache(cache, desc)
        results.append(row)
    return results


def get_scan_field_value_for_object(obj: Any, field_id: str) -> Any:
    """Get the value(s) for a single field id from a given object or cache dict.

    - For scalar fields: returns the value or None
    - For array fields: returns a list of values (possibly empty)
    Unknown field ids return None.
    """
    field_map = {f.id: f for f in get_searchable_fields()}
    desc = field_map.get(field_id)
    if desc is None:
        return None
    cache = _get_cache_from_obj(obj)
    if cache is None:
        return None if desc.kind == "scalar" else []
    return _extract_from_cache(cache, desc)
