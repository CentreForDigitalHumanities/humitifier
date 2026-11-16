"""Base classes for search functions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar

from ..constants import Cardinality, ValueType

if TYPE_CHECKING:
    from ..nodes import Expr, ExprType
    from ..sql import CompiledExpr, CompileContext


class ParamKind(StrEnum):
    FIELD = "field"
    LITERAL = "literal"
    EXPR = "expr"


@dataclass(frozen=True)
class Param:
    """Specification of a search function parameter."""

    name: str
    accepts: ParamKind
    value_types: frozenset[ValueType] | None = None
    cardinality: Cardinality | None = None


class SearchFunction:
    """Base class for self-registering search functions."""

    abstract: ClassVar[bool] = True
    name: ClassVar[str]
    description: ClassVar[str]
    examples: ClassVar[tuple[str, ...]] = ()
    params: ClassVar[tuple[Param, ...]] = ()
    variadic: ClassVar[tuple[Param, ...] | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.__dict__.get("abstract", False):
            from .registry import function_registry

            function_registry.register(cls)

    @classmethod
    def validate(cls, args: tuple[Expr, ...]) -> None:
        from ..nodes import FieldRef, Literal

        fixed_count = len(cls.params)
        variadic_group = cls.variadic

        if variadic_group is None:
            if len(args) != fixed_count:
                raise ValueError(
                    f"Function '{cls.name}' expects {fixed_count} argument(s), got {len(args)}"
                )
        else:
            var_len = len(variadic_group)
            if len(args) < fixed_count or (len(args) - fixed_count) % var_len != 0:
                raise ValueError(
                    f"Function '{cls.name}' expects {fixed_count} arguments plus repeated groups of {var_len}, got {len(args)}"
                )

        for i, arg in enumerate(args):
            if i < fixed_count:
                param = cls.params[i]
            else:
                var_idx = (i - fixed_count) % len(variadic_group)  # type: ignore[arg-type]
                param = variadic_group[var_idx]  # type: ignore[index]

            pos = getattr(arg, "position", 0)

            # Check parameter kind
            if param.accepts == ParamKind.FIELD and not isinstance(arg, FieldRef):
                raise ValueError(
                    f"'{cls.name}' argument '{param.name}' must be a field at position {pos}"
                )
            elif param.accepts == ParamKind.LITERAL and not isinstance(arg, Literal):
                raise ValueError(
                    f"'{cls.name}' argument '{param.name}' must be a literal at position {pos}"
                )

            # Check cardinality
            if param.cardinality is not None:
                if arg.expr_type.cardinality != param.cardinality:
                    if param.cardinality == Cardinality.ELEMENTS:
                        raise ValueError(
                            f"'{cls.name}' requires an array field at position {pos}"
                        )
                    else:
                        raise ValueError(
                            f"'{cls.name}' requires a scalar field at position {pos}"
                        )

            # Check value type
            if param.value_types is not None:
                if arg.expr_type.value_type not in param.value_types:
                    expected = "/".join(sorted(vt.value for vt in param.value_types))
                    array_str = " array" if param.cardinality == Cardinality.ELEMENTS else ""
                    raise ValueError(
                        f"'{cls.name}' requires an {expected}{array_str} field, got {arg.expr_type.value_type.value} at position {pos}"
                    )

    @classmethod
    def return_type_spec(cls) -> dict[str, Any]:
        """Return return type specification for frontend language spec."""
        try:
            expr_type = cls.return_type(())
            vt = getattr(expr_type.value_type, "value", expr_type.value_type)
            card = getattr(expr_type.cardinality, "value", expr_type.cardinality)
            return {
                "value_type": vt,
                "cardinality": card,
            }
        except Exception:
            return {
                "value_type": "dynamic",
                "cardinality": Cardinality.SINGLE.value,
            }

    @classmethod
    def return_type(cls, args: tuple[Expr, ...]) -> ExprType:
        """Return the expression type produced by calling this function with `args`."""
        raise NotImplementedError

    @classmethod
    def compile(cls, args: tuple[Expr, ...], ctx: CompileContext) -> CompiledExpr:
        """Compile this function call to a CompiledExpr."""
        raise NotImplementedError

    @classmethod
    def compile_matches(
        cls, args: tuple[Expr, ...], ctx: CompileContext
    ) -> SqlFragment | None:
        """Compile this function call to a SqlFragment producing matching elements, or None."""
        return None
