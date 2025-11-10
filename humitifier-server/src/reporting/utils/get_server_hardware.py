from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from hosts.models import Host, ScanData
from humitifier_common.artefacts import Hardware, HostnameCtl


@dataclass
class Server:
    hostname: str
    hardware: Hardware
    scan_date: datetime


def get_hardware_for_hosts(hosts: Iterable[Host]) -> list[Server]:
    output: list[Server] = []

    for host in hosts:
        scan_obj: ScanData = host.get_scan_object()

        if server := get_hardware_fact(scan_obj):
            output.append(server)

    return output


def get_hardware_fact(scan_obj: ScanData) -> Server | None:
    if not scan_obj:
        return None

    # Sometimes we have an empty scan, for some reason
    if not scan_obj.version:
        return None

    if not scan_obj.version >= 2:
        return None

    if Hardware.__artefact_name__ not in scan_obj.parsed_data.facts:
        return None

    if scan_obj.parsed_data.facts[Hardware.__artefact_name__] is None:
        return None

    if HostnameCtl.__artefact_name__ in scan_obj.parsed_data.facts:
        hostname_ctl: HostnameCtl = scan_obj.parsed_data.facts[
            HostnameCtl.__artefact_name__
        ]
        if hostname_ctl.virtualization != "vmware":
            return None

    hardware: Hardware = scan_obj.parsed_data.facts[Hardware.__artefact_name__]

    return Server(
        hostname=scan_obj.parsed_data.hostname,
        scan_date=scan_obj.scan_date,
        hardware=hardware,
    )
