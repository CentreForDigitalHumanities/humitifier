from __future__ import annotations

from types import UnionType

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, get_args, get_origin

from django.db.models import QuerySet
from django.db.models.expressions import RawSQL

from .models import Host
from humitifier_common.artefacts.registry import registry as artefact_registry
from pydantic import BaseModel


# Where in last_scan_cache the artefact lives
ArtefactSection = Literal["facts", "metrics"]


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


PrimitivePydanticTypes = (str, int, bool)


def _iter_artefacts() -> Iterable[tuple[ArtefactSection, Any, str]]:
    """Yield (section, artefact_cls, artefact_key) for all registered artefacts."""
    # Available facts/metrics return strings like "group.Name"
    for key in artefact_registry.available_facts:
        artefact_cls = artefact_registry.get(key)
        yield "facts", artefact_cls, key
    for key in artefact_registry.available_metrics:
        artefact_cls = artefact_registry.get(key)
        yield "metrics", artefact_cls, key


def _unwrap_optional(ann: Any) -> Any:
    """Return the inner annotation for Optional[X] or Union[X, None]."""
    origin = get_origin(ann)

    if origin is None:
        # PEP604 | style
        if type(ann) is UnionType:
            args = [a for a in getattr(ann, "__args__", ()) if a is not type(None)]  # noqa: E721
            if len(args) == 1:
                return args[0]
        return ann

    if origin is UnionType:
        args = [a for a in get_args(ann) if a is not type(None)]  # noqa: E721
        if len(args) == 1:
            return args[0]

    return ann


def _field_type_to_value_type(ann: Any) -> str | None:
    """Map a pydantic field annotation to a simplified value type string.

    Returns one of: "string", "integer", "boolean" or None if not supported.
    """
    ann = _unwrap_optional(ann)
    origin = get_origin(ann)
    if origin is None:
        if ann in PrimitivePydanticTypes:
            if ann is str:
                return "string"
            if ann is int:
                return "integer"
            if ann is bool:
                return "boolean"
        return None
    return None


def _iter_base_model_fields(model: type[BaseModel]) -> Iterable[tuple[str, str]]:
    """Yield (name, value_type) for primitive fields of a pydantic BaseModel."""
    for name, field in model.model_fields.items():
        value_type = _field_type_to_value_type(field.annotation)
        if value_type:
            yield name, value_type


def _get_list_element_type(list_cls: type) -> Any | None:
    """Return the element type for classes declared as `class X(list[T])`.

    The artefact system injects pydantic schema proxy, but we can still inspect
    __orig_bases__ to find the typing argument.
    """
    bases = getattr(list_cls, "__orig_bases__", None) or getattr(list_cls, "__bases__", ())
    for b in bases:
        # typing like list[T]
        origin = getattr(b, "__origin__", None)
        if origin in (list, list_cls):
            args = getattr(b, "__args__", ())
            if args:
                return args[0]
        # Support plain builtin list as base (unlikely)
        if b is list:
            return Any
    return None


