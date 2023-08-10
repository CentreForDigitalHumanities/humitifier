from dataclasses import dataclass
from pssh.output import HostOutput
from humitifier.html import (
    KvRow,
    KvTable, 
    HtmlString,
    HostCard, 
    HostModal,
    UnorderedList
)
from humitifier.config.facts import FactConfig
from humitifier.config.host import HostConfig
from humitifier.config.host_view import HostViewConfig
from humitifier.props.protocols import Property
from typing import TypeVar

Component= TypeVar("Component", KvTable, HostCard, HostModal)

@dataclass
class HostState:
    fqdn: Property
    data: dict[str, Property]
    view_cfg: HostViewConfig

    @classmethod
    def initialize(cls, cfg: HostConfig, outputs: list[HostOutput], fact_cfg: FactConfig, view_cfg: HostViewConfig) -> "HostState":
        facts = (fact_cfg.parse_output(output) for output in outputs)
        facts = {fact.alias: fact for fact in facts}
        return cls(
            fqdn=cfg.fqdn,
            data={**cfg.metadata_kv, **facts},
            view_cfg=view_cfg,
        )

    def __getitem__(self, key: type[Property]) -> Property:
        if key.alias in self.data:
            return self.data[key.alias]
        else:
            return key.from_host_state(self)

    def component(self, html_cls: type[Component]) -> Component:
        match html_cls.__name__:
            case KvTable.__name__:
                detail_props = (self[key] for key in self.view_cfg.table)
                rows = [x.component(KvRow) for x in detail_props]
                return KvTable(rows=rows)
            case HostCard.__name__:
                card_props = (self[key] for key in self.view_cfg.card)
                prop_list = UnorderedList(
                    items=[p.component(HtmlString) for p in card_props]
                )
                return HostCard(
                    fqdn=self.fqdn,
                    title=self.fqdn,
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
    