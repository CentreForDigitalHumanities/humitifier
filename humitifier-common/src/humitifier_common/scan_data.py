import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from humitifier_common.artefacts import registry as artefact_registry
from humitifier_common.utils.pydantic import create_typed_dict


class ArtefactScanOptions(BaseModel):
    """A class representing any config option for an artefact-collect-request.

    :ivar variant: Used to request a specific collector variant for a scan.
    :type variant: str
    """

    model_config = ConfigDict(extra="allow")

    variant: str = "default"


class ScanInput(BaseModel):
    """
    Represents the input model for scanning operations.

    This class holds the hostname and artefacts required for initiating a scan.
    The hostname identifies the target system, and the facts provide
    a list of facts (and metrics) to collect.

    :ivar hostname: The name of the host that will be scanned.
    :type hostname: str
    :ivar artefacts: A dictionary containing requested facts and config options, where
        each key represents the fact type and the value provides corresponding
        scanning options.
    :type artefacts: dict[str, ArtefactScanOptions]
    """

    hostname: str
    artefacts: dict[str, ArtefactScanOptions]


class ScanErrorMetadata(BaseModel):
    """
    Represents additional metadata associated with a scanning error.

    This class is used to encapsulate metadata details when an error occurs during
    a scan operation. It provides attributes to store relevant data such as
    identifier, outputs, exceptions, and exit codes.

    :ivar identifier: An optional identifier associated with the scan operation.
    :type identifier: str | None
    :ivar stdout: The standard output produced during the scan as a string.
    :type stdout: str | None
    :ivar stderr: The standard error output produced during the scan as a string.
    :type stderr: str | None
    :ivar exception: Representation of the exception/error message in string form.
    :type exception: str | None
    :ivar exit_code: Exit code returned from the scan operation.
    :type exit_code: int | None
    :ivar py_exception: The string representation of the Python exception, if
        available.
    :type py_exception: str | None
    """

    identifier: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    exception: str | None = None
    exit_code: int | None = None
    py_exception: str | None = None


class ErrorTypeEnum(Enum):
    """
    Represents various error types that can occur in the system.

    This Enum class is used to define a standard set of error types that can be referenced across
    the application. Each error type corresponds to a specific error condition that can be
    encountered during program execution.

    :ivar COLLECTOR_NOT_FOUND: Represents an error where the specified collector cannot be located.
    :type COLLECTOR_NOT_FOUND: str
    :ivar INVALID_SCAN_CONFIGURATION: Represents an error indicating the provided scan configuration
        is invalid. For example, a requested fact requires another fact to be collected, which is
        not requested.
    :type INVALID_SCAN_CONFIGURATION: str
    :ivar EXECUTION_ERROR: Represents a generic execution error encountered during program runtime.
    :type EXECUTION_ERROR: str
    """

    HOST_OFFLINE = "HOST_OFFLINE"
    COLLECTOR_NOT_FOUND = "COLLECTOR_NOT_FOUND"
    INVALID_SCAN_CONFIGURATION = "INVALID_SCAN_CONFIGURATION"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class ScanError(BaseModel):
    """
    Represents an error encountered during a scanning operation.

    This class is used to model and encapsulate data related to errors that occur
    during the scanning process. It includes detailed information about the error,
    such as the message, associated metadata, the type of collector implementation
    that caused the error, and additional classification of whether the error is global.

    :ivar message: The error message describing the nature of the scan error.
    :type message: str
    :ivar artefact: Optional additional information or context related to the scan
    error, if available.
    :type artefact: str | None
    :ivar collector_implementation: The name of the collector implementation
        where the error occurred, if applicable.
    :type collector_implementation: str | None
    :ivar global_error: Indicates whether the error is global and affects the entire
        scanning process.
    :type global_error: bool
    :ivar metadata: Optional metadata providing further details about the scan error.
    :type metadata: ScanErrorMetadata | None
    :ivar type: The classification of the error based on a predefined set of
        error types.
    :type type: ErrorTypeEnum | None
    """

    message: str
    artefact: str | None = None
    collector_implementation: str | None = None
    global_error: bool = False
    metadata: ScanErrorMetadata | None = None
    type: ErrorTypeEnum | None = None


