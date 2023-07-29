from dataclasses import dataclass
from humitifier.facts.blocks import Blocks
from humitifier.html import KvRow, HtmlString, ProgressBar

_HtmlComponent = KvRow | HtmlString | ProgressBar

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
    
    @staticmethod
    def _get_blocks(host_state) -> Blocks:
        stdout = host_state[Blocks.alias]
        return Blocks.from_stdout(stdout)
    
    @classmethod
    def from_host_state(cls, host_state) -> "LocalStorage":
        block = cls._get_blocks(host_state)[0]
        return cls(
            name=block.name,
            size_mb=block.size_mb,
            used_mb=block.used_mb,
        )
    
    def component(self, html_cls: type[_HtmlComponent]) -> _HtmlComponent:
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