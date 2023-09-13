from datetime import date
from humitifier.html import HtmlString, KvRow

from typing import TypeVar
from .unknown import Unknown

_Component = TypeVar("_Component", HtmlString, KvRow)


class EndDate(date):

    @classmethod
    @property
    def alias(cls) -> str:
        return "end_date"
    
    @classmethod
    def from_host_state(cls, host_state) -> "EndDate":
        try:
            return host_state[cls]
        except KeyError:
            return Unknown(
                prop_cls=cls,
                label="End Date",
                value="No end date known"
            )
    
    def component(self, html_cls: type[_Component]) -> _Component:
        match html_cls.__name__:
            case HtmlString.__name__:
                if isinstance(self, date):
                    return HtmlString(self.isoformat())
                else:
                    return HtmlString(self)
            case KvRow.__name__:
                return KvRow(
                    label="End Date", 
                    value=self.component(HtmlString)
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")