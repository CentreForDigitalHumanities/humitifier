from typing import Any, Optional, Type, TypedDict, Callable
from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import core_schema


def create_typed_dict(typed_dict_name: str, registry_function, total: bool = False):
    """
    Creates a dynamically typed dictionary with specified attributes and fields.

    Generates a custom TypedDict based on the provided typed dictionary name,
    a function that registers and returns a sequence of artefacts, and a flag
    indicating whether all fields should be total or optional. The fields
    of the TypedDict are determined based on the attributes of the artefacts
    returned by the registry function. Each field will represent a specific
    artefact, either as Optional or required, depending on the total flag.

    :param typed_dict_name: The name to assign to the dynamically created TypedDict.
    :param registry_function: A callable function that returns a sequence of
                              artefacts to be included as fields in the TypedDict.
    :param total: A boolean flag indicating whether all fields in the
                  TypedDict should be mandatory (total=True) or optional (total=False).
    :return: A dynamically constructed TypedDict with the specified name and
             fields derived from the registry function.
    """
    fields = {
        artefact.__artefact_name__: Optional[artefact]
        for artefact in registry_function()
    }
    return TypedDict(typed_dict_name, fields, total=total)


def insert_pydantic_schema_proxy(wrapped_class):
    """
    Inserts a special proxy method '__get_pydantic_core_schema__' into a class that is not
    a subclass of BaseModel. This ensures compatibility with Pydantic's schema generation
    process by injecting a handler function to determine core schema from the appropriate
    base class. If the wrapped class already contains this method, it does not overwrite it,
    and no further action is taken.

    Mainly, this is to solve cases like `class Artefact(list[SubType])`; pydantic
    doesn't understand this is just a fancy list. The inserted method will pass
    `list[SubType]` back as the type, which pydantic can understand.

    :param wrapped_class: The class into which the proxy method is to be injected, if it
        is not already a subclass of BaseModel.
    :type wrapped_class: Type[Any]
    :return: The original wrapped class, potentially with the new proxy method added.
    :rtype: Type[Any]
    :raises ValueError: If the class does not have valid base class(es), or if the class
        has multiple base classes, rendering schema determination ambiguous.
    """
    if not issubclass(wrapped_class, BaseModel):

        # Do nothing if the class already has a method set
        if hasattr(wrapped_class, "__get_pydantic_core_schema__"):
            return

        @classmethod  # noqa; it's _fine_ linter
        def __get_pydantic_core_schema__(
            cls: Type[Any], source: Type[Any], handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            # Dunno why this is needed; everyone seems to want it
            assert source is cls

            # First, get __orig_bases__; this contians the full typing
            bases = getattr(cls, "__orig_bases__", None)
            # If somehow we don't have that, fall back to __bases__
            if not bases:
                bases = cls.__bases__

            # Filter out `object`, as classes without a parent need to be caught.
            bases = [base for base in bases if base is not object]
            # If we don't have any bases (well, `object` is the base then, but okay)
            # we need to stop here and now and tell the dev to implement pydantic
            # compatibility
            if not bases:
                raise ValueError(
                    f"Class {cls.__name__} does not have a valid base class. Please implement __get_pydantic_core_schema__"
                )

            # Assume the last specified base is the correct one
            item_type = bases[-1]

            return handler(item_type)

        # Set our method
        wrapped_class.__get_pydantic_core_schema__ = __get_pydantic_core_schema__
