from dataclasses import dataclass
from humitifier.models.host import Host
from humitifier.protocols import IFact


@dataclass
class HostState:
    host: Host
    facts: dict[str, IFact]

    @classmethod
    def from_host_facts(cls, host: Host, facts: list[tuple[str, IFact]]) -> "HostState":
        host_facts = {fact.alias: fact for fqdn, fact in facts if fqdn == host.fqdn}
        return cls(host=host, facts=host_facts)