FactTypedDict = create_typed_dict("FactTypedDict", artefact_registry.all_facts)
MetricTypedDict = create_typed_dict("MetricTypedDict", artefact_registry.all_metrics)

_SCAN_OUTPUT_CLASSES: dict[int, type["ScanOutput"]] = {}


def get_fact_typed_dict(version: int):
    return create_typed_dict(
        f"FactTypedDictV{version}",
        lambda v=version: artefact_registry.all_facts(version=v),
    )


def get_metric_typed_dict(version: int):
    return create_typed_dict(
        f"MetricTypedDictV{version}",
        lambda v=version: artefact_registry.all_metrics(version=v),
    )


def get_scan_output_class(version: int) -> type["ScanOutput"]:
    if version in _SCAN_OUTPUT_CLASSES:
        return _SCAN_OUTPUT_CLASSES[version]

    fact_typed_dict = get_fact_typed_dict(version)
    metric_typed_dict = get_metric_typed_dict(version)
    target_version = version

    class _VersionedScanOutput(ScanOutput):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        original_input: ScanInput
        scan_date: datetime
        hostname: str
        facts: fact_typed_dict = Field(default_factory=dict)
        metrics: metric_typed_dict = Field(default_factory=dict)
        errors: list[ScanError] = Field(default_factory=list)
        version: int = target_version

    _VersionedScanOutput.__name__ = f"ScanOutputV{version}"
    _VersionedScanOutput.__qualname__ = f"ScanOutputV{version}"
    _SCAN_OUTPUT_CLASSES[version] = _VersionedScanOutput
    return _VersionedScanOutput


class ScanOutput(BaseModel):
    """
    Represents the output of a scanning operation.

    This class serves as a data model for the results obtained from a scan operation.
    It contains information about the original input used for the scan, details about
    the scanned system, various metrics collected during the scan, any errors encountered,
    and the format version of the output.

    :ivar original_input: The input data used to initiate the scanning operation.
    :type original_input: ScanInput
    :ivar hostname: The hostname of the scanned system.
    :type hostname: str
    :ivar facts: A dictionary containing facts or metadata about the scanned system.
    :type facts: dict[str, Any]
    :ivar metrics: A dictionary containing performance or health metrics of the
        scanned system collected during the scan process.
    :type metrics: dict[str, Any]
    :ivar errors: A list of errors encountered during the scan operation.
    :type errors: list[ScanError]
    :ivar version: The version of the scan output format.
    :type version: int
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    original_input: ScanInput
    scan_date: datetime
    hostname: str
    facts: FactTypedDict = Field(default_factory=dict)
    metrics: MetricTypedDict = Field(default_factory=dict)
    errors: list[ScanError] = Field(default_factory=list)
    version: int = 2

    def __new__(cls, *args, **kwargs):
        # Dynamic instantiation magic; given the data, we try to find the right
        # sub-class for the scan output based on the version number.

        # Only try to resolve the actual class if it's the base class that's
        # being instantiated
        if cls is ScanOutput:
            version = kwargs.get("version", artefact_registry.latest_version)
            subcls = get_scan_output_class(version)
            # If we found a sub-class, return an instance of that instead
            if subcls is not ScanOutput:
                return subcls(*args, **kwargs)

        # Otherwise, just keep chaining.
        return super().__new__(cls)

    @model_validator(mode="wrap")
    @classmethod
    def _validate_versioned(cls, data: Any, handler):
        # Similar deal; if Pydantic is doing stuff, make sure we use the right
        # sub-class if we can.

        if cls is ScanOutput:
            if isinstance(data, (str, bytes)):
                data = json.loads(data)

            if isinstance(data, dict):
                version = data.get("version", artefact_registry.latest_version)
            elif hasattr(data, "version"):
                version = getattr(data, "version", artefact_registry.latest_version)
            else:
                version = artefact_registry.latest_version

            subcls = get_scan_output_class(version)
            if subcls is not ScanOutput:
                return subcls.model_validate(data)

        return handler(data)

    def get_artefact_data(self, artefact):
        if not isinstance(artefact, str):
            if not hasattr(artefact, "__artefact_name__"):
                raise KeyError
            artefact = artefact.__artefact_name__

        if artefact in self.facts:
            return self.facts[artefact]

        if artefact in self.metrics:
            return self.metrics[artefact]

        raise KeyError
