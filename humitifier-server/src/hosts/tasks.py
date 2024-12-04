from celery import shared_task, signature

from hosts.utils import process_scan, historical_clean
from hosts.utils.build_scan_input import build_scan_input
from humitifier_common.scan_data import ScanOutput


@shared_task(name="server.hosts.historical_clean")
def historical_clean_task():
    historical_clean()


@shared_task(name="server.hosts.start_scan", pydantic=True)
def start_scan(hostname: str):
    scan_input = build_scan_input(hostname)

    scan_task = signature("agent.run_scan", args=(scan_input.model_dump(),))
    process_task = process_scan_output.signature()

    chain = scan_task | process_task
    chain = chain.on_error(on_scan_error.s())

    chain.apply_async()


@shared_task(name="server.hosts.process_scan", pydantic=True)
def process_scan_output(scan_output: ScanOutput):
    process_scan(scan_output)


@shared_task(name="server.hosts.on_scan_error")
def on_scan_error(request, exc, traceback):
    # TODO: implement error handling
    print(f"Error: {exc}")
    print(f"Request: {request}")
    print(f"Traceback: {traceback}")
