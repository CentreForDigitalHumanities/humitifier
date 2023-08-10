from dataclasses import dataclass
from humitifier.props import Fqdn
from humitifier.props.protocols import Property

from .host_view import HostViewConfig


@dataclass(frozen=True)
class HostConfig:
    fqdn: Fqdn
    metadata: list[Property]
    view_cfg: HostViewConfig | None = None


    @property
    def metadata_kv(self) -> dict[str, Property]:
        return {prop.alias: prop for prop in self.metadata}