from abc import abstractmethod
from typing import runtime_checkable, Protocol
from humitifier.html.protocols import HtmlComponent



@runtime_checkable
class PropertyFilter(Protocol):
    
    @abstractmethod
    def component(self, html_cls: type[HtmlComponent]) -> HtmlComponent: ...

    @abstractmethod
    def options(self) -> set[str]: ...