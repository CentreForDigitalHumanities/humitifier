from humitifier.html import HostCard, HostGrid, HostGridItems
from humitifier.config.app import AppConfig
from .host import HostState

from typing import TypeVar

Component = TypeVar("Component", HostGrid, HostGridItems)


class HostCollectionState(dict[str, HostState]):
    @classmethod
    def initialize(cls, app_config: AppConfig) -> "HostCollectionState":
        fact_cfg = app_config.facts
        all_outputs = app_config.collect_outputs()
        hosts = app_config.hosts
        data = {
            hostcfg.fqdn: HostState(
                config=hostcfg,
                fact_data=fact_cfg.initialize_host_fact_data([o for o in all_outputs if o.host == hostcfg.fqdn]),
            )
            for hostcfg in hosts
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
