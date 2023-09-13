from dataclasses import dataclass
from humitifier.html import MailTo, KvRow

from typing import TypeVar

_Component = TypeVar("_Component", MailTo, KvRow)

from .unknown import Unknown

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
    def from_host_state(cls, host_state) -> "Owner":
        try:
            return host_state[cls]
        except KeyError:
            return Unknown(
                prop_cls=cls,
                label="Owner",
                value="Unknown"
            )

    
    @staticmethod
    def query_option_set(items=list["Owner"]) -> set[str]:
        return set([o.name for o in items])
    
    def component(self, html_cls: type[_Component]) -> _Component:
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
    
    def filter(self, query: str) -> bool:
        return query in self.name or query in self.email