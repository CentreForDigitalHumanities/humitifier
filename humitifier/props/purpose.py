from humitifier.models.host_state import HostState
from humitifier.html import HtmlString, KvRow

_HtmlComponent = HtmlString | KvRow


class Purpose(str):

    @classmethod
    @property
    def alias(cls) -> str:
        return "purpose"
    
    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Purpose":
        return cls(host_state.metadata[cls.alias])
    
    def component(self, html_cls: type[_HtmlComponent]) -> _HtmlComponent:
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