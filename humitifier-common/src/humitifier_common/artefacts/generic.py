"""
A collection of facts that are generic and can be collected on any system.
"""

from datetime import datetime
from typing import Literal, Annotated, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    total_memory_gb: int = 0


##
## Hardware (lshw)
##


class LshwNode(BaseModel):
    """A single node of the hardware tree as reported by `lshw`.

    The tree structure is kept intact: every node holds its own children, so
    it stays clear what a device is attached to.
    """

    id: str
    node_class: str
    handle: str | None = None
    description: str | None = None
    product: str | None = None
    vendor: str | None = None
    serial: str | None = None
    version: str | None = None
    physid: str | None = None
    businfo: str | None = None
    logical_names: list[str] = []
    dev: str | None = None
    slot: str | None = None
    units: str | None = None
    size: int | None = None
    capacity: int | None = None
    clock: int | None = None
    width: int | None = None
    claimed: bool = False
    disabled: bool = False
    configuration: dict[str, str] = {}
    capabilities: dict[str, str] = {}
    children: list["LshwNode"] = []

    def walk(self, parent_path: str = "", depth: int = 0):
        """Yield (node, path, depth) for this node and all its descendants.

        The path is the slash-separated list of ids of all ancestors plus the
        node itself, making it unique within a single tree.
        """
        path = f"{parent_path}/{self.id}" if parent_path else self.id

        yield self, path, depth

        for child in self.children:
            yield from child.walk(path, depth + 1)


@fact(group=GENERIC, metadata=ArtefactMetadata(null_is_valid=True))
class Lshw(BaseModel):
    product: str | None = None
    vendor: str | None = None
    serial: str | None = None
    nodes: list[LshwNode] = []

    def walk(self):
        """Yield (node, path, depth) for every node in the hardware tree."""
        for node in self.nodes:
            yield from node.walk()


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


# Deprecated, replaced by PackageManagerInfo
@fact(group=GENERIC, max_version=2)
class PackageList(list[Package]):
    pass


###
### V6 package manager info
###


class BaseRepository(BaseModel):
    source_file: str
    options: dict[str, str] | None = None


class AptRepository(BaseRepository):
    kind: Literal["apt"] = "apt"
    dist: str
    uri: str
    components: list[str]


class RpmRepository(BaseRepository):
    kind: Literal["rpm"] = "rpm"

    id: str
    name: str

    enabled: bool

    base_url: str | None = None
    mirrorlist: str | None = None
    metalink: str | None = None

    gpg_check: bool = False
    gpg_key: str | None = None


class InstalledPackage(BaseModel):
    name: str
    current_version: str
    upgrade_available: bool
    new_version: str | None = None
    sources: list[str] | None = None
    arch: str | None = None


Repository = Annotated[
    Union[AptRepository, RpmRepository],
    Field(discriminator="kind"),
]


@fact(group=GENERIC, min_version=3)
class PackageManagerInfo(BaseModel):
    installed_packages: list[InstalledPackage] = Field(default_factory=list)
    repositories: list[Repository] = Field(default_factory=list)
    last_transaction_dt: datetime | None = None
    last_transaction_changed: int | None = None


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


##
## SELinux info
##


@fact(group=GENERIC, metadata=ArtefactMetadata(null_is_valid=True))
class SELinux(BaseModel):
    enabled: bool
    policy_name: str | None
    mode: str | None


##
## SystemD info
##


class SystemdUnit(BaseModel):
    unit: str
    load: str
    description: str | None
    active: str
    sub: str


@fact(group=GENERIC, metadata=ArtefactMetadata(null_is_valid=True))
class Systemd(BaseModel):
    units: list[SystemdUnit]


##
## iptables
##


class IPTableRules(BaseModel):
    # The scanner serializes this model by field name, so 'in_' needs to be
    # accepted next to the 'in' alias when parsing it again
    model_config = ConfigDict(populate_by_name=True)

    num: int | None = None
    pkts: int
    bytes: int
    target: str | None
    prot: str
    opt: str | None
    in_: str = Field(alias="in")
    out: str
    source: str
    destination: str
    options: str = ""


class IPTablesChain(BaseModel):
    chain: str
    default_policy: str | None = None
    default_packets: int | None = None
    default_bytes: int | None = None
    rules: list[IPTableRules]


class IPTablesPortAccessSource(BaseModel):
    source: str
    resolved_hostname: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_str(cls, data):
        if isinstance(data, str):
            return {"source": data}
        return data


class IPTablesPortAccess(BaseModel):
    """Human-friendly summary of who can reach a given port.

    Derived from the ACCEPT/DROP/REJECT rules in the INPUT chain. Sources are
    the raw source specs of the matching rules (e.g. ``131.211.0.0/16``);
    ``0.0.0.0/0`` means 'anyone'. A rule bound to a specific input interface
    is recorded as ``<source>@<interface>`` (e.g. ``0.0.0.0/0@lo``).
    """

    # None means the rule(s) apply to every port
    port: str | None
    protocol: str
    allowed_from: list[IPTablesPortAccessSource] = Field(default_factory=list)
    denied_from: list[IPTablesPortAccessSource] = Field(default_factory=list)
    # True if there is an ACCEPT rule for this port from any source on any
    # interface
    default_open: bool = False
    default_closed: bool = False


@fact(group=GENERIC, min_version=3)
class IPTables(BaseModel):
    chains: list[IPTablesChain]
    port_access: list[IPTablesPortAccess] = Field(default_factory=list)
