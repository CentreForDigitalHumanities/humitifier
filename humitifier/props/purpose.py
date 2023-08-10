from humitifier.html import HtmlString, KvRow

from typing import TypeVar

_Component = TypeVar("_Component", HtmlString, KvRow)


class Purpose(str):

    @classmethod
    @property
    def alias(cls) -> str:
        return "purpose"
    
    @staticmethod
    def query_option_set(items=list["Purpose"]) -> set[str]:
        return set(items)
    
    @classmethod
    def from_host_state(cls, host_state) -> "Purpose":
        return host_state[cls]
    
    def component(self, html_cls: type[_Component]) -> _Component:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self)
            case KvRow.__name__:
                return KvRow(
                    label="Purpose", 
                    value=HtmlString(self)
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")
            
    def filter(self, query: str) -> bool:
        return query == self