"""Registry for search functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import SearchFunction


class _FunctionRegistry:
    """Registry maintaining all available search function classes."""

    def __init__(self) -> None:
        self._functions: dict[str, type[SearchFunction]] = {}

    def register(self, func_cls: type[SearchFunction]) -> None:
        self._functions[func_cls.name.lower()] = func_cls

    def unregister(self, func_cls: type[SearchFunction]) -> None:
        self._functions.pop(func_cls.name.lower(), None)

    def get(self, name: str) -> type[SearchFunction] | None:
        return self._functions.get(name.lower())

    def all(self) -> list[type[SearchFunction]]:
        return sorted(self._functions.values(), key=lambda f: f.name.lower())


function_registry = _FunctionRegistry()
