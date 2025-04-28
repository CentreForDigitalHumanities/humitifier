"""
A collection of facts that are generic and can be collected on any system.
"""

from typing import Literal

from pydantic import BaseModel

from humitifier_common.artefacts.groups import GENERIC
from humitifier_common.artefacts.registry import fact, metric
from humitifier_common.artefacts.registry.registry import ArtefactMetadata


##
## Hardware
##


class BlockDevice(BaseModel):
    name: str
    type: str
    size: str
    model: str


class MemoryRange(BaseModel):
    range: str
    size: int
    state: Literal["online", "offline"]
    removable: bool
    block: str


@fact(group=GENERIC)
class Hardware(BaseModel):
    num_cpus: int
    memory: list[MemoryRange]
    block_devices: list[BlockDevice]
    pci_devices: list[str]
    usb_devices: list[str]


##
## Storage
##


class Block(BaseModel):
    name: str
    size_mb: int
    used_mb: int
    available_mb: int
    use_percent: int
    mount: str


@metric(group=GENERIC)
class Blocks(list[Block]):
    pass


##
## Users and groups
##


class Group(BaseModel):
    name: str
    gid: int
    users: list[str]


@fact(group=GENERIC)
class Groups(list[Group]):
    pass


class User(BaseModel):
    name: str
    uid: int
    gid: int
    info: str | None
    home: str
    shell: str


@fact(group=GENERIC)
class Users(list[User]):
    pass


##
## Hostname
##


@fact(group=GENERIC)
class HostnameCtl(BaseModel):
    hostname: str
    os: str
    cpe_os_name: str | None
    kernel: str
    virtualization: str | None


##
## Memory
##


@metric(group=GENERIC)
class Memory(BaseModel):
    total_mb: int
    used_mb: int
    free_mb: int
    swap_total_mb: int
    swap_used_mb: int
    swap_free_mb: int


##
## Packages
##


class Package(BaseModel):
    name: str
    version: str


@fact(group=GENERIC)
class PackageList(list[Package]):
    pass


##
## Network info
##


class AddressInfo(BaseModel):
    family: str
    address: str
    scope: str


class NetworkInterface(BaseModel):
    name: str
    altnames: list[str]
    link_type: str
    mac_address: str
    flags: list[str]
    addresses: list[AddressInfo]


@fact(group=GENERIC, metadata=ArtefactMetadata(null_is_valid=True))
class NetworkInterfaces(list[NetworkInterface]):
    pass
