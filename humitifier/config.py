from dataclasses import dataclass
from humitifier.models.host import Host
from humitifier.filters import Filter
from humitifier.properties import MetadataProperty, FactProperty
from humitifier.rules import Rule as RuleProtocol


@dataclass
class AppConfig:
    """App configuration"""

    environment: str
    hosts: list[Host]
    rules: list[RuleProtocol]
    filters: list[Filter]
    metadata_properties: list[MetadataProperty]
    fact_properties: list[FactProperty]
    grid_properties: list[MetadataProperty | FactProperty]
    pssh_conf: dict[str, str]
    poll_interval: str

    @classmethod
    def default(cls, hosts: list[Host]) -> "AppConfig":
        return cls(
            environment="demo",
            hosts=hosts,
            rules=[],
            filters=list(Filter),
            metadata_properties=list(MetadataProperty),
            fact_properties=list(FactProperty),
            grid_properties=[
                FactProperty.Hostname,
                FactProperty.Os,
                FactProperty.UptimeDays
            ],
            pssh_conf={},
            poll_interval="every 20 minutes",
        )