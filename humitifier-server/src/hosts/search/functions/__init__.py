"""Search functions package with auto-discovery."""

from __future__ import annotations

import importlib
import pkgutil

from .base import Param, ParamKind, SearchFunction
from .registry import function_registry


def _autodiscover() -> None:
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name not in ("base", "registry"):
            importlib.import_module(f"{__name__}.{module_info.name}")


_autodiscover()

__all__ = [
    "Param",
    "ParamKind",
    "SearchFunction",
    "function_registry",
]
