from hosts.models import Host
from humitifier_common.scan_data import ScanOutput


def process_scan(scan_output: ScanOutput):
    # TODO: no auto create!
    host, created = Host.objects.get_or_create(fqdn=scan_output.hostname)

    if scan_output.errors:
        print(f"Errors for {host.fqdn}: {scan_output.errors}")

    facts = {}
    for fact_name, fact_data in scan_output.facts.items():
        fact_name = fact_name.split(".", 1)[1]
        facts[fact_name] = fact_data

    host.add_scan(facts)
