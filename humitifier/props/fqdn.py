from humitifier.html import HtmlString, KvRow

from typing import TypeVar

_Component = TypeVar("_Component", HtmlString, KvRow)

class Fqdn(str):

    @classmethod
    @property
    def alias(cls) -> str:
        return "fqdn"
    
    @classmethod
    def from_host_state(cls, host_state) -> "Fqdn":
        return host_state.fqdn
    
    def component(self, html_cls: type[_Component]) -> _Component:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self)
            case KvRow.__name__:
                return KvRow(
                    label="FQDN", 
                    value=HtmlString(self)
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")