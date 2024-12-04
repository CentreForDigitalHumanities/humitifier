from humitifier_common.scan_data import ScanInput, ScanOutput
from .config import app
from ..scanner import scan


@app.task(name="agent.run_scan", pydantic=True)
def run_scan(scan_input: ScanInput) -> ScanOutput:
    return scan(scan_input)
