from dataclasses import dataclass
from typing import Any, Type, TypeVar

from humitifier_common.artefacts.registry.registry import ArtefactType
from humitifier_scanner.exceptions import FatalCollectorError
from humitifier_scanner.executor import Executors
from humitifier_scanner.executor.linux_shell import LinuxShellExecutor
from humitifier_scanner.logger import logger
from humitifier_common.artefacts import registry as artefacts_registry
from humitifier_common.scan_data import ErrorTypeEnum, ScanError, ScanErrorMetadata

_BASE_COLLECTORS = [
    "Collector",
    "ShellCollector",
]
T = TypeVar("T")


class CollectorMetaclass(type):
    """
    Metaclass for fact and metric collectors.

    This metaclass is responsible for validating and registering fact and metric
    collectors. It enforces constraints on the attributes `fact` and `metric`,
    ensuring they are correctly set and do not conflict. Furthermore, it ensures
    that all required facts are registered and available in the facts registry.

    :ivar _artefact: Internal attribute representing the validated `fact` or `metric` assigned
        to the collector class.
    :type _artefact: Optional[Artefact]
    """

    def __new__(cls, name, bases, dct):
        """
        :param cls: The metaclass being executed, typically 'CollectorMetaclass'.
        :param name: The name of the newly created class.
        :param bases: A tuple containing the base classes for the new class.
        :param dct: A dictionary containing all attributes, methods, and properties for
            the new class.
        :raises ValueError: Raised if an invalid configuration is detected, such as defining
            both 'fact' and 'metric', using a metric as a fact, or failing to define a valid
            'fact' or 'metric' attribute.
        :returns: The newly created class after applying all validations and registrations.
        :rtype: Type
        """
        new_cls = super().__new__(cls, name, bases, dct)

        # Skip the check if the class is a base FactCollector class
        if name in _BASE_COLLECTORS:
            return new_cls

        new_cls._artefact = None

        # Validate and set the 'fact' attribute for the Collector class.
        # Ensure that it is neither a metric nor incorrectly defined.
        if new_cls.fact and cls._is_fact_or_metric(new_cls.fact):
            new_cls._artefact = new_cls.fact
            new_cls.metric = None

            if new_cls.fact.__artefact_type__ != ArtefactType.FACT:
                raise ValueError(
                    "Collector was given a metric as a fact. Please use the 'metric' attribute instead"
                )

        # Validate and set the 'metric' attribute for the Collector class.
        # Ensure that it is correctly defined, is not set as a fact, and
        # does not include required facts (as metrics may not have dependencies).
        if new_cls.metric and cls._is_fact_or_metric(new_cls.metric):
            new_cls._artefact = new_cls.metric
            # Set it to none, as it will be a weird Type[T] otherwise
            new_cls.fact = None

            if new_cls.metric.__artefact_type__ != ArtefactType.METRIC:
                raise ValueError(
                    "Collector was given a fact as a metric. Please use "
                    "the 'fact' attribute instead"
                )

            if new_cls.required_facts:
                raise ValueError("Metrics are not allowed to have required facts!")

        # Final check, see if we managed to resolve the facts
        if new_cls._artefact is None:
            raise ValueError(
                "FactCollector must define a 'fact' or a 'metric' attribute"
            )
        cls._check_if_artefact_exists(new_cls, new_cls._artefact, "fact")

        # Check if all the required facts resolve
        for required_fact in new_cls.required_facts:
            cls._check_if_artefact_exists(new_cls, required_fact, "required_facts")

        from .registry import registry

        # We're done, lets add ourselves to the collector registry
        registry.register(new_cls)

        return new_cls

    @staticmethod
    def _is_fact_or_metric(obj):
        """
        Determines if the given object is either a fact or a metric by checking the
        presence of specific attributes.

        These attributes should be added by the fact registry;

        :param obj: The object to check for fact or metric attributes.
        :type obj: Any
        :return: Returns `True` if the object has both `__fact_name__` and
            `__fact_type__` attributes, otherwise `False`.
        :rtype: bool
        """
        return hasattr(obj, "__artefact_name__") and hasattr(obj, "__artefact_type__")

    def _check_if_artefact_exists(cls, artefact, attribute: str):
        """
        Check if a given artefact exists in the registry for a specific class attribute.

        This method verifies whether the provided artefact has a `__artefact_name__`
        attribute and ensures it is registered within the `registry`.
        If the artefact is missing the `__artefact_type__` attribute or is not registered,
        a `ValueError` is raised.

        :param artefact: The object representing the artefact to verify.
        :param attribute: The name of the attribute for which the artefact is being
            checked.
        :type attribute: str
        :raises ValueError: If the artefact lacks the `__artefact_name__` attribute or if
            the artefact is not registered in the `registry`.
        """
        if not cls._is_fact_or_metric(artefact):
            raise ValueError(
                f"Artefact {artefact} does not appear to be a valid fact or metric"
            )

        if not artefacts_registry.get(artefact.__artefact_name__):
            raise ValueError(
                f"Artefact {artefact.__artefact_name__} is not registered in the facts "
                f"registry for {cls.__name__}.{attribute}"
            )


