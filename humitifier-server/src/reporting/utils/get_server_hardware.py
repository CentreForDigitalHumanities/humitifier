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


def get_server_hardware(hosts: Iterable[Host]) -> list[Server]:
    output: list[Server] = []

    for host in hosts:
        scan_obj: ScanData = host.get_scan_object()
        if not scan_obj.version >= 2:
            continue

        if Hardware.__artefact_name__ not in scan_obj.parsed_data.facts:
            continue

        if scan_obj.parsed_data.facts[Hardware.__artefact_name__] is None:
            continue

        if HostnameCtl.__artefact_name__ in scan_obj.parsed_data.facts:
            hostname_ctl: HostnameCtl = scan_obj.parsed_data.facts[
                HostnameCtl.__artefact_name__
            ]
            if hostname_ctl.virtualization != "vmware":
                continue

        hardware: Hardware = scan_obj.parsed_data.facts[Hardware.__artefact_name__]

        output.append(
            Server(
                hostname=scan_obj.parsed_data.hostname,
                scan_date=scan_obj.scan_date,
                hardware=hardware,
            )
        )

    return output
