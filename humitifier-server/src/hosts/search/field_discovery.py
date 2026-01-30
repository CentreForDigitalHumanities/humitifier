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


def _build_array_field_id(
    section: str,
    artefact_key: str,
    array_path: tuple[str, ...],
    element_field_path: tuple[str, ...]
) -> str:
    """Construct a field identifier for an array field.

    Args:
        section: The artefact section (e.g., 'facts' or 'metrics')
        artefact_key: The key identifying the artefact type
        array_path: Path components including "[]" markers for arrays
        element_field_path: Path to field within array elements

    Returns:
        A field ID like "facts.generic.Hardware.memory[]->size"

    Example:
        >>> _build_array_field_id("facts", "Hardware", ("memory", "[]"), ("size",))
        "facts.Hardware.memory[]->size"
    """
    # Extract only the field names, excluding "[]" markers
    field_names = [component for component in array_path if component != "[]"]

    # Start with section and artefact key
    identifier = f"{section}.{artefact_key}"

    # Add field path if present
    if field_names:
        identifier += "." + ".".join(field_names)

    # Add array marker
    identifier += "[]"

    # Add element field path if present
    if element_field_path:
        identifier += "->" + ".".join(element_field_path)

    return identifier


def _create_scalar_field(
    section: str,
    artefact_key: str,
    field_path: tuple[str, ...],
    value_type: str
) -> SearchableField:
    """Create a searchable field descriptor for a scalar (non-array) field.

    Args:
        section: The artefact section (e.g., 'facts' or 'metrics')
        artefact_key: The key identifying the artefact type
        field_path: Tuple of field names forming the path to this field
        value_type: The primitive type (e.g., 'string', 'integer', 'boolean')

    Returns:
        A SearchableField descriptor for the scalar field
    """
    field_id = f"{section}.{artefact_key}." + ".".join(field_path)
    label = f"{field_id} ({value_type})"

    return SearchableField(
        id=field_id,
        label=label,
        value_type=value_type,  # type: ignore[arg-type]
        section=section,
        kind="scalar",
        artefact_key=artefact_key,
        field_path=field_path,
    )


