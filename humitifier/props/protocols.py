from abc import abstractmethod
from typing import Protocol, runtime_checkable

@runtime_checkable
class Property(Protocol):
    """A property is a component that can be rendered to HTML."""

    @classmethod
    @property
    @abstractmethod
    def alias(cls) -> str: ...

    @classmethod
    @abstractmethod
    def from_host_state(cls, host_state): ...

    @abstractmethod
    def component(self, html_cls): ...