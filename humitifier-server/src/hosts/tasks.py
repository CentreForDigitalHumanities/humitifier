from celery import shared_task, signature

from hosts.utils import process_scan, historical_clean
from hosts.utils.build_scan_input import build_scan_input
from humitifier_common.scan_data import ScanOutput
from humitifier_common.celery.task_names import SCANNER_RUN_SCAN

from humitifier_server.celery.task_names import *


@shared_task(name=HOSTS_HISTORICAL_CLEAN)
def historical_clean_task():
    historical_clean()


@shared_task(name=HOSTS_START_SCAN, pydantic=True)
def start_scan(hostname: str):
    scan_input = build_scan_input(hostname)

    scan_task = signature(SCANNER_RUN_SCAN, args=(scan_input.model_dump(),))
    process_task = process_scan_output.signature()

    chain = scan_task | process_task
    chain = chain.on_error(on_scan_error.s())

    chain.apply_async()


@shared_task(name=HOSTS_PROCESS_SCAN, pydantic=True)
def process_scan_output(scan_output: ScanOutput):
    process_scan(scan_output)


@shared_task(name=HOSTS_SCAN_HANDLE_ERROR)
def on_scan_error(request, exc, traceback):
    # TODO: implement error handling
    print(f"Error: {exc}")
    print(f"Request: {request}")
    print(f"Traceback: {traceback}")
