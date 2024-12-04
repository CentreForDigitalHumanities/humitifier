from enum import Enum
from typing import Any

from pydantic import BaseModel


class FactScanOptions(BaseModel):
    variant: str = "default"


class ScanInput(BaseModel):
    hostname: str
    facts: dict[str, FactScanOptions]


class ScanErrorMetadata(BaseModel):
    identifier: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    exception: str | None = None
    exit_code: int | None = None
    py_exception: str | None = None


class ErrorTypeEnum(Enum):
    COLLECTOR_NOT_FOUND = "COLLECTOR_NOT_FOUND"
    INVALID_SCAN_CONFIGURATION = "INVALID_SCAN_CONFIGURATION"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class ScanError(BaseModel):
    message: str
    fact: str | None = None
    collector_implementation: str | None = None
    global_error: bool = False
    metadata: ScanErrorMetadata | None = None
    type: ErrorTypeEnum | None = None


class ScanOutput(BaseModel):
    hostname: str
    facts: dict[str, Any]
    errors: list[ScanError]
    version: int = 2
