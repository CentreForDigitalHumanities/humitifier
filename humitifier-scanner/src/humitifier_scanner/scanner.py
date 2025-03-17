import subprocess
from datetime import datetime

import sys
from typing import Any, Type

from humitifier_common.artefacts.registry.registry import ArtefactType
from humitifier_scanner.collectors import CollectInfo, registry
from humitifier_scanner.collectors.backend import Collector
from humitifier_scanner.exceptions import (
    MissingRequiredFactError,
)
from humitifier_scanner.executor import Executors, get_executor, release_executor
from humitifier_scanner.logger import logger
from humitifier_common.scan_data import (
    ErrorTypeEnum,
    ScanError,
    ScanErrorMetadata,
    ScanInput,
    ScanOutput,
)


def scan(input_data: ScanInput) -> ScanOutput:
    today = datetime.now().astimezone()
    try:
        collectors, errors = _get_scan_order(input_data)
    except MissingRequiredFactError as e:
        error = ScanError(
            global_error=True,
            message=f"Required fact {e.artefact_name} not requested!",
            type=ErrorTypeEnum.INVALID_SCAN_CONFIGURATION,
            metadata=ScanErrorMetadata(
                py_exception=e.name(),
            ),
        )
        return ScanOutput(
            facts={},
            errors=[error],
            metrics={},
            original_input=input_data,
            hostname=input_data.hostname,
            scan_date=today,
        )

    output = ScanOutput(
        hostname=input_data.hostname,
        facts={},
        metrics={},
        errors=errors,
        original_input=input_data,
        scan_date=today,
    )

    if _check_host_online(input_data.hostname):
        for collector in collectors:
            collector_output, collector_errors = _run_collector(
                collector, input_data, output
            )

            if collector.fact:
                output.facts[collector.artefact_name()] = collector_output
            elif collector.metric:
                output.metrics[collector.artefact_name()] = collector_output

            output.errors.extend(collector_errors)
    else:
        output.errors.append(
            ScanError(
                message="The intended host seems to be offline",
                type=ErrorTypeEnum.HOST_OFFLINE,
            )
        )

    _release_executors(input_data)

    return output


def _get_scan_order(
    input_data: ScanInput,
) -> tuple[list[Type[Collector]], list[ScanError]]:
    collectors = []
    errors = []

    for artefact, options in input_data.artefacts.items():
        variant = options.variant

        collector = registry.get(artefact, variant)
        if not collector:
            errors.append(
                ScanError(
                    artefact=artefact,
                    collector_implementation=f"{artefact}:{variant}",
                    message=f"Could not find collector for {artefact} with variant {variant}",
                    type=ErrorTypeEnum.COLLECTOR_NOT_FOUND,
                )
            )
            continue

        collectors.append(collector)

    requested_facts = [
        collector.artefact_name()
        for collector in collectors
        if collector.artefact_type() == ArtefactType.FACT
    ]

    for collector in collectors:
        for required_fact in collector.required_facts:
            if required_fact.__artefact_name__ not in requested_facts:
                raise MissingRequiredFactError(
                    f"Required artefact {required_fact.__artefact_name__ } not requested!",
                    required_fact.__artefact_name__,
                )

    # make sure that any collector that requires another collector is
    # scanned after the required collector
    for collector in collectors.copy():
        for required_fact in collector.required_facts:
            required_implementation = registry.get(required_fact.__artefact_name__)
            required_index = collectors.index(required_implementation)
            implementation_index = collectors.index(collector)

            if required_index > implementation_index:
                collectors.remove(collector)
                collectors.insert(required_index, collector)

    scan_order = [collector.artefact_name() for collector in collectors]
    logger.debug(f"Resolved artefact-scan order: {scan_order}")

    return collectors, errors


def _check_host_online(hostname):
    # Why are we building in support for Windows? Reasons!
    ping_count_arg = "-n" if sys.platform.lower() == "win32" else "-c"

    try:
        result = subprocess.run(
            ["ping", ping_count_arg, "1", hostname],
            capture_output=True,
            text=True,
        )
        is_online = result.returncode == 0

        if is_online:
            logger.debug("Host is online")
        else:
            logger.debug("Host is offline :(")

        return is_online

    except Exception as e:
        logger.error(f"An error occurred while trying to contact host {hostname}: {e}")
        return False


def _run_collector(
    collector: Type[Collector], input_data: ScanInput, current_output: ScanOutput
) -> tuple[Any, list[ScanError]]:
    output = None
    errors = []

    logger.debug(f"Starting collector {collector.artefact_name()}:{collector.variant}")

    required_executors, exc_errors = _get_executors(collector, input_data)
    required_facts, fact_errors = _get_required_fact_data(collector, current_output)

    if exc_errors:
        errors.extend(exc_errors)
    if fact_errors:
        errors.extend(fact_errors)

    # If either of the above functions returned errors, we cannot proceed
    if errors:
        logger.debug(f"Collector startup errors: {errors}")
        return output, errors

    collect_info = CollectInfo(
        executors=required_executors,
        required_facts=required_facts,
    )
    try:
        output, errors = collector().run(collect_info)
    except Exception as e:
        logger.debug(
            "An error occurred while collecting fact",
            exc_info=True,
        )
        error = ScanError(
            artefact=collector.artefact_name(),
            collector_implementation=collector.__class__.__name__,
            message="An error occurred while collecting artefact",
            metadata=ScanErrorMetadata(
                py_exception=e.__class__.__name__,
            ),
        )
        errors.append(error)
    finally:
        return output, errors


def _get_executors(
    collector: Type[Collector], input_data: ScanInput
) -> tuple[dict[Executors, Any], list[ScanError]]:
    executors = {}
    errors = []

    try:
        for executor in collector.required_executors:
            executors[executor] = get_executor(executor, input_data.hostname)
    except Exception as e:
        logger.debug(
            "An error occurred while getting executors",
            exc_info=True,
        )
        error = ScanError(
            artefact=collector.artefact_name(),
            collector_implementation=collector.__class__.__name__,
            message="An error occurred while getting executors: " + str(e),
            type=ErrorTypeEnum.EXECUTION_ERROR,
            metadata=ScanErrorMetadata(
                py_exception=e.__class__.__name__,
            ),
        )
        errors.append(error)
    finally:
        return executors, errors


def _release_executors(input_data: ScanInput) -> None:
    for executor in Executors:
        release_executor(executor, input_data.hostname)


def _get_required_fact_data(
    collector: Type[Collector], current_output: ScanOutput
) -> tuple[dict, list[ScanError]]:
    required_fact_data = {}
    errors = []

    for required_fact in collector.required_facts:
        try:
            required_fact_data[required_fact] = current_output.facts[
                required_fact.__artefact_name__
            ]
        except KeyError as e:
            collected_facts = ", ".join(current_output.facts.keys())
            logger.debug(
                f"Required fact '{required_fact.__artefact_name__}' not found in already collected facts: {collected_facts}",
                exc_info=True,
            )
            error = ScanError(
                fact=collector.artefact_name(),
                collector_implementation=collector.__class__.__name__,
                message="Required fact not found in already collected facts",
                metadata=ScanErrorMetadata(
                    py_exception=e.__class__.__name__,
                ),
            )
            errors.append(error)

    return required_fact_data, errors
