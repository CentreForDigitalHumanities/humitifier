from datetime import date
from humitifier.models.host_state import HostState
from humitifier.html import HtmlString, KvRow

_HtmlComponent = HtmlString | KvRow


class EndDate(date):

    @classmethod
    @property
    def alias(cls) -> str:
        return "end_date"
    
    @classmethod
    def from_host_state(cls, host_state: HostState) -> "EndDate":
        return cls.fromisoformat(host_state.metadata[cls.alias])
    
    def component(self, html_cls: type[_HtmlComponent]) -> _HtmlComponent:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self.isoformat())
            case KvRow.__name__:
                return KvRow(
                    label="End Date", 
                    value=HtmlString(self.isoformat())
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")