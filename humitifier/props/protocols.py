from abc import abstractmethod
from typing import Protocol, runtime_checkable

@runtime_checkable
class Property(Protocol):
    @classmethod
    @property
    @abstractmethod
    def alias(cls) -> str: ...

    @classmethod
    @abstractmethod
    def from_host_state(cls, host_state): ...

    @abstractmethod
    def component(self, html_cls): ...


@runtime_checkable
class Filterable(Protocol):

    @abstractmethod
    def filter(self, query: str) -> bool: ...

