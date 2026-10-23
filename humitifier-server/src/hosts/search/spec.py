"""Language specification exposing search grammar, functions, and fields."""

from __future__ import annotations

from typing import Any

from .constants import GROUP_CLOSE, GROUP_OPEN, LogicalOperator
from .field_discovery import get_searchable_fields
from .functions import function_registry
from .operators import operator_registry


def get_language_spec() -> dict[str, Any]:
    """Generate the full language specification for frontend consumption.

    Includes:
    - Comparison operators with symbols and descriptions
    - Logical keywords (AND, OR, NOT)
    - Grouping bracket tokens
    - Registered search functions with parameter specifications and examples
    - Searchable fields with identifiers and value types
    """
    operators = [
        {
            "symbol": op.symbol,
            "keyword": op.keyword,
            "description": op.description,
        }
        for op in operator_registry.all()
    ]

    functions = [
        {
            "name": func.name,
            "description": func.description,
            "examples": list(func.examples),
            "params": [
                {
                    "name": p.name,
                    "accepts": p.accepts.value,
                    "value_types": (
                        sorted(vt.value for vt in p.value_types)
                        if p.value_types
                        else None
                    ),
                    "cardinality": p.cardinality.value if p.cardinality else None,
                }
                for p in func.params
            ],
            "variadic": (
                [
                    {
                        "name": p.name,
                        "accepts": p.accepts.value,
                        "value_types": (
                            sorted(vt.value for vt in p.value_types)
                            if p.value_types
                            else None
                        ),
                        "cardinality": p.cardinality.value if p.cardinality else None,
                    }
                    for p in func.variadic
                ]
                if func.variadic
                else None
            ),
        }
        for func in function_registry.all()
    ]

    fields = [
        {
            "id": f.id,
            "label": f.label,
            "value_type": f.value_type.value,
            "section": f.section.value,
            "kind": f.kind.value,
        }
        for f in get_searchable_fields()
    ]

    return {
        "operators": operators,
        "logical_operators": [op.value for op in LogicalOperator],
        "grouping": {
            "open": GROUP_OPEN,
            "close": GROUP_CLOSE,
        },
        "functions": functions,
        "fields": fields,
    }
