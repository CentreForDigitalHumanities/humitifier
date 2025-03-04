from datetime import UTC, datetime, timedelta

from celery import signature
from django.utils import timezone

from hosts.models import Host
from humitifier_server.celery.task_names import SCANNING_START_FULL_SCAN


def start_full_scan(host: Host, *, force=False, delay_seconds=None):
    host.last_scan_scheduled = timezone.now()
    host.save()

    eta = None
    if delay_seconds:
        eta = datetime.now(UTC) + timedelta(seconds=delay_seconds)

    task = signature(SCANNING_START_FULL_SCAN, args=(host.fqdn, force))

    return task.apply_async(eta=eta)
