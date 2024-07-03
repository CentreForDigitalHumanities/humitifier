import json
from dataclasses import asdict, dataclass
from datetime import timedelta

from humitifier.utils import ssh_command


@dataclass
class Block:
    name: str
    size_mb: int
    used_mb: int
    available_mb: int
    use_percent: int
    mount: str

    @classmethod
    def from_line(cls, output_line: str) -> list["Block"]:
        name, size, used, available, use_percent, mount = output_line.strip().split()
        return cls(
            name=name.strip(),
            size_mb=int(size),
            used_mb=int(used),
            available_mb=int(available),
            use_percent=int(use_percent.rstrip("%")),
            mount=mount.strip(),
        )


@ssh_command("df | egrep '^/'")
class Blocks(list[Block]):

    @classmethod
    def from_stdout(cls, output: list[str]) -> "Blocks":
        blocks = [Block.from_line(line) for line in output]
        return cls(blocks)

    @classmethod
    def from_sql(cls, sql_data) -> "Blocks":
        return cls([Block(**block) for block in sql_data])

    def to_sql(self):
        return [asdict(block) for block in self]


@dataclass
class Group:
    name: str
    gid: int
    users: list[str]

    @classmethod
    def from_line(cls, output_line: list[str]) -> list["Group"]:
        name, _, gid, users = output_line.strip().split(":")
        users = [] if users == "" else users.split(",")
        return cls(name=name, gid=int(gid), users=users)

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def tooltip(self) -> str:
        return f"gid: {self.gid}, users: {self.users}"


@ssh_command("cat /etc/group")
class Groups(list[Group]):

    @classmethod
    def from_stdout(cls, output: list[str]) -> "Groups":
        return cls([Group.from_line(line) for line in output])

    @classmethod
    def from_sql(cls, sql_data) -> "Groups":
        return cls([Group(**group) for group in sql_data])

    def to_sql(self):
        return [asdict(group) for group in self]


@ssh_command("cat /hum/doc/server_facts.json")
@dataclass
class HostMeta:
    department: str | None
    contact: str | None
    update_policy: dict[str, bool] | None
    webdav: str | None
    vhosts: list[dict] | None
    fileservers: list[str] | None
    databases: dict[dict[str, list[str]]] | None

    @classmethod
    def from_stdout(cls, output: list[str]) -> "HostMeta":
        base_args = {
            "department": None,
            "contact": None,
            "update_policy": None,
            "webdav": None,
            "vhosts": None,
            "fileservers": None,
            "databases": None,
        }
        if output[0] == "cat: /hum/doc/server_facts.json: No such file or directory":
            return cls(**base_args)
        json_str = "\n".join(output)
        json_args = json.loads(json_str)
        return cls(**{**base_args, **json_args})

    @classmethod
    def from_sql(cls, sql_data) -> "HostMeta":
        return cls(**sql_data)

    def to_sql(self):
        return asdict(self)


@ssh_command("hostnamectl")
@dataclass
class HostnameCtl:
    hostname: str
    os: str
    cpe_os_name: str | None
    kernel: str
    virtualization: str | None

    @staticmethod
    def _parse_line(line: str) -> tuple[str, str]:
        label, _, value = line.strip().partition(":")
        match label:
            case "Static hostname":
                create_arg = "hostname"
            case "Operating System":
                create_arg = "os"
            case "CPE OS Name":
                create_arg = "cpe_os_name"
            case "Kernel":
                create_arg = "kernel"
            case "Virtualization":
                create_arg = "virtualization"
            case _:
                return None, None
        return create_arg, value.strip()

    @classmethod
    def from_stdout(cls, output: list[str]) -> "HostnameCtl":
        base_args = {
            "virtualization": None,
            "cpe_os_name": None,
        }
        parsed_props = [cls._parse_line(line) for line in output]
        parsed_args = {k: v for k, v in parsed_props if k is not None}
        return cls(**{**base_args, **parsed_args})

    @classmethod
    def from_sql(cls, sql_data) -> "HostnameCtl":
        return cls(**sql_data)

    def to_sql(self):
        return asdict(self)


