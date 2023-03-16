from sqlite3 import Row
from datetime import datetime, timedelta
from typing import List, Literal

from dataclasses import dataclass


@dataclass
class Server:
    """
    A HUM-IT server
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
    nfs_shares: List[str]  # A list of NFS shares on the server. Example: ["/mnt/nfs", "/mnt/nfs2"]
    webdav_shares: List[str]  # A list of WebDAV shares on the server. Example: ["/webdav", "/webdav2"]
    requesting_department: str  # The department that requested the server. Example: "IT"
    server_type: str  # The type of server. Example: "Web Server"
    contact_persons: List[str]  # Contact persons for the server. Example: ["J.Doe@mail.me", "J.Smit@mail.co"]
    expiry_date: datetime  # The expiry date of the server. Example: datetime(2022, 12, 31)
    update_policy: Literal["automatic", "manual"]  # The server's update policy. Example: "automatic"
    available_updates: List[str]  # The available package updates. Example: ["nginx", "mysql"]
    reboot_required: bool  # Whether a reboot is required for the updates to take effect.
    users: List[str]  # A list of users on the server. Example: ["john", "jane"]
    groups: List[str]  # A list of groups on the server. Example: ["developers", "admins"]
    installed_packages: List[str]  # A list of installed packages on the server. Example: ["nginx", "mysql", "python3"]

    def to_query(self) -> dict:
        res = self.__dict__
        res["uptime"] = res["uptime"].seconds
        for k, v in res.items():
            if isinstance(v, list):
                res[k] = ",".join(v)
        return res

    @classmethod
    def from_sql_row(cls, row: Row) -> "Server":
        data = dict(row)
        data["uptime"] = timedelta(seconds=data["uptime"])
        data["expiry_date"] = datetime.strptime(data["expiry_date"], "%Y-%m-%d %H:%M:%S")
        for k in [
            "nfs_shares",
            "webdav_shares",
            "contact_persons",
            "available_updates",
            "users",
            "groups",
            "installed_packages",
        ]:
            data[k] = data[k].split(",")
        return cls(**data)
