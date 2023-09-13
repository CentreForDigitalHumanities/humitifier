from pssh.output import HostOutput
from humitifier.html import HostCard, HostGrid, HostGridItems
from humitifier.config.host import HostConfig
from humitifier.config.facts import FactConfig
from .host import HostState

from typing import TypeVar

Component = TypeVar("Component", HostGrid, HostGridItems)

class HostCollectionState(dict[str, HostState]):

    @classmethod
    def initialize(
        cls, 
        hosts: list[HostConfig], 
        all_outputs: list[HostOutput], 
        fact_cfg: FactConfig, 
    ) -> "HostCollectionState":
        data = {
            hostcfg.fqdn: HostState(
                config=hostcfg,
                fact_data=fact_cfg.initialize_host_fact_data(
                    [o for o in all_outputs if o.host == hostcfg.fqdn]
                )
            ) for hostcfg in hosts
        }
        return cls(data)


    def component(self, html_cls: type[Component]) -> Component:
        match html_cls.__name__:
            case HostGridItems.__name__:
                items = [x.component(HostCard) for x in self.values()]
                return HostGridItems(items=items)
            case HostGrid.__name__:
                items = self.component(HostGridItems)
                return HostGrid(items=items)
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")
