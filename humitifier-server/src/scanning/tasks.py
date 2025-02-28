from celery import shared_task, signature

from humitifier_common.scan_data import ScanOutput
from humitifier_common.celery.task_names import SCANNER_RUN_SCAN

from humitifier_server.celery.task_names import *
from humitifier_server.logger import logger
from hosts.models import Host
from scanning.utils.process_scan import process_scan


@shared_task(name=SCANNING_START_SCAN, pydantic=True)
def start_scan(hostname: str):
    try:
        host = Host.objects.get(fqdn=hostname)
    except Host.DoesNotExist:
        logger.error(f"Start-scan: Host {hostname} is not found")
        return

    scan_input = host.get_scan_input()

    scan_task = signature(SCANNER_RUN_SCAN, args=(scan_input.model_dump(),))
    process_task = process_scan_output.signature()

    chain = scan_task | process_task
    chain = chain.on_error(on_scan_error.s())

    chain.apply_async()


@shared_task(name=SCANNING_PROCESS_SCAN, pydantic=True)
def process_scan_output(scan_output: ScanOutput):
    process_scan(scan_output)


@shared_task(name=SCANNING_SCAN_HANDLE_ERROR)
def on_scan_error(id, **kwargs):
    logger.error(f"Error during task id: %s", kwargs)
    # TODO: add alert
