from celery import shared_task, signature

from humitifier_common.scan_data import ScanOutput
from humitifier_common.celery.task_names import SCANNER_RUN_SCAN

from humitifier_server.celery.task_names import *
from humitifier_server.logger import logger
from hosts.models import Host
from scanning.utils.process_scan import process_scan


@shared_task(name=SCANNING_START_SCAN, pydantic=True)
def start_scan(hostname: str, force=False):
    """
    Initiates a scanning process for a specified host. The function first attempts to locate the host
    using its fully qualified domain name (FQDN). If found, it validates whether the host's data
    source allows scheduled scanning unless explicitly forced. Upon successful validation, the function
    prepares the scanning input and creates a task chain to execute the scanning and process the
    scan results.

    :param hostname: The fully qualified domain name (FQDN) of the host to be scanned.
    :param force: A boolean flag to override scanning restrictions for non-schedulable hosts.
    :type hostname: str
    :type force: bool
    :return: None
    :rtype: None
    """
    try:
        # Attempt to fetch the host based on the FQDN. Log an error if the host does not exist.
        host = Host.objects.get(fqdn=hostname)
    except Host.DoesNotExist:
        logger.error(f"Start-scan: Host {hostname} is not found")
        return

    # Check if the host's data source allows scheduled scanning, and handle non-schedulable cases unless forced.
    if (
        not host.data_source
        or host.data_source.scan_scheduling != ScanScheduling.SCHEDULED
    ):
        if not force:
            logger.error(
                f"Start-scan: scan requested for non-schedulable host {hostname}"
            )
            return

    # Prepare the scan input, create a task chain for scanning and processing, and handle potential errors.
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
