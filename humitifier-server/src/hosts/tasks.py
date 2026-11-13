from celery import shared_task
from humitifier_common.artefacts import HostnameCtl
from humitifier_common.scan_data import ScanOutput

from hosts.models import OperatingSystem
from hosts.utils import historical_clean
from humitifier_server.celery.task_names import *


@shared_task(name=HOSTS_HISTORICAL_CLEAN)
def historical_clean_task():
    historical_clean()


@shared_task(name=HOSTS_UPDATE_OS_LIST, pydantic=True)
def update_os_list_task(scan_output: ScanOutput) -> None:
    if not scan_output or scan_output.version <= 1:
        return

    hostname_info: HostnameCtl | None = scan_output.facts.get("generic.HostnameCtl")
    if not hostname_info or not hostname_info.os:
        return

    os = hostname_info.os

    if not OperatingSystem.objects.filter(name=os).exists():
        OperatingSystem.objects.create(name=os)
