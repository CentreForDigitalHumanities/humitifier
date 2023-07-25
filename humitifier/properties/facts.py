from dataclasses import dataclass
from datetime import timedelta

from humitifier.protocols import IProperty
from humitifier.facts import (
    Block,
    Blocks,
    HostnameCtl, 
    Memory as MemoryFact,
    Package,
    Packages as PackagesFact, 
)
from humitifier.views.atoms import InlineList, ProgressBar
from humitifier.models.host_state import HostState


@dataclass
class Hostname(IProperty):
    value: str
    kv_label: str = "Hostname"

    @classmethod
    def slug(cls) -> str:
        return "hostname"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Hostname":
        return cls(value=host_state.facts[HostnameCtl.alias].hostname)

    def render_kv_value(self) -> str:
        return self.value
    

@dataclass
class Os(IProperty):
    value: str
    kv_label: str = "Operating System"

    @classmethod
    def slug(cls) -> str:
        return "os"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Os":
        return cls(value=host_state.facts[HostnameCtl.alias].os)

    def render_kv_value(self) -> str:
        return self.value
    

@dataclass
class PackageList(IProperty):
    value: list[Package]
    kv_label: str = "Packages"

    @classmethod
    def slug(cls) -> str:
        return "packages"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "PackageList":
        return cls(value=host_state.facts[PackagesFact.alias].items)

    def render_kv_value(self) -> str:
        atom = InlineList(items=[str(p) for p in self.value])
        return atom.render()
    

@dataclass
class Memory(IProperty):
    value: MemoryFact
    kv_label: str = "Memory"

    @classmethod
    def slug(cls) -> str:
        return "memory"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Memory":
        return cls(value=host_state.facts[MemoryFact.alias])

    def render_kv_value(self) -> str:
        description = f"{self.value.used_mb} MB / {self.value.total_mb} MB"
        atom = ProgressBar(description=description, value=int(self.value.used_mb / self.value.total_mb * 100))
        return atom.render()
    

@dataclass
class LocalStorage(IProperty):
    value: Block
    kv_label: str = "Local Storage"

    @classmethod
    def slug(cls) -> str:
        return "local_storage"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "LocalStorage":
        return cls(value=host_state.facts[Blocks.alias].items[0])

    def render_kv_value(self) -> str:
        description = f"{self.value.used_mb} MB / {self.value.size_mb} MB"
        atom = ProgressBar(description=description, value=int(self.value.used_mb / self.value.size_mb * 100))
        return atom.render()
    

@dataclass
class Virtualization(IProperty):
    value: str
    kv_label: str = "Is Virtual"

    @classmethod
    def slug(cls) -> str:
        return "virtualization"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Virtualization":
        return cls(value=host_state.facts[HostnameCtl.alias].virtualization)

    def render_kv_value(self) -> str:
        return str(self.value == "vmware")
    

@dataclass
class Uptime(IProperty):
    value: timedelta
    kv_label: str = "Uptime"

    @classmethod
    def slug(cls) -> str:
        return "uptime"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Uptime":
        return cls(value=host_state.facts["uptime"])

    def render_kv_value(self) -> str:
        return f"{self.value.days} days"