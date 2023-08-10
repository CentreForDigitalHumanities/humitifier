from abc import abstractmethod
from typing import runtime_checkable, Protocol


@runtime_checkable
class HtmlComponent(Protocol):
    """A HtmlComponent can be rendered into a string to be served as html"""

    @abstractmethod
    def render(self) -> str: ...

@runtime_checkable
class Renderable(Protocol):
    """A Renderable can translate its data into a html component that can be displayed"""

    @abstractmethod
    def component(self, html_cls: type[HtmlComponent]) -> HtmlComponent: ...


@runtime_checkable
class PsshOp(Protocol):
    """A PsshOp can both produce a command to run over ssh and parse its output"""

    @classmethod
    @abstractmethod
    def from_stdout(cls, stdout: list[str]): ...

    @abstractmethod
    def ssh_command(self, host_config) -> str: ...


@runtime_checkable
class WithAlias(Protocol):
    """A WithAlias has a unique alias describing the data or property it represents"""

    @classmethod
    @property
    @abstractmethod
    def alias(self) -> str: ...


@runtime_checkable
class Filterable(Protocol):
    """A Filterable can be filtered by a query string"""

    @abstractmethod
    def filter(self, query: str) -> bool: ...


@runtime_checkable
class WithQueryOptions(Protocol):
    """A QuerySuggestions can provide a set of suggestions for a query string"""

    @staticmethod
    @abstractmethod
    def query_option_set(items=list["WithQueryOptions"]) -> set[str]: ...


@runtime_checkable
class FromState(Protocol):
    """A FromState can be constructed from a HostState"""

    @classmethod
    @abstractmethod
    def from_host_state(cls, host_state) -> 'FromState': ...


@runtime_checkable
class HostFact(WithAlias, PsshOp, Protocol):
    """A HostFact can create data for a HostState by parsing stdout from a ssh command"""


@runtime_checkable
class StateProperty(WithAlias, FromState, Renderable, Protocol):
    """A StateProperty can be constructed from a HostState and rendered into a HtmlComponent"""


@runtime_checkable
class FilterProperty(StateProperty, Filterable, Protocol):
    """A FilterProperty can be constructed from a HostState, rendered into a HtmlComponent, and filtered by a query string"""