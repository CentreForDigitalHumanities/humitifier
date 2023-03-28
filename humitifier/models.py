from datetime import date, timedelta
from typing import Literal, Optional

from dataclasses import dataclass


@dataclass
class Person:
    """
    A person associated to a server
    """

    name: str  # The name of the person. Example: "Bartolomew Bagshot"
    email: str  # The email address of the person. Example: "bbagshot@hogwarts.co.uk"
    role: Optional[Literal["admin", "user", "developer", "researcher"]]  # The role of the person. Example: "admin"
    department: Optional[str]  # The department of the person. Example: "Department of Magical Creatures"
    notes: Optional[str]  # Optional notes about the person. Example: "Contact for server maintenance"


@dataclass
class ServiceContract:
    """
    A service contract associated to a server
    """

    entity: str  # The entity that the contract is with. Example: "Hogwarts School of Witchcraft and Wizardry"
    owner: Person  # The owner of the contract. Example: Person(name="Bartolomew Bagshot", email="b.bagshot@hogwarts.co.uk")
    creation_date: date  # The date on which the contract was created. Example: date(2022, 12, 31)
    expiry_date: date  # The expiry date of the contract. Example: date(2022, 12, 31)
    purpose: str  # The purpose of the contract. Example: "webapp"
    people: list[Person]  # A list of people associated to the server. Example: [Person(...), Person(...)]


@dataclass
class Package:
    name: str  # The name of the package. Example: "nginx"
    version: str  # The version of the package. Example: "1.21.1-1ubuntu1"

    def __str__(self) -> str:
        return f"{self.name} {self.version}"


@dataclass
class Server:
    """
    An arbitrary server
    """

    name: str  # The name of the server. Example: "web-server-01"
    ip_address: str  # The IP address of the server. Example: "192.168.1.100"
    cpu_total: int  # The total number of CPUs of the server. Example: 8
    cpu_usage: float  # The current CPU usage percentage of the server. Example: 75.0
    memory_total: int  # The total amount of memory in GB of the server. Example: 16
    memory_usage: int  # The current memory usage in GB of the server. Example: 8
    local_storage_total: int  # The total storage capacity of the server in GB. Example: 1000
    local_storage_usage: int  # The current storage usage in GB of the server. Example: 500
    is_virtual: bool  # Whether the server is virtual or physical. Example: True
    os: str  # The operating system of the server. Example: "Ubuntu 20.04 LTS"
    uptime: timedelta  # The uptime of the server. Example: timedelta(days=30, hours=12)
    nfs_shares: list[str]  # A list of NFS shares on the server. Example: ["/mnt/nfs", "/mnt/nfs2"]
    webdav_shares: list[str]  # A list of WebDAV shares on the server. Example: ["/webdav", "/webdav2"]
    packages: list[Package]  # A list of packages installed on the server. Example: [Package(...)]
    service_contract: ServiceContract  # The service contract associated to the server. Example: ServiceContract(...)
    reboot_required: bool  # Whether a reboot is required for the updates to take effect.
    users: list[str]  # A list of users on the server. Example: ["john", "jane"]
    groups: list[str]  # A list of groups on the server. Example: ["developers", "admins"]

    @property
    def uptime_days(self) -> int:
        return self.uptime.days
