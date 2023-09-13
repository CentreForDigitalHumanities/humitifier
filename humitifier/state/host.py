from dataclasses import dataclass
from humitifier.html import KvRow, KvTable, HtmlString, HostCard, HostModal, UnorderedList
from humitifier.config.host import HostConfig
from humitifier.props.protocols import Property
from typing import TypeVar

Component = TypeVar("Component", KvTable, HostCard, HostModal)


@dataclass
class HostState:
    fact_data: dict[str, Property]
    config: HostConfig

    @property
    def fqdn(self) -> str:
        return self.config.fqdn

    def __getitem__(self, key: type[Property]) -> Property:
        if key.alias in self.fact_data:
            return self.fact_data[key.alias]
        elif key.alias in self.config.metadata_kv:
            return self.config.metadata_kv[key.alias]
        else:
            raise KeyError(str(key))

    def component(self, html_cls: type[Component]) -> Component:
        match html_cls.__name__:
            case KvTable.__name__:
                detail_props = (prop_cls.from_host_state(self) for prop_cls in self.config.view_cfg.table)
                rows = [x.component(KvRow) for x in detail_props]
                return KvTable(rows=rows)
            case HostCard.__name__:
                card_props = [prop_cls.from_host_state(self) for prop_cls in self.config.view_cfg.card]
                prop_list = UnorderedList(items=[p.component(HtmlString) for p in card_props])
                return HostCard(
                    fqdn=self.config.fqdn,
                    title=self.config.fqdn,
                    properties=prop_list,
                    issue_count=0,
                )
            case HostModal.__name__:
                table = self.component(KvTable)
                return HostModal(
                    table=table,
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")
