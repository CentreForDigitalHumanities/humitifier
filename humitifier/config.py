from dataclasses import dataclass
from humitifier.models.host import Host
from humitifier import facts
from humitifier import filters
from humitifier.properties import metadata, facts as factprops
from humitifier.protocols import IFact, IFilter, IProperty
from typing import Type


DEFAULT_FACTS = [
    facts.HostnameCtl,
    facts.Memory,
    facts.Packages,
    facts.Uptime,
    facts.Blocks,
    facts.Users,
    facts.Groups
]

DEFAULT_METAPROPS = [
    metadata.Department,
    metadata.Owner,
    metadata.StartDate,
    metadata.EndDate,
    metadata.RetireIn,
    metadata.Purpose,
    metadata.People
]

DEFAULT_FACTPROPS = [
    factprops.Hostname,
    factprops.Os,
    factprops.PackageList,
    factprops.Memory,
    factprops.LocalStorage,
    factprops.Virtualization,
    factprops.Uptime
]

DEFAULT_GRIDPROPS = [
    factprops.Hostname,
    factprops.Os,
    factprops.Uptime
]

DEFAULT_FILTERS = [
    filters.HostnameFilter,
    filters.OsFilter,
    filters.PackageFilter,
    filters.DepartmentFilter,
    filters.OwnerFilter,
    filters.PersonFilter,
    filters.PurposeFilter
]

@dataclass
class AppConfig:
    """App configuration"""

    environment: str
    hosts: list[Host]
    # rules: list[RuleProtocol]
    facts: list[IFact]
    filters: list[Type[IFilter]]
    metadata_properties: list[Type[IProperty]]
    fact_properties: list[Type[IProperty]]
    grid_properties: list[Type[IProperty]]
    pssh_conf: dict[str, str]
    poll_interval: str

    @classmethod
    def default(cls, hosts: list[Host]) -> "AppConfig":
        return cls(
            environment="demo",
            hosts=hosts,
            # rules=[],
            facts=DEFAULT_FACTS,
            filters=DEFAULT_FILTERS,
            metadata_properties=DEFAULT_METAPROPS,
            fact_properties=DEFAULT_FACTPROPS,
            grid_properties=DEFAULT_GRIDPROPS,
            pssh_conf={},
            poll_interval="every 20 minutes",
        )

    @property
    def filter_kv(self) -> dict[str, Type[IFilter]]:
        return {f.slug: f for f in self.filters}