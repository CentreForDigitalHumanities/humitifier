from dataclasses import dataclass
from humitifier.props import Fqdn
from humitifier.props.protocols import Property

from .host_view import HostViewConfig
from .rules import RuleConfig


@dataclass(frozen=True)
class HostConfig:
    fqdn: Fqdn
    metadata: list[Property]
    view_cfg: HostViewConfig | None = None
    rule_cfg: RuleConfig | None = None

    @property
    def metadata_kv(self) -> dict[str, Property]:
        return {prop.alias: prop for prop in self.metadata}
