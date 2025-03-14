from datetime import UTC, datetime, timedelta

from celery import signature
from django.utils import timezone

from hosts.models import Host
from humitifier_common.celery.task_names import SCANNER_RUN_SCAN
from humitifier_server.celery.task_names import *


def start_full_scan(
    host: Host, *, force: bool = False, delay_seconds: int | None = None
):
    """
    Schedules and initiates a full scan on the given host. The scan can optionally be
    forced, and it is possible to configure a delay before the scan begins.

    :param host: The target host object on which the scan will be performed.
    :type host: Host
    :param force: Determines whether the scan should be forced. If set to True, the
        scan will proceed regardless of other conditions.
    :type force: bool
    :param delay_seconds: An optional delay, in seconds, before the scan begins.
        If None, the scan starts immediately.
    :type delay_seconds: int | None
    :return: None
    """
    host.last_scan_scheduled = timezone.now()
    host.save()

    _start_scan(host, force=force, delay_seconds=delay_seconds)


def _start_scan(
    host: Host,
    *,
    force: bool = False,
    delay_seconds: int | None = None,
):
    """
    Starts a scanning process for a given host by creating a task chain with error
    handling, and optionally scheduling the process with a delay.

    The function orchestrates the following steps:
    1. Generates the scan input based on the provided host and force configuration.
    2. Configures error handling for the scan input generation process.
    3. Sets up and executes the scanning operation, along with error handling for
       the scanning process itself.
    4. Combines the scan input generation and scanning processes into a task
       chain, applying additional processing if necessary.
    5. Optionally schedules the execution of the chain based on the provided delay.

    :param host: The host object containing all necessary information for scanning.
    :param force: Whether to force the scanning process regardless of existing configurations.
    :param delay_seconds: Optional delay in seconds to schedule the scan. If None, the task is
        executed immediately.
    :return: None
    """
    # Get our generic log-error handler-task
    log_error_task = signature(MAIN_LOG_ERROR)

    # Setup scan input creation
    get_scan_input_task = signature(SCANNING_GET_SCAN_INPUT, args=(host.fqdn, force))
    get_scan_input_task.on_error(log_error_task)

    # Setup scan running
    run_scan_task = signature(SCANNER_RUN_SCAN)

    on_scan_error = signature(SCANNING_SCAN_HANDLE_ERROR)
    run_scan_task.on_error(on_scan_error)

    # Setup the task-chain
    chain = get_scan_input_task | run_scan_task | _get_processing_chain()

    # Schedule our tasks
    eta = None
    if delay_seconds:
        eta = datetime.now(UTC) + timedelta(seconds=delay_seconds)

    chain.apply_async(eta=eta)


def _get_processing_chain(initial_args: tuple | None = None):
    """
    Generates the processing part of the chain; mainly intended for a future
    where we want to process scans uploaded through the API
    """
    # Get our generic log-error handler-task
    log_error_task = signature(MAIN_LOG_ERROR)

    # Setup scan processing
    generate_alerts_task = signature(ALERTING_GENERATE_ALERTS, args=initial_args)
    generate_alerts_task.on_error(log_error_task)

    save_scan_task = signature(SCANNING_SAVE_SCAN)
    save_scan_task.on_error(log_error_task)

    return generate_alerts_task | save_scan_task
