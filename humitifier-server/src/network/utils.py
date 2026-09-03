from typing import Optional

from datetime import UTC, datetime, timedelta

from celery import signature
from django.utils import timezone

from network.models import IPInfo
from humitifier_common.index_data import IndexIPInput
from humitifier_common.celery.task_names import NETWORK_INDEXER_INDEX_IP
from humitifier_server.celery.task_names import *


def start_index(
    ip: IPInfo, *, ports: Optional[list[int]] = None, delay_seconds: int | None = None
):
    ip.last_index_scheduled = timezone.now()
    ip.save()

    _start_index(ip, ports=ports, delay_seconds=delay_seconds)


def _start_index(
    ip: IPInfo, *, ports: Optional[list[int]] = None, delay_seconds: int | None = None
):

    # Get our generic log-error handler-task
    log_error_task = signature(MAIN_LOG_ERROR)

    index_task = signature(
        NETWORK_INDEXER_INDEX_IP,
        kwargs={
            "ip": IndexIPInput(ip_address=ip.ip_address, ports=ports or []).model_dump()
        },
    )

    on_index_error = signature(NETWORK_INDEX_HANDLE_ERROR)
    index_task.on_error(on_index_error)

    process_task = signature(NETWORK_PROCESS_INDEXED_IP)
    process_task.on_error(log_error_task)

    chain = index_task | process_task

    # Schedule our tasks
    eta = None
    if delay_seconds:
        eta = datetime.now(UTC) + timedelta(seconds=delay_seconds)

    return chain.apply_async(eta=eta)
