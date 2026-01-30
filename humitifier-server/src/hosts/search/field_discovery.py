"""Discovery and introspection of searchable fields from artefacts."""

from __future__ import annotations

from types import UnionType
from typing import Any, Iterable, get_args, get_origin

from humitifier_common.artefacts.registry import registry as artefact_registry
from pydantic import BaseModel

from .types import ArtefactSection, SearchableField


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
