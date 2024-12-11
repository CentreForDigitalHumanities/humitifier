from dataclasses import dataclass

from humitifier_common.facts.registry import metric

##
## ZFS list
##


@dataclass
class ZFSVolume:
    name: str
    size_mb: int
    used_mb: int
    mount: str


@dataclass
class ZFSPool:
    name: str
    size_mb: int
    used_mb: int


@metric(namespace="special")
@dataclass
class ZFS:
    pools: list[ZFSPool]
    volumes: list[ZFSVolume]
