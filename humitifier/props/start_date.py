from datetime import date
from humitifier.html import HtmlString, KvRow

from typing import TypeVar

_Component = TypeVar("_Component", HtmlString, KvRow)

class StartDate(date):

    @classmethod
    @property
    def alias(cls) -> str:
        return "start_date"
    
    @classmethod
    def from_host_state(cls, host_state) -> "StartDate":
        return host_state[cls]
    
    def component(self, html_cls: type[_Component]) -> _Component:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self.isoformat())
            case KvRow.__name__:
                return KvRow(
                    label="Start Date", 
                    value=HtmlString(self.isoformat())
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")