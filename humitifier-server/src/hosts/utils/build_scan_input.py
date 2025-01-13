from hosts.models import Host
from humitifier_common.scan_data import ArtefactScanOptions, ScanInput
from humitifier_common.artefacts import registry as facts_registry


def build_scan_input(hostname: str | Host) -> ScanInput:
    host = hostname
    if isinstance(hostname, str):
        host = Host.objects.get(fqdn=hostname)

    # TODO: proper scan input building
    all_facts = facts_registry.all()
    all_facts = [fact.__artefact_name__ for fact in all_facts]

    requested_facts = {fact: ArtefactScanOptions() for fact in all_facts}

    return ScanInput(hostname=host.fqdn, artefacts=requested_facts)
