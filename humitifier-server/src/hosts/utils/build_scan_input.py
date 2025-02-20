from hosts.models import Host
from humitifier_common.scan_data import ScanInput


def build_scan_input(hostname: str | Host) -> ScanInput:
    # TODO: move method to scanning
    host = hostname
    if isinstance(hostname, str):
        host = Host.objects.get(fqdn=hostname)

    return host.get_scan_input()