@ssh_command("free -m")
@dataclass
class Memory:
    total_mb: int
    used_mb: int
    free_mb: int
    swap_total_mb: int
    swap_used_mb: int
    swap_free_mb: int

    @classmethod
    def from_stdout(cls, output: list[str]) -> "Memory":
        for line in output:
            match line.strip().partition(":"):
                case "Mem", _, value:
                    mem = [int(v) for v in value.split()]
                case "Swap", _, value:
                    swap = [int(v) for v in value.split()]
        return cls(
            total_mb=mem[0],
            used_mb=mem[1],
            free_mb=mem[2],
            swap_total_mb=swap[0],
            swap_used_mb=swap[1],
            swap_free_mb=swap[2],
        )

    @property
    def total_percent_use(self):
        return int(self.used_mb / self.total_mb * 100)

    @classmethod
    def from_sql(cls, sql_data) -> "Memory":
        return cls(**sql_data)

    def to_sql(self):
        return asdict(self)


@dataclass
class Package:
    name: str
    version: str

    @classmethod
    def from_line(cls, output_line: str) -> "Package":
        name, _, version = output_line.strip().partition("\t")
        return cls(name=name, version=version)

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def tooltip(self) -> str:
        return f"version: {self.version}"


@ssh_command(
    "command -v dpkg-query >/dev/null 2>&1 && "
    "dpkg-query -W -f='${Package}\t${Version}\n' || "
    "rpm -qa --queryformat '%{NAME}\t%{VERSION}\n'"
)
class PackageList(list[Package]):

    @classmethod
    def from_stdout(cls, output: list[str]) -> "PackageList":
        return cls([Package.from_line(line) for line in output])

    @classmethod
    def from_sql(cls, sql_data) -> "PackageList":
        return cls([Package(**pkg) for pkg in sql_data])

    def to_sql(self):
        return [asdict(pkg) for pkg in self]


@ssh_command("uptime -p")
class Uptime(timedelta):

    @classmethod
    def from_stdout(cls, output: list[str]) -> "Uptime":
        line = output[0].replace("up ", "")
        args = {}
        for part in line.split(", "):
            value, _, name = part.strip().partition(" ")
            args[name] = int(value)
        fixed = {k + "s" if not k.endswith("s") else k: v for k, v in args.items()}
        if "years" in fixed:
            fixed["days"] = fixed.get("days", 0) + fixed.pop("years") * 365
        return cls(**fixed)

    @classmethod
    def from_sql(cls, sql_data) -> "Uptime":
        return cls(seconds=int(sql_data))

    def to_sql(self):
        return self.total_seconds()


@dataclass
class User:
    name: str
    uid: int
    gid: int
    info: str | None
    home: str
    shell: str

    @classmethod
    def from_line(cls, output_line: str) -> list["User"]:
        name, _, uid, gid, info, home, shell = output_line.strip().split(":")
        info = None if info == "" else info
        return cls(name=name, uid=int(uid), gid=int(gid), info=info, home=home, shell=shell)

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def tooltip(self) -> str:
        return f"uid: {self.uid}, gid: {self.gid}, info: {self.info}, home: {self.home}, shell: {self.shell}"


@ssh_command("cat /etc/passwd")
class Users(list[User]):

    @classmethod
    def from_stdout(cls, output: list[str]) -> "Users":
        return cls([User.from_line(line) for line in output])

    @classmethod
    def from_sql(cls, sql_data) -> "Users":
        return cls([User(**user) for user in sql_data])

    def to_sql(self):
        return [asdict(user) for user in self]


@ssh_command("test -f /opt/puppetlabs/puppet/cache/state/agent_disabled.lock && echo true || echo false")
@dataclass
class PuppetAgentStatus:
    disabled: bool

    @classmethod
    def from_stdout(cls, output: list[str]) -> "PuppetAgentStatus":
        return cls(disabled=output[0].strip() == "true")

    @classmethod
    def from_sql(cls, sql_data) -> "PuppetAgentStatus":
        return cls(**sql_data)

    def to_sql(self):
        return asdict(self)


@ssh_command("for path in $(jq -r '.vhosts[] | to_entries[] | .value.docroot' /hum/doc/server_facts.json); do find $path -maxdepth 1 -name wp-config.php -print -quit;done")
@dataclass
class IsWordpress:
    is_wp: bool

    @classmethod
    def from_stdout(cls, output: list[str]) -> "IsWordpress":
        return cls(is_wp=output and output[0].strip() != "")

    @classmethod
    def from_sql(cls, sql_data) -> "IsWordpress":
        return cls(**sql_data)

    def to_sql(self):
        return asdict(self)


SshFact = (
    Blocks | Groups | HostMeta | HostnameCtl | Memory | PackageList | Uptime | Users | PuppetAgentStatus | IsWordpress
)
SSH_FACTS = [Blocks, Groups, HostMeta, HostnameCtl, Memory, PackageList, Uptime, Users, PuppetAgentStatus, IsWordpress]
