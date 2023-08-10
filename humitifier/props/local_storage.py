from dataclasses import dataclass
from humitifier.facts.blocks import Blocks, Block
from humitifier.html import KvRow, HtmlString, ProgressBar

from typing import TypeVar

_Component = TypeVar("_Component", HtmlString, KvRow, ProgressBar)


@dataclass
class LocalStorage:
    name: str
    size_mb: int
    used_mb: int

    @classmethod
    @property
    def alias(cls) -> str:
        return "local_storage"

    @property
    def percentage(self) -> int:
        return int(self.used_mb / self.size_mb * 100)
    
    @property
    def label(self) -> str:
        return f"{self.used_mb} MB / {self.size_mb} MB"
    
    @classmethod
    def from_host_state(cls, host_state) -> "LocalStorage":
        block: Block = host_state[Blocks][0]
        return cls(
            name=block.name,
            size_mb=block.size_mb,
            used_mb=block.used_mb,
        )
    
    def component(self, html_cls: type[_Component]) -> _Component:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(f"Disk: {self.label}")
            case ProgressBar.__name__:
                return ProgressBar(
                    percentage=self.percentage,
                    label=self.label,
                )
            case KvRow.__name__:
                return KvRow(
                    label="Local Storage",
                    value=self.component(ProgressBar)
                )