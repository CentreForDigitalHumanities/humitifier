from humitifier.facts.hostnamectl import HostnameCtl
from humitifier.html import HtmlString, KvRow

from typing import TypeVar

_Component = TypeVar("_Component", HtmlString, KvRow)
from .unknown import Unknown
class Virtualization(str):

    @classmethod
    @property
    def alias(cls) -> str:
        return "virtualization"
    
    @classmethod
    def from_host_state(cls, host_state) -> "Virtualization":
        try:
            return cls(host_state[HostnameCtl].virtualization)
        except KeyError:
            return Unknown(
                prop_cls=cls,
                label="Department",
                value="Unknown"
            )

    
    def component(self, html_cls: type[_Component]) -> _Component:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self)
            case KvRow.__name__:
                return KvRow(
                    label="Virtualization", 
                    value=HtmlString(self)
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")