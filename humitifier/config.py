from dataclasses import dataclass
from humitifier.models.host import Host
from humitifier.filters import Filter as FilterProtocol
from humitifier.meta_properties import MetaProp as MetaPropProtocol
from humitifier.rules import Rule as RuleProtocol


@dataclass
class AppConfig:
    """App configuration"""

    environment: str
    hosts: list[Host]
    rules: list[RuleProtocol]
    filters: list[FilterProtocol]
    meta_properties: list[MetaPropProtocol]
    pssh_conf: dict[str, str]
    poll_interval: str
