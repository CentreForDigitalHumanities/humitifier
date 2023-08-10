from dataclasses import dataclass
from humitifier.html import HtmlString, KvRow, ProgressBar
from humitifier.facts.memory import Memory


from typing import TypeVar

_Component = TypeVar("_Component", HtmlString, KvRow, ProgressBar)

@dataclass
class MemoryUse:
    used_mb: int
    total_mb: int

    @classmethod
    @property
    def alias(cls) -> str:
        return "memory-use"
    
    @property
    def label(self) -> str:
        return f"{self.used_mb} MB / {self.total_mb} MB"
    
    @property
    def percentage(self) -> int:
        return round(self.used_mb / self.total_mb * 100)
    
    @classmethod
    def from_host_state(cls, host_state) -> "MemoryUse":
        mem: Memory = host_state[Memory]
        return cls(used_mb=mem.used_mb, total_mb=mem.total_mb)
    
    def component(self, htmlcls: type[_Component]) -> _Component:
        match htmlcls.__name__:
            case HtmlString.__name__:
                return HtmlString(f"Memory: {self.label}")
            case KvRow.__name__:
                return KvRow(label="Memory", value=self.component(ProgressBar))
            case ProgressBar.__name__:
                return ProgressBar(label=self.label, percentage=self.percentage)
            case _:
                raise ValueError(f"Unknown html component: {htmlcls.__name__}")