"""Protocols for implementing custom Atom, Properties, Facts, and Rules.
"""

from humitifier.models.host import Host
from humitifier.models.host_state import HostState

from typing import Protocol, TypeVar

ExtractedProperty = TypeVar("ExtractedProperty")

class IProperty(Protocol):
    """Protocol for a readable property to be extracted from a HostState."""
    slug: str
    

    def extract(self, host_state: HostState) -> ExtractedProperty:
        """Extract the property from the given HostState."""
        ...

    def kv_table_row(self, properties: ExtractedProperty) -> str:
        """Return a string representation of the property for a KV table row."""
        ...


class IFact(Protocol):
    """Protocol for a fact to be extracted from a host over ssh."""
    slug: str

    @classmethod
    def from_stdout(cls, stdout: list[str]) -> "IFact":
        """Create a Fact from the stdout of a command."""
        ...

    def command(self, host: Host | None) -> str:
        """Return the command to be run on the host."""
        ...


class IFilter(Protocol):
    """Protocol for a filter to be applied to a list of HostStates."""
    slug: str


    def apply(self, host_state: HostState, query: str) -> bool:
        """Apply the filter to a HostState."""
        ...

    def options(self, host_states: list[HostState]) -> list[str]:
        """Return a list of options for the filter."""
        ...

