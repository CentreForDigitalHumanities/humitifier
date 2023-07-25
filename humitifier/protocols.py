"""Protocols for implementing custom Atom, Properties, Facts, and Rules.
"""
from jinja2 import Template

from typing import Literal, Protocol


class IAtom(Protocol):
    template: Template

    def render(self) -> str:
        ...

class IProperty(Protocol):
    """Protocol for a readable property to be extracted from a HostState."""
    kv_label: str
    
    @classmethod
    def slug(cls) -> str:
        """Return the slug of the property."""
        ...

    @classmethod
    def from_host_state(cls, host_state) -> "IProperty":
        """Extract the property from the given HostState."""
        ...

    @property
    def kv_value_html(self) -> str:
        """Return a string representation of the property for a KV table row."""
        ...


class IFact(Protocol):
    """Protocol for a fact to be extracted from a host over ssh."""
    alias: str
    template: Template | str

    @classmethod
    def from_stdout(cls, stdout: list[str]) -> "IFact":
        """Create a Fact from the stdout of a command."""
        ...



class IFilter(Protocol):
    """Protocol for a filter to be applied to a list of HostStates."""
    filter_key: str
    widget: Literal["search", "select"]
    label: str

    @classmethod
    def apply(cls, host_state, query: str) -> bool:
        """Apply the filter to a HostState."""
        ...

    @classmethod
    def options(cls, host_states) -> list[str]:
        """Return a list of options for the filter."""
        ...

