from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping

from django.db.models import QuerySet
from django.db.models.expressions import RawSQL

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
    kind: "scalar" for plain objects; "array" when the artefact is list[...] and
          the search targets an element's field.
    artefact_key: the key inside last_scan_cache[section] (e.g. "generic.HostnameCtl").
    field_path: the JSON path within the artefact object (for arrays, inside the element).
    """

    id: str
    label: str
    value_type: Literal["string", "integer", "boolean"]
    section: ArtefactSection
    kind: Literal["scalar", "array"]
    artefact_key: str
    field_path: tuple[str, ...]


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


def _field_type_to_value_type(ann: Any) -> str | None:
    """Map a pydantic field annotation to a simplified value type string.

    Returns one of: "string", "integer", "boolean" or None if not supported.
    """
    origin = getattr(ann, "__origin__", None)
    if origin is None:
        if ann in PrimitivePydanticTypes:
            if ann is str:
                return "string"
            if ann is int:
                return "integer"
            if ann is bool:
                return "boolean"
        return None
    # Optional[X] appears as Union[X, NoneType]; keep primitive X
    if origin is getattr(__import__("typing"), "Union"):
        args = [a for a in getattr(ann, "__args__", ()) if a is not type(None)]  # noqa: E721
        if len(args) == 1:
            return _field_type_to_value_type(args[0])
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

    for section, artefact_cls, artefact_key in _iter_artefacts():
        if isinstance(artefact_cls, type) and issubclass(artefact_cls, BaseModel):
            for name, value_type in _iter_base_model_fields(artefact_cls):
                field_id = f"{section}.{artefact_key}.{name}"
                fields.append(
                    SearchableField(
                        id=field_id,
                        label=field_id,
                        value_type=value_type,  # type: ignore[arg-type]
                        section=section,
                        kind="scalar",
                        artefact_key=artefact_key,
                        field_path=(name,),
                    )
                )
        elif isinstance(artefact_cls, type) and issubclass(artefact_cls, list):
            element_type = _get_list_element_type(artefact_cls)
            if isinstance(element_type, type) and issubclass(element_type, BaseModel):
                for name, value_type in _iter_base_model_fields(element_type):
                    field_id = f"{section}.{artefact_key}[]->{name}"
                    fields.append(
                        SearchableField(
                            id=field_id,
                            label=field_id,
                            value_type=value_type,  # type: ignore[arg-type]
                            section=section,
                            kind="array",
                            artefact_key=artefact_key,
                            field_path=(name,),
                        )
                    )

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
    qs: QuerySet,
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
            # Array artefact: use jsonb_array_elements with RawSQL
            # Build SQL path like: last_scan_cache->'facts'->'generic.PackageList'
            section = descriptor.section
            artefact = descriptor.artefact_key
            field = descriptor.field_path[0]

            base = (
                "jsonb_array_elements(\"hosts_host\".\"last_scan_cache\"->%s->%s)"
            )

            # value expression for element field as text
            # elem->>'field'
            if descriptor.value_type == "string":
                where = "elem->>%s ILIKE %s"
                params = [section, artefact, field, f"%{value}%"]
            else:
                # Compare as text equality; sufficient for int/bool exact matching
                where = "elem->>%s = %s"
                params = [section, artefact, field, str(value)]

            query = f"SELECT 1 FROM {base} AS elem WHERE {where} LIMIT 1"
            qs = qs.annotate(_match=RawSQL(query, params)).filter(_match__isnull=False)

    return qs


__all__ = ["SearchableField", "get_searchable_fields", "search_hosts_by_scan_fields"]
