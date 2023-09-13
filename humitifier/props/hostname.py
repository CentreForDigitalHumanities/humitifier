from humitifier.facts.hostnamectl import HostnameCtl
from humitifier.html import HtmlString, KvRow

from typing import TypeVar

_Component = TypeVar("_Component", HtmlString, KvRow)
from .unknown import Unknown

class Hostname(str):

    @classmethod
    @property
    def alias(cls) -> str:
        return "hostname"
    
    @classmethod
    def from_host_state(cls, host_state) -> "Hostname":
        try:
            return cls(host_state[HostnameCtl].hostname)
        except KeyError:
            return Unknown(
                prop_cls=cls,
                label="Hostname",
                value="Unknown"
            )

    
    @staticmethod
    def query_option_set(items=list["Hostname"]) -> set[str]:
        return set(items)
    
    def component(self, html_cls: type[_Component]) -> _Component:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self)
            case KvRow.__name__:
                return KvRow(
                    label="Hostname", 
                    value=HtmlString(self)
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")
            
    def filter(self, query: str) -> bool:
        return query in self