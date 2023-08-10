from dataclasses import dataclass

from humitifier.props.protocols import Property


@dataclass(frozen=True)
class HostViewConfig:
    card: list[type[Property]]
    table: list[type[Property]]