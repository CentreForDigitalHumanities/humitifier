"""Array element filtering search function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..constants import Cardinality, ValueType
from ..sql import ElementSet, SqlFragment
from .base import Param, ParamKind, SearchFunction

if TYPE_CHECKING:
    from ..nodes import Expr, ExprType
    from ..sql import CompileContext


class Filter(SearchFunction):
    """Filter array elements by a regex pattern (strings) or exact value (integers/booleans)."""

    name = "filter"
    description = "filter array elements by regex pattern or exact value"
    examples = (
        'filter(facts.generic.PackageManagerInfo.installed_packages[].name, "apache") contains "apache2"',
        'count(filter(facts.generic.PackageManagerInfo.installed_packages[].name, "ssh")) > 0',
        'count(filter(facts.generic.Hardware.memory[].size, 2147483648)) > 0',
        'count(filter(facts.generic.PackageManagerInfo.installed_packages[].upgrade_available, true)) > 0',
    )
    params = (
        Param(
            "field",
            ParamKind.FIELD,
            None,
            Cardinality.ELEMENTS,
        ),
        Param(
            "pattern",
            ParamKind.LITERAL,
            frozenset({ValueType.STRING, ValueType.INTEGER, ValueType.BOOLEAN}),
            Cardinality.SINGLE,
        ),
    )

    @classmethod
    def validate(cls, args: tuple[Expr, ...]) -> None:
        super().validate(args)
        if len(args) == 2:
            field_type = args[0].expr_type.value_type
            literal_type = args[1].expr_type.value_type
            if field_type != literal_type:
                pos = getattr(args[1], "position", 0)
                raise ValueError(
                    f"Type mismatch: cannot filter {field_type.value} array with {literal_type.value} literal at position {pos}"
                )

    @classmethod
    def return_type_spec(cls) -> dict[str, Any]:
        return {
            "value_type": "dynamic",
            "cardinality": Cardinality.ELEMENTS.value,
            "dynamic_from_arg": 0,
        }

    @classmethod
    def return_type(cls, args: tuple[Expr, ...]) -> ExprType:
        from ..nodes import ExprType

        return ExprType(args[0].expr_type.value_type, Cardinality.ELEMENTS)

    @classmethod
    def compile(cls, args: tuple[Expr, ...], ctx: CompileContext) -> ElementSet:
        from ..nodes import Literal

        elem_set = ctx.to_element_set(args[0])
        val = args[1].value if isinstance(args[1], Literal) else args[1]

        if elem_set.value_type == ValueType.STRING:
            condition = SqlFragment(
                f"{elem_set.value.sql} ~* %s", elem_set.value.params + (str(val),)
            )
        elif elem_set.value_type == ValueType.BOOLEAN:
            bool_val = str(val).lower() if isinstance(val, bool) else str(val).lower()
            condition = SqlFragment(
                f"{elem_set.value.sql} = %s", elem_set.value.params + (bool_val,)
            )
        else:
            condition = SqlFragment(
                f"{elem_set.value.sql} = %s", elem_set.value.params + (str(val),)
            )
        return elem_set.with_condition(condition)
