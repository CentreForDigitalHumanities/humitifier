from dataclasses import dataclass
from .protocols import Property

from humitifier.html import HtmlString, KvRow

from typing import TypeVar


_Component = TypeVar("_Component", HtmlString, KvRow)

@dataclass
class Unknown:
    prop_cls: type[Property]
    label: str
    value: str = "UNKNOWN"

    def filter(self, query: str) -> bool:
        return query == "unknown"
    
    def component(self, html_cls: type[_Component]) -> _Component:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self.value)
            case KvRow.__name__:
                return KvRow(
                    label=self.label, 
                    value=self.component(HtmlString)
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")