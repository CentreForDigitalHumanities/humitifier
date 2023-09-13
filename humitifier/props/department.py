from humitifier.html import HtmlString, KvRow

from typing import TypeVar
from .unknown import Unknown

_Component = TypeVar("_Component", HtmlString, KvRow)

class Department(str):

    @classmethod
    @property
    def alias(cls) -> str:
        return "department"
    
    @classmethod
    def from_host_state(cls, host_state) -> "Department":
        try:
            return host_state[cls]
        except KeyError:
            return Unknown(
                prop_cls=cls,
                label="Department",
                value="Unknown"
            )
    
    
    @staticmethod
    def query_option_set(items=list["Department"]) -> set[str]:
        return set(items)
    
    def component(self, html_cls: type[_Component]) -> _Component:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self)
            case KvRow.__name__:
                return KvRow(
                    label="Department", 
                    value=HtmlString(self)
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")
    
    def filter(self, query: str) -> bool:
        return query == self