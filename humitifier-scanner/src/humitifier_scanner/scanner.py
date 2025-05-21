import subprocess
from collections import defaultdict, deque
from datetime import datetime

import sys
from typing import Any, Type

from humitifier_common.artefacts.registry.registry import ArtefactType
from humitifier_scanner.collectors.backend import Collector, CollectInfo, registry
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
    if input_data is None:
        raise ValueError("input_data is None")

    today = datetime.now().astimezone()
    try:
        collectors, errors = _get_scan_order(input_data)
    except MissingRequiredFactError as e:
        logger.error(f"Required fact {e.artefact_name} not requested!")
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

            #
            global_errors = [error for error in collector_errors if error.global_error]
            if global_errors:
                break
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

    dependencies = {}

    for collector in collectors:

        for optional_fact in collector.optional_facts:
            if optional_fact.__artefact_name__ in requested_facts:
                if optional_fact not in dependencies:
                    dependencies[optional_fact] = set()
                dependencies[optional_fact].add(collector)

        for required_fact in collector.required_facts:
            if required_fact.__artefact_name__ not in requested_facts:
                raise MissingRequiredFactError(
                    f"Required artefact {required_fact.__artefact_name__ } not requested!",
                    required_fact.__artefact_name__,
                )

            if required_fact not in dependencies:
                dependencies[required_fact] = set()
            dependencies[required_fact].add(collector)

    logger.debug(f"Resolved dependencies: {dependencies}")

    scan_order = resolve_collector_order(collectors, dependencies)
    _debug_scan_order = [collector.artefact_name() for collector in scan_order]
    logger.debug(f"Resolved artefact-scan order: {_debug_scan_order}")

    return scan_order, errors


def resolve_collector_order(collectors, dependencies):
    # Step 1: Build the dependency graph and in-degree count
    dependency_graph = defaultdict(set)
    num_dependencies = {collector: 0 for collector in collectors}

    for required, dependents in dependencies.items():
        required_implementation = registry.get(required.__artefact_name__)
        for dependent in dependents:
            dependency_graph[required_implementation].add(dependent)
            num_dependencies[dependent] += 1

    # Step 2: Initialize a queue with collectors that have no dependencies (num_dependencies 0)
    queue = deque(
        [collector for collector in collectors if num_dependencies[collector] == 0]
    )
    ordered_collectors = []

    # Step 3: Topological Sort (Kahn's Algorithm)
    while queue:
        current = queue.popleft()
        ordered_collectors.append(current)

        for dependent in dependency_graph[current]:
            num_dependencies[dependent] -= 1
            if num_dependencies[dependent] == 0:
                queue.append(dependent)

    # Step 4: Validate for cyclic dependencies
    if len(ordered_collectors) != len(collectors):
        raise ValueError("Cycle detected in dependencies, order cannot be resolved.")

    return ordered_collectors


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
    required_facts, optional_facts, fact_errors = _get_fact_data(
        collector, current_output
    )

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
        optional_facts=optional_facts,
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
            # If we cannot get an executor, something is truly wrong. Hence, we treat it
            # as a global error.
            global_error=True,
        )
        errors.append(error)
    finally:
        return executors, errors


def _release_executors(input_data: ScanInput) -> None:
    for executor in Executors:
        release_executor(executor, input_data.hostname)


def _get_fact_data(
    collector: Type[Collector], current_output: ScanOutput
) -> tuple[dict, dict, list[ScanError]]:
    required_fact_data = {}
    optional_fact_data = {}
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

    for optional_fact in collector.optional_facts:
        try:
            optional_fact_data[optional_fact] = current_output.facts[
                optional_fact.__artefact_name__
            ]
        except KeyError as e:
            optional_fact_data[optional_fact] = None

    return required_fact_data, optional_fact_data, errors
