"""Constants and enumerations for host search functionality."""

from __future__ import annotations

from enum import StrEnum


class Section(StrEnum):
    FACTS = "facts"
    METRICS = "metrics"
    META = "meta"
    ALERTS = "alerts"


class FieldKind(StrEnum):
    SCALAR = "scalar"
    ARRAY = "array"


class ValueType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"


class Cardinality(StrEnum):
    SINGLE = "single"
    ELEMENTS = "elements"


class LogicalOperator(StrEnum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class TokenType(StrEnum):
    IDENT = "ident"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OPERATOR = "operator"
    LOGICAL = "logical"
    ALIAS = "alias"
    LPAREN = "lparen"
    RPAREN = "rparen"
    LBRACE = "lbrace"
    RBRACE = "rbrace"
    COMMA = "comma"


ALIAS_KEYWORD = "AS"
MATCH_COLUMN_PREFIX = "Matches: "
ARRAY_MARKER = "[]"
SCAN_CACHE_FIELD = "last_scan_cache"
GROUP_OPEN = "{"
GROUP_CLOSE = "}"


class SearchFormParam(StrEnum):
    SEARCH_STRING = "search-string"
    COLUMNS = "columns"
    SHOW_MATCHES = "show-matches"
    INCLUDE_ARCHIVED = "include-archived"
    LOAD = "load"


class ExportType(StrEnum):
    CSV = "csv"
    JSON = "json"
    TXT = "txt"


EXPORT_FILENAME_PREFIX = "humitifier-advanced-export-"
