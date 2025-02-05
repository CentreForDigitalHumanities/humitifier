from humitifier_common.celery.task_names import SCANNER_RUN_SCAN
from humitifier_common.scan_data import ScanInput, ScanOutput
from .config import app
from ..scanner import scan


@app.task(name=SCANNER_RUN_SCAN, pydantic=True)
def run_scan(scan_input: ScanInput) -> ScanOutput:
    return scan(scan_input)
