from dataclasses import dataclass
from humitifier.models.host_state import HostState
from humitifier.html import MailTo, KvRow

_HtmlComponent = MailTo | KvRow


@dataclass
class Owner:
    name: str
    email: str
    notes: str | None = None

    @classmethod
    @property
    def alias(cls) -> str:
        return "owner"
    
    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Owner":
        return cls(**host_state.metadata[cls.alias])
    
    def component(self, html_cls: type[_HtmlComponent]) -> _HtmlComponent:
        match html_cls.__name__:
            case MailTo.__name__:
                return MailTo(
                    name=self.name,
                    email=self.email,
                    info=self.notes,
                )
            case KvRow.__name__:
                return KvRow(
                    label="Owner",
                    value=self.component(MailTo),
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")