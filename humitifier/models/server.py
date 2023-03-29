from datetime import timedelta
from pydantic import BaseModel
from .package import Package
from .servicecontract import ServiceContract


class Server(BaseModel):
    """
    An arbitrary server
    """

    hostname: str  # The name of the server. Example: "web-server-01"
    slug: str  # The fqdn slug of the server. Example: "web-server-01.af.dd.com"
    ip_address: str  # The IP address of the server. Example: "192.168.1.100"
    cpu_total: int  # The total number of CPUs of the server. Example: 8
    memory_total: float  # The total amount of memory in GB of the server. Example: 16
    memory_usage: float  # The current memory usage in GB of the server. Example: 8
    local_storage_total: float  # The total storage capacity of the server in GB. Example: 1000
    is_virtual: bool  # Whether the server is virtual or physical. Example: True
    os: str  # The operating system of the server. Example: "Ubuntu 20.04 LTS"
    uptime: timedelta  # The uptime of the server. Example: timedelta(days=30, hours=12)
    packages: list[Package]  # A list of packages installed on the server. Example: [Package(...)]
    service_contract: ServiceContract | None  # The service contract associated to the server. Example: ServiceContract(...)
    reboot_required: bool  # Whether a reboot is required for the updates to take effect.
    # TODO: implement readers for the following fields
    # cpu_usage: float  # The current CPU usage percentage of the server. Example: 75.0
    # local_storage_usage: int  # The current storage usage in GB of the server. Example: 500
    # nfs_shares: list[str]  # A list of NFS shares on the server. Example: ["/mnt/nfs", "/mnt/nfs2"]
    # webdav_shares: list[str]  # A list of WebDAV shares on the server. Example: ["/webdav", "/webdav2"]
    # users: list[str]  # A list of users on the server. Example: ["john", "jane"]
    # groups: list[str]  # A list of groups on the server. Example: ["developers", "admins"]

    @property
    def uptime_days(self) -> int:
        return self.uptime.days
