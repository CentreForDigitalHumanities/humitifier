from dataclasses import dataclass
from datetime import timedelta
from enum import Enum, auto
from pssh.clients import ParallelSSHClient
from pssh.output import HostOutput
from humitifier.models.host import Host


@dataclass
class HostnameCtl:
    hostname: str
    os: str
    cpe_os_name: str | None
    kernel: str
    virtualization: str | None

    @classmethod
    def from_stdout(cls, output: list[str]) -> "HostnameCtl":
        """Parse output of `hostnamectl`

        Example output:
        ```
        Static hostname: myhost
        Operating System: Ubuntu 20.04.1 LTS
        CPE OS Name: cpe:/o:canonical:ubuntu_linux:20.04
        Kernel: Linux 5.4.0-90-generic
        Virtualization: kvm
        ```
        """
        create_args = {
            "virtualization": None,
            "cpe_os_name": None,
        }
        for line in output:
            match line.strip().partition(":"):
                case "Static hostname", _, value:
                    create_args["hostname"] = value.strip()
                case "Operating System", _, value:
                    create_args["os"] = value.strip()
                case "CPE OS Name", _, value:
                    create_args["cpe_os_name"] = value.strip()
                case "Kernel", _, value:
                    create_args["kernel"] = value.strip()
                case "Virtualization", _, value:
                    create_args["virtualization"] = value.strip()
        return cls(**create_args)
    


@dataclass
class Package:
    name: str
    version: str

    @classmethod
    def from_stdout(cls, output: list[str]) -> list["Package"]:
        """Parse output of `dpkg` or `rpm` formatted to {name}\t{version}

        Example output:
        ```
        package1\t1.0.0
        package2\t2.0.0
        """
        items = (line.strip().partition("\t") for line in output)
        return [cls(name=n, version=v) for n, _, v in items]

    def __str__(self) -> str:
        return f"{self.name}=={self.version}"


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
        """Parse output of `free -m`

        Example output:
        ```
        total used free shared buff/cache available
        Mem: 16000 1000 1000 1000 14000 15000
        Swap: 1000 100 900
        ```
        """

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
    


@dataclass
class Block:
    name: str
    size_mb: int
    used_mb: int
    available_mb: int
    use_percent: int
    mount: str

    @classmethod
    def from_stdout(cls, output: list[str]) -> list["Block"]:
        """Parse output of `df -m`

        Example output:
        ```
        Filesystem     1M-blocks  Used Available Use% Mounted on
        /dev/sda1        16000  1000     14000  10% /
        ```
        """
        items = [line.strip().split() for line in output][1:]
        return [
            cls(
                name=name.strip(),
                size_mb=int(size),
                used_mb=int(used),
                available_mb=int(available),
                use_percent=int(use_percent.rstrip("%")),
                mount=mount.strip(),
            )
            for name, size, used, available, use_percent, mount in items
        ]
    


class Uptime(timedelta):
    @classmethod
    def from_stdout(cls, output: list[str]) -> "Uptime":
        """Parse output of `uptime -p`

        Example output:
        ```
        up 5 days, 22 hours, 52 minutes
        ```
        """
        line = output[0].replace("up ", "")
        args = {}
        for part in line.split(", "):
            value, _, name = part.strip().partition(" ")
            args[name] = int(value)
        fixed = {k + "s" if not k.endswith("s") else k: v for k, v in args.items()}
        if "years" in fixed:
            fixed["days"] = fixed.get("days", 0) + fixed.pop("years") * 365
        return cls(**fixed)



@dataclass
class Group:
    name: str
    gid: int
    users: list[str]

    @classmethod
    def from_stdout(cls, output: list[str]) -> list["Group"]:
        """Parse output of `cat /etc/group`

        Example output:
        ```
        root:x:0:mary
        daemon:x:1:joseph,john
        bin:x:2:
        sys:x:3:
        ```
        """

        def _parse_line(line: str) -> Group:
            name, _, gid, users = line.strip().split(":")
            users = [] if users == "" else users.split(",")
            return cls(name=name, gid=int(gid), users=users)

        return [_parse_line(groupline) for groupline in output]


@dataclass
class User:
    name: str
    uid: int
    gid: int
    info: str | None
    home: str
    shell: str

    @classmethod
    def from_stdout(cls, output: list[str]) -> list["User"]:
        """Parse output of `cat /etc/passwd`

        Example output:
        ```
        root:x:0:0:root:/root:/bin/bash
        systemd-network:x:100:102:systemd Network Management,,,:/run/systemd:/usr/sbin/nologin
        systemd-resolve:x:101:103:systemd Resolver,,,:/run/systemd:/usr/sbin/nologin
        ```
        """

        def _parse_line(line: str) -> User:
            name, _, uid, gid, info, home, shell = line.strip().split(":")
            info = None if info == "" else info
            return cls(name=name, uid=int(uid), gid=int(gid), info=info, home=home, shell=shell)

        return [_parse_line(userline) for userline in output]
    
    
FactData = HostnameCtl | Memory | Block | Uptime | Group | User

class Fact(Enum):
    HostnameCtl = auto()
    Package = auto()
    Memory = auto()
    Block = auto()
    Uptime = auto()
    Group = auto()
    User = auto()


    @property
    def _fact_data(self) -> FactData:
        match self:
            case Fact.HostnameCtl: return HostnameCtl
            case Fact.Package: return Package
            case Fact.Memory: return Memory
            case Fact.Block: return Block
            case Fact.Uptime: return Uptime
            case Fact.Group: return Group
            case Fact.User: return User

            
    def _wrap_descriptor(self, cmd: str) -> str:
        return f"echo '{self.name}' && {cmd}"
    
    def _parse_stdout(self, output: list[str]) -> FactData:
        return self._fact_data.from_stdout(output)
    
    @classmethod
    def parse_hostoutput(cls, host_output: HostOutput) -> tuple[str, FactData]:
        key, *stdout = list(host_output.stdout)
        return (host_output.host, cls[key]._parse_stdout(stdout))


    def _host_cmd(self, host: Host | None) -> str:
        match self:
            case Fact.HostnameCtl: return "hostnamectl"
            case Fact.Package:
                return (
                    "command -v dpkg-query >/dev/null 2>&1 && "
                    "dpkg-query -W -f='${Package}\t${Version}\n' || "
                    "rpm -qa --queryformat '%{NAME}\t%{VERSION}\n'"
                )
            case Fact.Memory: return "free -m"
            case Fact.Block: return "df -m"
            case Fact.Uptime: return "uptime -p"
            case Fact.Group: return "cat /etc/group"
            case Fact.User: return "cat /etc/passwd"

    def cmd(self, host: Host | None) -> str:    
        return self._wrap_descriptor(self._host_cmd(host))
    

    @staticmethod
    def collect_fact_data(client: ParallelSSHClient, facts: list["Fact"]) -> list[tuple[str, FactData]]:
        host_outputs = []
        for fact in facts:
            commands = [fact.cmd(None) for _ in range(len(client.hosts))]
            host_outputs += client.run_command("%s", host_args=commands)
        client.join()
        return [Fact.parse_hostoutput(host_output) for host_output in host_outputs]