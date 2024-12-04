from dataclasses import dataclass
from typing import Any, Type, TypeVar

from humitifier_scanner.exceptions import FatalCollectorError
from humitifier_scanner.executor import Executors
from humitifier_scanner.executor.linux_shell import LinuxShellExecutor
from humitifier_scanner.logger import logger
from humitifier_common.facts import registry as facts_registry
from humitifier_common.scan_data import ErrorTypeEnum, ScanError, ScanErrorMetadata

_BASE_FACT_COLLECTORS = [
    "FactCollector",
    "ShellFactCollector",
]
T = TypeVar("T")


class CollectorMetaclass(type):

    def __new__(cls, name, bases, dct):
        new_cls = super().__new__(cls, name, bases, dct)

        # Skip the check if the class is a base FactCollector class
        if name in _BASE_FACT_COLLECTORS:
            return new_cls

        if new_cls.fact is None:
            raise ValueError("FactCollector must define a 'fact' attribute")

        cls._check_if_fact_exists(new_cls, new_cls.fact, "fact")

        for required_fact in new_cls.required_facts:
            cls._check_if_fact_exists(new_cls, required_fact, "required_facts")

        from .registry import registry

        registry.register(new_cls)

        return new_cls

    def _check_if_fact_exists(cls, fact, attribute: str):
        if not hasattr(fact, "__fact_name__"):
            raise ValueError(
                f"Fact {fact} does not have a __fact_name__ attribute for "
                f"{cls.__name__}.{attribute}"
            )

        if not facts_registry.get(fact.__fact_name__):
            raise ValueError(
                f"Fact {fact.__fact_name__} is not registered in the facts "
                f"registry for {cls.__name__}.{attribute}"
            )


@dataclass
class CollectInfo:
    executors: dict[Executors, Any]
    required_facts: dict


class FactCollector(metaclass=CollectorMetaclass):
    fact = Type[T]
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
                    fact=self.fact.__fact_name__,
                    collector_implementation=f"{self.fact.__fact_name__}:{self.variant}",
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

        If `fatal` is True, execution will be halted and the fact will return
        'None' as the output. (And the error will be reported in the scan output)

        This can be used to report 'soft' errors that don't necessarily need to
        stop the collector from running, but should still be reported.
        """
        self.errors.append(
            ScanError(
                message=message,
                fact=self.fact.__fact_name__,
                collector_implementation=f"{self.fact.__fact_name__}:{self.variant}",
                metadata=metadata,
                type=error_type,
            )
        )
        logger.debug(f"Error occurred in {self.__class__.__name__}: {message}")
        if fatal:
            raise FatalCollectorError

    def collect(self, info: CollectInfo) -> T:
        """Implement your collector logic here."""
        raise NotImplementedError("FactCollector must implement a collect method")


class ShellFactCollector(FactCollector):
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
            "FactCollector must implement a collect_from_shell method"
        )
