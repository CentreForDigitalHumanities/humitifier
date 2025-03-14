from enum import Enum
from typing import Any, get_args

from pydantic import BaseModel, ConfigDict

from humitifier_common.artefacts.registry.registry import (
    registry as artefact_registry,
)


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


class ScanOutput(BaseModel):
    """
    Represents the output of a scanning operation.

    This class serves as a data model for the results obtained from a scan operation.
    It contains information about the original input used for the scan, details about
    the scanned system, various metrics collected during the scan, any errors encountered,
    and the current version of the output format.

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
    :ivar version: The version of the scan output format. Defaults to 2.
    :type version: int
    """

    original_input: ScanInput
    hostname: str
    facts: dict[str, Any]
    metrics: dict[str, Any]
    errors: list[ScanError]
    version: int = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Make sure any dict-based contents are going to be parsed into their
        # respective artefact models
        for key, val in self.facts.items():
            self.facts[key] = self._parse_artefact(key, val)

        for key, val in self.metrics.items():
            self.metrics[key] = self._parse_artefact(key, val)

    def get_artefact_data(self, artefact):
        if not isinstance(artefact, str):
            if not hasattr(artefact, "__artefact_name__"):
                raise KeyError
            artefact = artefact.__artefact_name__

        if artefact in self.facts:
            data = self.facts[artefact]
            # Should not do anything, but just in case
            return self._parse_artefact(artefact, data)
        if artefact in self.metrics:
            data = self.metrics[artefact]
            # Should not do anything, but just in case
            return self._parse_metrics(artefact, data)

        raise KeyError

    @staticmethod
    def _parse_artefact(artefact_name, data):
        """
        Parses an input data object into a specific artefact instance based on the specified
        artefact name. This method checks the data's type and adapts it to match the expected
        format for the target artefact. If the input data is a dictionary or list, it
        attempts to unpack the contents and initialize the artefact accordingly. If the data
        is `None`, the method returns `None`.

        :param artefact_name: The name of the artefact to be retrieved from the artefact
                              registry.
        :type artefact_name: str
        :param data: The input data object to be parsed. It may be an existing instance of
                     the artefact, a dictionary of initialization parameters, or a list of
                     dictionaries containing initialization parameters.
        :type data: Any
        :return: An instance of the artefact corresponding to the provided name and adapted
                 data. Returns `None` if the input data is `None`.
        :rtype: Any
        """
        artefact = artefact_registry.get(artefact_name)

        if isinstance(data, artefact):
            return data

        if isinstance(data, dict):
            return artefact(**data)

        if isinstance(data, list):
            inner_type = get_args(artefact.__orig_bases__[0])[0]
            if inner_type:
                return artefact([inner_type(**datum) for datum in data])
            return artefact(data)

        return artefact(data) if data else None
