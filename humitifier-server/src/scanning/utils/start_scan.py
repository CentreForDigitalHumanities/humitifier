from datetime import UTC, datetime, timedelta

from celery import signature
from django.utils import timezone

from hosts.models import Host
from humitifier_common.celery.task_names import SCANNER_RUN_SCAN
from humitifier_server.celery.task_names import *


def start_full_scan(
    host: Host, *, force: bool = False, delay_seconds: int | None = None
):
    host.last_scan_scheduled = timezone.now()
    host.save()

    _start_scan(host, force=force, delay_seconds=delay_seconds)


def _start_scan(
    host: Host,
    *,
    force: bool = False,
    delay_seconds: int | None = None,
):
    # Get our generic log-error handler-task
    log_error_task = signature(MAIN_LOG_ERROR)

    # Setup scan input creation
    get_scan_input_task = signature(SCANNING_GET_SCAN_INPUT, args=(host.fqdn, force))
    get_scan_input_task.on_error(log_error_task)

    # Setup scan running
    run_scan_task = signature(SCANNER_RUN_SCAN)

    on_scan_error = signature(SCANNING_SCAN_HANDLE_ERROR)
    run_scan_task.on_error(on_scan_error)

    # Setup scan processing
    generate_alerts_task = signature(ALERTING_GENERATE_ALERTS)
    generate_alerts_task.on_error(log_error_task)

    save_scan_task = signature(SCANNING_SAVE_SCAN)
    save_scan_task.on_error(log_error_task)

    # Setup the task-chain
    chain = get_scan_input_task | run_scan_task | generate_alerts_task | save_scan_task

    # Schedule our tasks
    eta = None
    if delay_seconds:
        eta = datetime.now(UTC) + timedelta(seconds=delay_seconds)

    chain.apply_async(eta=eta)
