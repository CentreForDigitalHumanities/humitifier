"""Array element filtering search function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..constants import Cardinality, ValueType
from ..sql import ElementSet, SqlFragment
from .base import Param, ParamKind, SearchFunction

if TYPE_CHECKING:
    from ..nodes import Expr, ExprType
    from ..sql import CompileContext


class Filter(SearchFunction):
    """Filter array elements by a regex pattern."""

    name = "filter"
    description = "filter array elements by regex pattern"
    examples = (
        'filter(facts.generic.PackageManagerInfo.installed_packages[].name, "apache") contains "apache2"',
        'count(filter(facts.generic.PackageManagerInfo.installed_packages[].name, "ssh")) > 0',
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
            frozenset({ValueType.STRING}),
            Cardinality.SINGLE,
        ),
    )

    @classmethod
    def return_type(cls, args: tuple[Expr, ...]) -> ExprType:
        from ..nodes import ExprType

        return ExprType(args[0].expr_type.value_type, Cardinality.ELEMENTS)

    @classmethod
    def compile(cls, args: tuple[Expr, ...], ctx: CompileContext) -> ElementSet:
        from ..nodes import Literal

        elem_set = ctx.to_element_set(args[0])
        pattern = args[1].value if isinstance(args[1], Literal) else str(args[1])
        condition = SqlFragment(
            f"{elem_set.value.sql} ~ %s", elem_set.value.params + (str(pattern),)
        )
        return elem_set.with_condition(condition)
