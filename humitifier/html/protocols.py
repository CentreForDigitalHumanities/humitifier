from abc import abstractmethod
from typing import Protocol, runtime_checkable

@runtime_checkable
class HtmlComponent(Protocol):
    """An HTML component can be rendered to HTML."""

    @abstractmethod
    def render(self) -> str: ...
