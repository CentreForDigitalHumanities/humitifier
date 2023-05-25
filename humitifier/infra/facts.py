from dataclasses import dataclass
from datetime import timedelta


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


Fact = HostnameCtl | Package | Memory | Block | Uptime | Group | User
