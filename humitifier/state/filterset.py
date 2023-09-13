
from dataclasses import dataclass
from humitifier.html import SelectInput, SearchInput, FilterSet
from humitifier.config.filterset import FiltersetConfig, FilterConfig
from .host import HostState
from humitifier.props.unknown import Unknown

Widget = SelectInput | SearchInput

@dataclass
class HostStateFilterset:
    widgets: list[Widget]
    config: FiltersetConfig

    @staticmethod
    def _filter_widget(hosts: list[HostState], cfg: FilterConfig) -> Widget:
        f_prop, html_cls = cfg
        values = [f_prop.from_host_state(h) for h in hosts]
        known_values = [v for v in values if not isinstance(v, Unknown)]
        return html_cls(
            name=f_prop.alias,
            label=f_prop.alias,
            options=list(f_prop.query_option_set(known_values)) + ["unknown"]
        )
    

    @classmethod
    def initialize(cls, hosts: list[HostState], cfg: FiltersetConfig):
        return cls(
            widgets=[cls._filter_widget(hosts, f_cfg) for f_cfg in cfg],
            config=cfg
        )


    def component(self, html_cls: type[FilterSet]) -> FilterSet:
        match html_cls.__name__:
            case FilterSet.__name__:
                return html_cls(widgets=self.widgets)
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")
            
    
    def apply(self, query_kv: dict[str, str], hosts: list[HostState]) -> list[HostState]:
        queries = [(self.config.kv[k], v) for k, v in query_kv.items()]

        def _filter_host(host: HostState) -> bool:
            return all([f.from_host_state(host).filter(v) for f, v in queries])
        
        return list(filter(_filter_host, hosts))
