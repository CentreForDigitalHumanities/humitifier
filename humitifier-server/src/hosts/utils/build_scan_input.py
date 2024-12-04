from hosts.models import Host
from humitifier_common.scan_data import FactScanOptions, ScanInput
from humitifier_common.facts import registry as facts_registry


def build_scan_input(hostname: str | Host) -> ScanInput:
    host = hostname
    if isinstance(hostname, str):
        host = Host.objects.get(fqdn=hostname)

    # TODO: proper scan input building
    all_facts = facts_registry.all()
    all_facts = [fact.__fact_name__ for fact in all_facts]

    requested_facts = {fact: FactScanOptions() for fact in all_facts}

    return ScanInput(hostname=host.fqdn, facts=requested_facts)