def get_searchable_fields() -> list[SearchableField]:
    """
    Build and return descriptors for fields inside Host.last_scan_cache that are
    reasonably searchable.

    Current implementation includes:
    - Primitive fields (str/int/bool) of BaseModel artefacts
    - Primitive fields of element models for list[...] artefacts
    """
    fields: list[SearchableField] = []

    def render_array_id(section: str, artefact_key: str, array_path: tuple[str, ...], element_field_path: tuple[str, ...]) -> str:
        # Build something like: facts.generic.Hardware.memory[]->size
        # array_path contains keys and "[]" markers; for id, omit keys then append [] at the right spot.
        # We'll render keys joined by '.', placing [] at the end.
        keys_only = [p for p in array_path if p != "[]"]
        head = f"{section}.{artefact_key}"
        if keys_only:
            head += "." + ".".join(keys_only)
        head += "[]"
        if element_field_path:
            head += "->" + ".".join(element_field_path)
        return head

    def add_scalar(section: str, artefact_key: str, path: tuple[str, ...], value_type: str):
        field_id = f"{section}.{artefact_key}." + ".".join(path)
        label = f"{field_id} ({value_type})"
        fields.append(
            SearchableField(
                id=field_id,
                label=label,
                value_type=value_type,  # type: ignore[arg-type]
                section=section,
                kind="scalar",
                artefact_key=artefact_key,
                field_path=path,
            )
        )

    def add_array(section: str, artefact_key: str, array_path: tuple[str, ...], element_field_path: tuple[str, ...], value_type: str):
        field_id = render_array_id(section, artefact_key, array_path, element_field_path)
        label = f"{field_id} ({value_type})"
        fields.append(
            SearchableField(
                id=field_id,
                label=label,
                value_type=value_type,  # type: ignore[arg-type]
                section=section,
                kind="array",
                artefact_key=artefact_key,
                field_path=(),
                array_path=array_path,
                element_field_path=element_field_path,
            )
        )

    def collect_from_model(section: str, artefact_key: str, model: type[BaseModel], base_path: tuple[str, ...] = ()):
        for name, field in model.model_fields.items():
            ann = _unwrap_optional(field.annotation)
            # primitive scalar
            vt = _field_type_to_value_type(ann)
            if vt:
                add_scalar(section, artefact_key, base_path + (name,), vt)
                continue
            origin = get_origin(ann)
            if isinstance(ann, type) and issubclass(ann, BaseModel):
                collect_from_model(section, artefact_key, ann, base_path + (name,))
                continue
            if origin in (list, tuple):
                args = get_args(ann)
                if not args:
                    continue
                elem = _unwrap_optional(args[0])
                # List of BaseModel
                if isinstance(elem, type) and issubclass(elem, BaseModel):
                    # Recurse element fields; each becomes an array field
                    def collect_elem_fields(elem_model: type[BaseModel], elem_base_path: tuple[str, ...] = ()):
                        for ename, ef in elem_model.model_fields.items():
                            eann = _unwrap_optional(ef.annotation)
                            evt = _field_type_to_value_type(eann)
                            if evt:
                                add_array(section, artefact_key, base_path + (name, "[]"), elem_base_path + (ename,), evt)
                                continue
                            eorigin = get_origin(eann)
                            if isinstance(eann, type) and issubclass(eann, BaseModel):
                                collect_elem_fields(eann, elem_base_path + (ename,))
                                continue
                            if eorigin in (list, tuple):
                                eargs = get_args(eann)
                                if not eargs:
                                    continue
                                eelem = _unwrap_optional(eargs[0])
                                # Nested arrays inside element: support by adding another [] in array_path
                                if isinstance(eelem, type) and issubclass(eelem, BaseModel):
                                    # Collect primitive fields inside nested element model
                                    def collect_nested(nmodel: type[BaseModel], nbase: tuple[str, ...] = ()):
                                        for nname, nf in nmodel.model_fields.items():
                                            nann = _unwrap_optional(nf.annotation)
                                            nvt = _field_type_to_value_type(nann)
                                            if nvt:
                                                add_array(section, artefact_key, base_path + (name, "[]", ename, "[]"), nbase + (nname,), nvt)
                                                continue
                                    collect_nested(eelem)
                                else:
                                    # list of primitives inside element
                                    evt2 = _field_type_to_value_type(eelem)
                                    if evt2:
                                        add_array(section, artefact_key, base_path + (name, "[]", ename, "[]"), (), evt2)

                    collect_elem_fields(elem)
                else:
                    # list of primitives directly in model
                    pvt = _field_type_to_value_type(elem)
                    if pvt:
                        add_array(section, artefact_key, base_path + (name, "[]"), (), pvt)

    for section, artefact_cls, artefact_key in _iter_artefacts():
        if isinstance(artefact_cls, type) and issubclass(artefact_cls, BaseModel):
            collect_from_model(section, artefact_key, artefact_cls)
        elif isinstance(artefact_cls, type) and issubclass(artefact_cls, list):
            element_type = _get_list_element_type(artefact_cls)
            if isinstance(element_type, type) and issubclass(element_type, BaseModel):
                # element fields as array path ('[]',)
                def collect_elem_for_top(elem_model: type[BaseModel], elem_base: tuple[str, ...] = ()):
                    for name, value_type in _iter_base_model_fields(elem_model):
                        add_array(section, artefact_key, ("[]",), (name,), value_type)
                    # Also support nested BaseModels and lists in element
                    for ename, ef in elem_model.model_fields.items():
                        eann = _unwrap_optional(ef.annotation)
                        if isinstance(eann, type) and issubclass(eann, BaseModel):
                            # Primitive fields deeper
                            for nname, nvt in _iter_base_model_fields(eann):
                                add_array(section, artefact_key, ("[]", ename, "[]"), (nname,), nvt)
                        elif get_origin(eann) in (list, tuple):
                            eargs = get_args(eann)
                            if eargs:
                                eelem = _unwrap_optional(eargs[0])
                                if isinstance(eelem, type) and issubclass(eelem, BaseModel):
                                    for nname, nvt in _iter_base_model_fields(eelem):
                                        add_array(section, artefact_key, ("[]", ename, "[]"), (nname,), nvt)
                                else:
                                    pvt = _field_type_to_value_type(eelem)
                                    if pvt:
                                        add_array(section, artefact_key, ("[]", ename, "[]"), (), pvt)
                collect_elem_for_top(element_type)
            else:
                # list of primitives directly as artefact
                pvt = _field_type_to_value_type(element_type)
                if pvt:
                    add_array(section, artefact_key, ("[]",), (), pvt)

    return fields


