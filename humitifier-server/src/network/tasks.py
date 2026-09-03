from datetime import timedelta

from celery import shared_task
from django.db.models import BooleanField, Func, Q, Value
from django.utils import timezone

from hosts.models import Host
from humitifier_common.index_data import IndexedIP

from humitifier_server.celery.task_names import *
from humitifier_server.logger import logger
from network.models import IPInfo
from network.utils import start_index


@shared_task(name=NETWORK_PROCESS_INDEXED_IP, pydantic=True)
def process_indexed_ip(indexed_ip: IndexedIP):

    try:
        ip = IPInfo.objects.get(ip_address=indexed_ip.ip_address)

    except IPInfo.DoesNotExist:
        logger.error(
            f"Received indexed IP for unknown IP address: {indexed_ip.ip_address}"
        )
        return

    ip.update_from_indexed_ip(indexed_ip)

    ##
    ## Get existing Hosts for the IP
    ##
    # By DNS
    entries = [
        entry[:-1] if entry.endswith(".") else entry for entry in ip.reverse_dns_entries
    ]
    hosts = Host.objects.exclude(archived=True).filter(fqdn__in=entries)
    ip.hosts_from_dns.set(hosts)

    # By IP
    class JSONBPathExists(Func):
        function = "jsonb_path_exists"
        output_field = BooleanField()

    search_term = ip.ip_address

    jsonpath_expr = (
        f'$.facts."generic.NetworkInterfaces"[*].addresses[*].address ? ('
        f'@ like_regex "{search_term}/" flag "i")'
    )

    hosts = Host.objects.exclude(archived=True).filter(
        JSONBPathExists("last_scan_cache", Value(jsonpath_expr))
    )
    ip.hosts_from_ip.set(hosts)
    ip.save()


@shared_task(name=NETWORK_INDEXER_SCHEDULER)
def indexer_scheduler(*, max_batch_size: int = 10, scan_interval_hours: int = 1):
    # Get a datetime to compare last schedules against. If the last scheduled index
    # of an IP was before this time, it is deemed 'schedulable'.
    scan_threshold_datetime = timezone.now() - timedelta(hours=scan_interval_hours)

    schedulable_ips = IPInfo.objects.filter(
        Q(last_index_scheduled__lt=scan_threshold_datetime)
        | Q(last_index_scheduled__isnull=True)
    )

    if schedulable_ips.count() == 0:
        return "No IPs were due for scanning"

    # Slice our results to a max of max_batch_size if we have more than our max batch
    # size
    if schedulable_ips.count() > max_batch_size:
        schedulable_ips = schedulable_ips[:max_batch_size]

    for ip in schedulable_ips:
        start_index(ip)

    return "Scheduled the following IPs: {}".format(
        ", ".join([str(ip.ip_address) for ip in schedulable_ips])
    )
