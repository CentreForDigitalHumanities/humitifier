from datetime import timedelta

from celery import shared_task, signature
from django.db.models import Q
from django.utils import timezone

from humitifier_common.scan_data import ScanInput, ScanOutput
from humitifier_common.celery.task_names import SCANNER_RUN_SCAN

from humitifier_server.celery.task_names import *
from humitifier_server.logger import logger
from hosts.models import Host, ScanScheduling
from scanning.utils import start_full_scan as queue_full_scan


@shared_task(name=SCANNING_GET_SCAN_INPUT, pydantic=True)
def get_scan_input_from_host(fqdn: str, force: bool = False) -> ScanInput:
    try:
        # Attempt to fetch the host based on the FQDN. Log an error if the host does not exist.
        host = Host.objects.get(fqdn=fqdn)
    except Host.DoesNotExist as e:
        logger.error(f"Start-scan: Host {fqdn} is not found")
        raise e

    # Check if the host's data source allows scheduled scanning, and handle non-schedulable cases unless forced.
    if (
        not host.data_source
        or host.data_source.scan_scheduling != ScanScheduling.SCHEDULED
    ):
        if not force:
            logger.error(f"Start-scan: scan requested for non-schedulable host {fqdn}")
            raise RuntimeError("Scan requested for non-schedulable host")

    # Prepare the scan input, create a task chain for scanning and processing, and handle potential errors.
    scan_input = host.get_scan_input()

    if not scan_input:
        logger.error("Start-scan: scan requested for host without scan spec set")
        raise ValueError("Missing scan spec")

    return scan_input


@shared_task(name=SCANNING_SAVE_SCAN, pydantic=True)
def save_scan(scan_output: ScanOutput | None):
    # Happens if the previous step decided that the scan is invalid
    if scan_output is None:
        return

    try:
        host = Host.objects.get(fqdn=scan_output.hostname)
    except Host.DoesNotExist:
        logger.error("Received scan output for unknown host")
        return

    if scan_output.errors:
        logger.error(f"Errors for {host.fqdn}: {scan_output.errors}")

    host.add_scan(scan_output.model_dump())


@shared_task(name=SCANNING_SCAN_HANDLE_ERROR)
def on_scan_error(id, **kwargs):
    logger.error(f"Error during task id: %s", kwargs)


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