def _parse_value(value: Any, value_type: str) -> Any:
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


def search_hosts_by_scan_fields(
    qs: QuerySet[Host],
    criteria: Mapping[str, Any],
) -> QuerySet:
    """
    Filter a Host queryset by searching values within last_scan_cache JSON fields.

    criteria: mapping from SearchableField.id to the value to search.
    All criteria are combined using AND semantics.
    - string values: case-insensitive substring match (icontains)
    - integer/bool: exact match
    For array artefacts, matches hosts where any element has a field matching the value.
    """
    if not criteria:
        return qs

    # Build a map from id to descriptor for quick lookup
    fields_by_id = {field.id: field for field in get_searchable_fields()}

    for field_id, raw_value in criteria.items():
        descriptor = fields_by_id.get(field_id)
        if descriptor is None:
            # Unknown field id; ignore silently
            continue

        value = _parse_value(raw_value, descriptor.value_type)

        if descriptor.kind == "scalar":
            # Build Django JSON lookup path
            json_lookup = [
                "last_scan_cache",
                descriptor.section,
                descriptor.artefact_key,
                *descriptor.field_path,
            ]
            lookup = "__".join(json_lookup)

            if descriptor.value_type == "string":
                qs = qs.filter(**{f"{lookup}__icontains": value})
            else:
                qs = qs.filter(**{lookup: value})
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
                # Element itself is primitive. For strings, Postgres jsonb scalar::text
                # includes quotes, so we strip them conditionally.
                # We'll build the expression later depending on value type.
                text_expr = f"{expr}::text"

            if descriptor.value_type == "string":
                if not elem_field_path:
                    # primitive element: strip quotes when it's a JSON string
                    text_for_compare = (
                        f"CASE WHEN jsonb_typeof({expr})='string' "
                        f"THEN trim(both '" + '"' + f"' from {expr}::text) "
                        f"ELSE {expr}::text END"
                    )
                    where = f"{text_for_compare} ILIKE %s"
                else:
                    where = f"{text_expr} ILIKE %s"
                params.append(f"%{value}%")
            else:
                where = f"{text_expr} = %s"
                params.append(str(value))

            from_sql = " CROSS JOIN LATERAL ".join(from_clauses)
            query = f"SELECT 1 FROM {from_sql} WHERE {where} LIMIT 1"
            qs = qs.annotate(_match=RawSQL(query, params)).filter(_match__isnull=False)

    return qs


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


__all__ = [
    "SearchableField",
    "get_searchable_fields",
    "search_hosts_by_scan_fields",
    "get_scan_field_value_for_object",
    "get_scan_field_values",
]
