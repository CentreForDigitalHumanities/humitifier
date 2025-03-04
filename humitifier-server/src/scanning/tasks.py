from datetime import timedelta

from celery import shared_task, signature
from django.db.models import Q
from django.utils import timezone

from humitifier_common.scan_data import ScanOutput
from humitifier_common.celery.task_names import SCANNER_RUN_SCAN

from humitifier_server.celery.task_names import *
from humitifier_server.logger import logger
from hosts.models import Host, ScanScheduling
from scanning.utils.process_scan import process_scan
from scanning.utils.start_scan import start_full_scan as queue_full_scan


@shared_task(name=SCANNING_START_FULL_SCAN, pydantic=True)
def start_full_scan(hostname: str, force=False):
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
    # TODO: TypeError('Object of type ErrorTypeEnum is not JSON serializable')
    # Probably a host-not-found error


@shared_task(name=SCANNING_SCAN_HANDLE_ERROR)
def on_scan_error(id, **kwargs):
    logger.error(f"Error during task id: %s", kwargs)
    # TODO: add alert


@shared_task(name=SCANNING_FULL_SCAN_SCHEDULER)
def schedule_full_scans(
    *, max_batch_size: int = 10, scan_interval_hours: int = 1
) -> str:
    """
    Schedules full host scans for eligible hosts based on the provided criteria. The
    function considers only hosts marked as schedulable and checks their last scheduled
    scan time against a calculated threshold. Hosts that satisfy the conditions are
    processed up to a specified maximum batch size.

    :param max_batch_size: The maximum number of hosts that can be scheduled for scans in
        a single execution.
    :type max_batch_size: int
    :param scan_interval_hours: The time interval in hours used to determine the threshold
        for scheduling hosts. Only hosts whose last scan was scheduled before this time
        (or never scheduled) are eligible.
    :type scan_interval_hours: int
    :return: str
    """
    # Get a datetime to compare last schedules against. If the last scheduled scan
    # of a host was before this time, it is deemed 'schedulable'.
    scan_threshold_datetime = timezone.now() - timedelta(hours=scan_interval_hours)

    schedulable_hosts = (
        Host.objects.filter(
            # Ignore any host that is not explicitly marked as auto-schedulable
            data_source__scan_scheduling=ScanScheduling.SCHEDULED,
        )
        .filter(
            # Filter out any that have had a scan scheduled after our threshold
            Q(last_scan_scheduled__lte=scan_threshold_datetime)
            |
            # Also allow those without any previous scan scheduled
            Q(last_scan_scheduled=None),
        )
        .order_by(
            # Sort by last scan scheduled dt, so we always scan the host that was
            # scanned the furthest back first.
            "last_scan_scheduled"
        )
    )

    if schedulable_hosts.count() == 0:
        return "No hosts were due for scanning"

    # Slice our results to a max of max_batch_size if we have more than our max batch
    # size
    if schedulable_hosts.count() > max_batch_size:
        schedulable_hosts = schedulable_hosts[:max_batch_size]

    for host in schedulable_hosts:
        queue_full_scan(host)

    return "Scheduled the following hosts: {}".format(
        ", ".join([host.fqdn for host in schedulable_hosts])
    )
