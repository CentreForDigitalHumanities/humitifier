from celery import signature

from hosts.models import Host
from humitifier_server.celery.task_names import *


def regenerate_alerts(host: Host):

    scan_data = host.get_scan_object()
    if not scan_data:
        return

    scan_output = scan_data.parsed_data

    # Get our generic log-error handler-task
    log_error_task = signature(MAIN_LOG_ERROR)

    generate_alerts_task = signature(
        ALERTING_GENERATE_ALERTS, args=(scan_output.model_dump(mode="json"),)
    )
    generate_alerts_task.on_error(log_error_task)

    return generate_alerts_task.delay()
