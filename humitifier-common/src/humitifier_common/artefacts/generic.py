"""
A collection of facts that are generic and can be collected on any system.
"""

from dataclasses import dataclass

from humitifier_common.artefacts.registry import fact, metric

##
## Hardware
##


@dataclass
class BlockDevice:
    name: str
    type: str
    size: str
    model: str


@fact(group="generic")
@dataclass
class Hardware:
    num_cpus: int
    memory: int
    block_devices: list[BlockDevice]
    pci_devices: list[str]
    usb_devices: list[str]


##
## Storage
##


@dataclass
class Block:
    name: str
    size_mb: int
    used_mb: int
    available_mb: int
    use_percent: int
    mount: str


@metric(group="generic")
class Blocks(list[Block]):
    pass


##
## Users and groups
##


@dataclass
class Group:
    name: str
    gid: int
    users: list[str]


@fact(group="generic")
class Groups(list[Group]):
    pass


@dataclass
class User:
    name: str
    uid: int
    gid: int
    info: str | None
    home: str
    shell: str


@fact(group="generic")
class Users(list[User]):
    pass


##
## Hostname
##


@fact(group="generic")
@dataclass
class HostnameCtl:
    hostname: str
    os: str
    cpe_os_name: str | None
    kernel: str
    virtualization: str | None


##
## Memory
##


@metric(group="generic")
@dataclass
class Memory:
    total_mb: int
    used_mb: int
    free_mb: int
    swap_total_mb: int
    swap_used_mb: int
    swap_free_mb: int


##
## Packages
##


@dataclass
class Package:
    name: str
    version: str


@fact(group="generic")
class PackageList(list[Package]):
    pass