def _create_array_field(
    section: str,
    artefact_key: str,
    array_path: tuple[str, ...],
    element_field_path: tuple[str, ...],
    value_type: str
) -> SearchableField:
    """Create a searchable field descriptor for an array field.

    Args:
        section: The artefact section (e.g., 'facts' or 'metrics')
        artefact_key: The key identifying the artefact type
        array_path: Path components including "[]" markers indicating arrays
        element_field_path: Path to the field within array elements
        value_type: The primitive type (e.g., 'string', 'integer', 'boolean')

    Returns:
        A SearchableField descriptor for the array field
    """
    field_id = _build_array_field_id(section, artefact_key, array_path, element_field_path)
    label = f"{field_id} ({value_type})"

    return SearchableField(
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


def _collect_nested_array_fields(
    section: str,
    artefact_key: str,
    nested_model: type[BaseModel],
    parent_array_path: tuple[str, ...],
    nested_base_path: tuple[str, ...] = ()
) -> list[SearchableField]:
    """Collect searchable primitive fields from a nested array element model.

    Args:
        section: The artefact section
        artefact_key: The key identifying the artefact type
        nested_model: The Pydantic model for nested array elements
        parent_array_path: Array path from parent context
        nested_base_path: Base path within nested elements

    Returns:
        List of SearchableField descriptors for primitive fields
    """
    fields: list[SearchableField] = []

    for field_name, field_info in nested_model.model_fields.items():
        annotation = _unwrap_optional(field_info.annotation)
        value_type = _field_type_to_value_type(annotation)

        if value_type:
            field = _create_array_field(
                section,
                artefact_key,
                parent_array_path,
                nested_base_path + (field_name,),
                value_type
            )
            fields.append(field)

    return fields


def _collect_list_element_fields(
    section: str,
    artefact_key: str,
    element_model: type[BaseModel],
    base_path: tuple[str, ...],
    field_name: str,
    element_base_path: tuple[str, ...] = ()
) -> list[SearchableField]:
    """Collect searchable fields from list element models recursively.

    Handles list[BaseModel] fields within a parent BaseModel, extracting
    primitive fields and nested structures.

    Args:
        section: The artefact section
        artefact_key: The key identifying the artefact type
        element_model: The Pydantic model for list elements
        base_path: Path to the parent field containing the list
        field_name: Name of the list field
        element_base_path: Base path within element models for nested fields

    Returns:
        List of SearchableField descriptors
    """
    fields: list[SearchableField] = []

    for element_field_name, element_field_info in element_model.model_fields.items():
        annotation = _unwrap_optional(element_field_info.annotation)
        value_type = _field_type_to_value_type(annotation)

        # Handle primitive fields in the element
        if value_type:
            field = _create_array_field(
                section,
                artefact_key,
                base_path + (field_name, "[]"),
                element_base_path + (element_field_name,),
                value_type
            )
            fields.append(field)
            continue

        origin = get_origin(annotation)

        # Handle nested BaseModel within element
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            nested_fields = _collect_list_element_fields(
                section,
                artefact_key,
                annotation,
                base_path + (field_name, "[]"),
                element_field_name,
                element_base_path
            )
            fields.extend(nested_fields)
            continue

        # Handle nested lists within element (e.g., list[list[T]])
        if origin in (list, tuple):
            nested_list_args = get_args(annotation)
            if not nested_list_args:
                continue

            nested_element_type = _unwrap_optional(nested_list_args[0])

            # Nested list of BaseModel
            if isinstance(nested_element_type, type) and issubclass(nested_element_type, BaseModel):
                nested_array_path = base_path + (field_name, "[]", element_field_name, "[]")
                nested_fields = _collect_nested_array_fields(
                    section,
                    artefact_key,
                    nested_element_type,
                    nested_array_path
                )
                fields.extend(nested_fields)
            else:
                # Nested list of primitives
                primitive_value_type = _field_type_to_value_type(nested_element_type)
                if primitive_value_type:
                    field = _create_array_field(
                        section,
                        artefact_key,
                        base_path + (field_name, "[]", element_field_name, "[]"),
                        (),
                        primitive_value_type
                    )
                    fields.append(field)

    return fields


def _collect_model_fields(
    section: str,
    artefact_key: str,
    model: type[BaseModel],
    base_path: tuple[str, ...] = ()
) -> list[SearchableField]:
    """Recursively collect all searchable fields from a Pydantic BaseModel.

    Traverses the model structure to find:
    - Primitive scalar fields (str, int, bool)
    - Nested BaseModel fields
    - Lists of primitives or BaseModels
    - Deeply nested list structures

    Args:
        section: The artefact section (e.g., 'facts' or 'metrics')
        artefact_key: The key identifying the artefact type
        model: The Pydantic BaseModel class to introspect
        base_path: Current path context for nested fields

    Returns:
        List of SearchableField descriptors for all discoverable fields
    """
    fields: list[SearchableField] = []

    for field_name, field_info in model.model_fields.items():
        annotation = _unwrap_optional(field_info.annotation)

        # Check for primitive scalar fields
        value_type = _field_type_to_value_type(annotation)
        if value_type:
            field = _create_scalar_field(
                section,
                artefact_key,
                base_path + (field_name,),
                value_type
            )
            fields.append(field)
            continue

        origin = get_origin(annotation)

        # Handle nested BaseModel fields
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            nested_fields = _collect_model_fields(
                section,
                artefact_key,
                annotation,
                base_path + (field_name,)
            )
            fields.extend(nested_fields)
            continue

        # Handle list or tuple fields
        if origin in (list, tuple):
            type_args = get_args(annotation)
            if not type_args:
                continue

            element_type = _unwrap_optional(type_args[0])

            # List of BaseModel elements
            if isinstance(element_type, type) and issubclass(element_type, BaseModel):
                element_fields = _collect_list_element_fields(
                    section,
                    artefact_key,
                    element_type,
                    base_path,
                    field_name
                )
                fields.extend(element_fields)
            else:
                # List of primitives
                primitive_value_type = _field_type_to_value_type(element_type)
                if primitive_value_type:
                    field = _create_array_field(
                        section,
                        artefact_key,
                        base_path + (field_name, "[]"),
                        (),
                        primitive_value_type
                    )
                    fields.append(field)

    return fields


def _collect_top_level_list_fields(
    section: str,
    artefact_key: str,
    element_model: type[BaseModel]
) -> list[SearchableField]:
    """Collect searchable fields from a top-level list artefact.

    Handles artefacts that are defined as list[BaseModel] at the top level,
    where the artefact itself is a list type.

    Args:
        section: The artefact section
        artefact_key: The key identifying the artefact type
        element_model: The Pydantic model for list elements

    Returns:
        List of SearchableField descriptors
    """
    fields: list[SearchableField] = []

    # Collect primitive fields directly from element model
    for field_name, value_type in _iter_base_model_fields(element_model):
        field = _create_array_field(
            section,
            artefact_key,
            ("[]",),
            (field_name,),
            value_type
        )
        fields.append(field)

    # Also handle nested structures and lists within elements
    for element_field_name, element_field_info in element_model.model_fields.items():
        annotation = _unwrap_optional(element_field_info.annotation)

        # Handle nested BaseModel within element
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            for nested_field_name, nested_value_type in _iter_base_model_fields(annotation):
                field = _create_array_field(
                    section,
                    artefact_key,
                    ("[]", element_field_name, "[]"),
                    (nested_field_name,),
                    nested_value_type
                )
                fields.append(field)

        # Handle nested lists within element
        elif get_origin(annotation) in (list, tuple):
            type_args = get_args(annotation)
            if type_args:
                nested_element_type = _unwrap_optional(type_args[0])

                if isinstance(nested_element_type, type) and issubclass(nested_element_type, BaseModel):
                    # Nested list of BaseModel
                    for nested_field_name, nested_value_type in _iter_base_model_fields(nested_element_type):
                        field = _create_array_field(
                            section,
                            artefact_key,
                            ("[]", element_field_name, "[]"),
                            (nested_field_name,),
                            nested_value_type
                        )
                        fields.append(field)
                else:
                    # Nested list of primitives
                    primitive_value_type = _field_type_to_value_type(nested_element_type)
                    if primitive_value_type:
                        field = _create_array_field(
                            section,
                            artefact_key,
                            ("[]", element_field_name, "[]"),
                            (),
                            primitive_value_type
                        )
                        fields.append(field)

    return fields


def get_searchable_fields() -> list[SearchableField]:
    """Build and return descriptors for searchable fields in Host.last_scan_cache.

    This function introspects all registered artefacts (facts and metrics) to discover
    fields that can be used for searching hosts. It handles various structures:

    - Primitive scalar fields (str, int, bool) in BaseModel artefacts
    - Nested BaseModel fields with dot-notation paths
    - Lists of primitives and BaseModels with array notation
    - Deeply nested list structures with multiple array levels

    Returns:
        A list of SearchableField descriptors, each containing:
        - id: Unique identifier for the field (e.g., "facts.Hardware.memory[]->size")
        - label: Human-readable label with type information
        - value_type: The primitive type (string, integer, or boolean)
        - section: The artefact section (facts or metrics)
        - kind: Either "scalar" or "array"
        - Relevant path information for field access

    Example field IDs:
        - "facts.generic.Hardware.hostname" (scalar)
        - "facts.generic.Hardware.memory[]->size" (array)
        - "metrics.DiskUsage.partitions[]->mountpoint" (array)
    """
    fields: list[SearchableField] = []

    for section, artefact_class, artefact_key in _iter_artefacts():
        # Handle BaseModel artefacts
        if isinstance(artefact_class, type) and issubclass(artefact_class, BaseModel):
            model_fields = _collect_model_fields(section, artefact_key, artefact_class)
            fields.extend(model_fields)

        # Handle list-type artefacts (e.g., class MyArtefact(list[SomeModel]))
        elif isinstance(artefact_class, type) and issubclass(artefact_class, list):
            element_type = _get_list_element_type(artefact_class)

            if isinstance(element_type, type) and issubclass(element_type, BaseModel):
                # List of BaseModel elements
                list_fields = _collect_top_level_list_fields(section, artefact_key, element_type)
                fields.extend(list_fields)
            else:
                # List of primitives
                primitive_value_type = _field_type_to_value_type(element_type)
                if primitive_value_type:
                    field = _create_array_field(
                        section,
                        artefact_key,
                        ("[]",),
                        (),
                        primitive_value_type
                    )
                    fields.append(field)

    return fields
