from pydantic import BaseModel

from humitifier_common.artefacts.groups import SPECIAL
from humitifier_common.artefacts.registry import metric

##
## ZFS list
##


class ZFSVolume(BaseModel):
    name: str
    size_mb: int
    used_mb: int
    mount: str


class ZFSPool(BaseModel):
    name: str
    size_mb: int
    used_mb: int


@metric(group=SPECIAL)
class ZFS(BaseModel):
    pools: list[ZFSPool]
    volumes: list[ZFSVolume]
