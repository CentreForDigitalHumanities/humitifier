from humitifier_common.scan_data import ScanErrorMetadata
from .backend import CollectInfo, ShellCollector, T
from humitifier_scanner.executor.linux_shell import LinuxShellExecutor, ShellOutput
from humitifier_common.artefacts import (
    Block,
    Blocks,
    Group,
    Groups,
    HostnameCtl,
    Memory,
    Package,
    PackageList,
    User,
    Users,
)
from ..constants import DEB_OS_LIST, RPM_OS_LIST
from ..utils import os_in_list


class BlocksMetricCollector(ShellCollector):
    metric = Blocks

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Blocks:
        blocks = []

        result = shell_executor.execute("df -BM | egrep '^/'")

        for output_line in result.stdout:
            try:
                name, size, used, available, use_percent, mount = (
                    output_line.strip().split()
                )

                blocks.append(
                    Block(
                        name=name.strip(),
                        # Remove the 'M' from the size, used, and available values
                        size_mb=int(size.rstrip("M")),
                        used_mb=int(used.rstrip("M")),
                        available_mb=int(available.rstrip("M")),
                        use_percent=int(use_percent.rstrip("%")),
                        mount=mount.strip(),
                    )
                )
            except ValueError:
                self.add_error("Failed to parse block output", fatal=True)

        return Blocks(blocks)


class GroupsFactCollector(ShellCollector):
    fact = Groups

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Groups:
        groups = []

        result = shell_executor.execute("cat /etc/group")

        for output_line in result.stdout:
            try:
                name, _, gid, users = output_line.strip().split(":")
                users = [] if users == "" else users.split(",")

                groups.append(Group(name=name, gid=int(gid), users=users))
            except ValueError:
                self.add_error("Failed to parse group output")

        return Groups(groups)


class UsersFactCollector(ShellCollector):
    fact = Users

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Users:
        users = []

        result = shell_executor.execute("cat /etc/passwd")

        for output_line in result.stdout:
            try:
                name, _, uid, gid, info, home, shell = output_line.strip().split(":")
                users.append(
                    User(
                        name=name,
                        uid=int(uid),
                        gid=int(gid),
                        info=info if info != "" else None,
                        home=home,
                        shell=shell,
                    )
                )
            except ValueError:
                self.add_error("Failed to parse user output")

        return Users(users)


class MemoryMetricCollector(ShellCollector):
    metric = Memory

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Memory:
        result = shell_executor.execute("free -m")

        output = Memory(
            total_mb=0,
            used_mb=0,
            free_mb=0,
            swap_total_mb=0,
            swap_used_mb=0,
            swap_free_mb=0,
        )

        for output_line in result.stdout:
            if output_line.startswith("Mem:") or output_line.startswith("Swap:"):
                values = self._split_line(output_line)

                total, used, free, *_ = values

                if output_line.startswith("Mem:"):
                    output.total_mb, output.used_mb, output.free_mb = total, used, free
                else:
                    output.swap_total_mb, output.swap_used_mb, output.swap_free_mb = (
                        total,
                        used,
                        free,
                    )

        return output

    def _split_line(self, line: str) -> tuple[int, int, int, int, int, int]:
        total, used, free, shared, buff_cache, available = 0, 0, 0, 0, 0, 0
        try:
            values = line.strip().split()
            del values[0]  # Remove the first value, which is the label

            # memory is split into 6 values, swap is split into 3
            if len(values) == 6:
                total, used, free, shared, buff_cache, available = [
                    int(value) for value in values
                ]
            elif len(values) == 3:
                total, used, free = [int(value) for value in values]
        except ValueError as e:
            self.add_error(
                "Failed to parse memory output: " + str(e),
                metadata=ScanErrorMetadata(
                    py_exception=e.__class__.__name__,
                ),
                fatal=True,
            )

        return total, used, free, shared, buff_cache, available


class HostnameCtlFactCollector(ShellCollector):
    fact = HostnameCtl

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> HostnameCtl:

        result = shell_executor.execute("hostnamectl")

        base_args = {
            "virtualization": None,
            "cpe_os_name": None,
        }
        parsed_props = [self._parse_line(line) for line in result.stdout]
        parsed_args = {k: v for k, v in parsed_props if k is not None}

        return HostnameCtl(**{**base_args, **parsed_args})

    @staticmethod
    def _parse_line(line: str) -> tuple[None, None] | tuple[str, str]:
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


class PackageListFactCollector(ShellCollector):
    fact = PackageList
    required_facts = [HostnameCtl]

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> PackageList:
        hostname_ctl: HostnameCtl = info.required_facts.get(HostnameCtl)

        os = hostname_ctl.os

        if os_in_list(os, DEB_OS_LIST):
            result = shell_executor.execute(
                "dpkg-query -W -f='${Package}\t${Version}\n'"
            )
            return self._parse_result(result)

        if os_in_list(os, RPM_OS_LIST):
            result = shell_executor.execute(
                "rpm -qa --queryformat '%{NAME}\t%{VERSION}\n'"
            )
            return self._parse_result(result)

        self.add_error("Unknown OS")
        return PackageList([])

    @staticmethod
    def _parse_result(result: ShellOutput):
        packages = []

        for output_line in result.stdout:
            name, _, version = output_line.strip().partition("\t")
            packages.append(Package(name=name, version=version))

        return PackageList(packages)
