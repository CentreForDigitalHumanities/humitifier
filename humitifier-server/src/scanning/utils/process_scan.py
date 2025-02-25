from hosts.models import Host
from humitifier_common.scan_data import ScanOutput
from humitifier_server.logger import logger


def process_scan(scan_output: ScanOutput):
    try:
        host = Host.objects.get(fqdn=scan_output.hostname)
    except Host.DoesNotExist:
        logger.error("Received scan output for unknown host")
        return

    if scan_output.errors:
        logger.error(f"Errors for {host.fqdn}: {scan_output.errors}")

    host.add_scan(scan_output.model_dump())