@dataclass
class CollectInfo:
    executors: dict[Executors, Any]
    required_facts: dict


class Collector(metaclass=CollectorMetaclass):
    """
    Collector class

    The Collector class serves as a fundamental unit for implementing specific logic
    to gather information or metrics. This class is designed to handle artefacts and
    their respective collectors. The core functionality involves executing the logic
    defined in the `collect` method while providing mechanisms for safe error
    handling, logging, and error reporting.

    Each derived class must implement the `collect` method to define how its logic is
    executed. Directly overriding the `run` method is discouraged unless required with
    significant understanding of its internal workings. Additionally, utility methods
    like `add_error` assist in robust error handling.

    :ivar fact: The type of fact the collector processes.
    :type fact: Type[T]
    :ivar metric: The type of metric the collector processes.
    :type metric: Type[T]
    :ivar variant: A string indicating the collector's variant or implementation type.
    :type variant: str
    :ivar required_facts: A list of facts that must be provided for the collector to function.
    :type required_facts: list
    :ivar required_executors: A list of executors required for running the collector.
    :type required_executors: list[Executors]
    :ivar errors: A list of errors encountered during the collector's execution.
    :type errors: list[ScanError]
    """

    fact = Type[T]
    metric = Type[T]
    variant: str = "default"

    required_facts = []
    required_executors: list[Executors] = []

    def __init__(self):
        self.errors: list[ScanError] = []

    def run(self, info: CollectInfo) -> tuple[T | None, list[ScanError]]:
        """Run the collector and return the output and any errors

        DO NOT OVERRIDE THIS METHOD! Instead, override the `collect` method
        to implement the collector logic.

        This is an internal method the scanner calls and provides some
        fail-safes for handling errors and exceptions.

        (Okay, you _may_ override this method if you know what you're doing)
        """
        output = None
        try:
            output = self.collect(info)
        # We don't log the error if it's a FatalCollectorError, as it's expected
        # that the collector has added a more detailed error message
        except FatalCollectorError:
            pass
        # Any other exceptions we create a ScanError for; while the collector
        # should be handling any errors itself, we want to make sure that we
        # log any unhandled exceptions
        except Exception as e:
            self.errors.append(
                ScanError(
                    message=str(e),
                    artefact=self.artefact_name(),
                    collector_implementation=f"{self.artefact_name()}:{self.variant}",
                    metadata=ScanErrorMetadata(py_exception=e.__class__.__name__),
                )
            )
        finally:
            return output, self.errors

    def add_error(
        self,
        message,
        metadata: ScanErrorMetadata | None = None,
        error_type: ErrorTypeEnum | None = None,
        *,
        fatal: bool = False,
    ):
        """Log an error to the collector.

        If `fatal` is True, execution will be halted and the artefact will return
        'None' as the output. (And the error will be reported in the scan output)

        This can be used to report 'soft' errors that don't necessarily need to
        stop the collector from running, but should still be reported.
        """
        self.errors.append(
            ScanError(
                message=message,
                artefact=self.artefact_name(),
                collector_implementation=f"{self.artefact_name()}:{self.variant}",
                metadata=metadata,
                type=error_type,
            )
        )
        logger.debug(f"Error occurred in {self.__class__.__name__}: {message}")
        if fatal:
            raise FatalCollectorError

    def collect(self, info: CollectInfo) -> T:
        """Implement your collector logic here."""
        raise NotImplementedError("Collector must implement a collect method")

    @classmethod
    def artefact_name(cls) -> str:
        """
        Retrieves the name of the artefact associated with the class.

        :return: The artefact name as a string.
        :rtype: str
        """
        return cls._artefact.__artefact_name__

    @classmethod
    def artefact_type(cls) -> ArtefactType:
        """
        Retrieves the type of the artefact associated with the class.
        :return:
        """
        return cls._artefact.__artefact_type__


class ShellCollector(Collector):
    """
    Provides a base class for shell-based collectors, as a shorthand class
    for collectors using shell-executors only.

    The purpose of this class is to facilitate creating collectors that
    rely on shell executors for their functionality. It provides a premade
    `collect` method that automatically retrieves the shell executor
    from the `info` argument and invokes the `collect_from_shell` method,
    which must be implemented by subclasses to define the specific logic
    for collecting data using shell commands.

    :ivar required_executors: A list of executors required by this collector.
    :type required_executors: list
    """

    required_executors = [Executors.SHELL]

    def collect(self, info: CollectInfo) -> T:
        """Premade collect method for shell-based collectors.
        Will call `collect_from_shell` with the shell executor provided in the
        `info` argument.
        """
        executor: LinuxShellExecutor = info.executors.get(Executors.SHELL)
        if not executor:
            raise ValueError("Shell executor is required for this collector")

        return self.collect_from_shell(executor, info)

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> T:
        """Implement your shell-based collector logic here."""
        raise NotImplementedError(
            "Collector must implement a collect_from_shell method"
        )
