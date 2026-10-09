import configparser
import ipaddress
import json
import re
from datetime import datetime
from pathlib import Path

import jc

from humitifier_common.scan_data import ScanErrorMetadata
from .backend import CollectInfo, ShellCollector, FileCollector, Collector
from humitifier_scanner.executor.linux_shell import LinuxShellExecutor
from humitifier_common.artefacts import (
    AddressInfo,
    Block,
    BlockDevice,
    Blocks,
    Group,
    Groups,
    Hardware,
    HostnameCtl,
    Lshw,
    LshwNode,
    Memory,
    MemoryRange,
    NetworkInterface,
    NetworkInterfaces,
    SELinux,
    Systemd,
    SystemdUnit,
    User,
    Users,
    PackageManagerInfo,
    InstalledPackage,
    AptRepository,
    RpmRepository,
    IPTables,
    IPTablesChain,
    IPTablesPortAccess,
    IPTableRules,
)
from ..constants import DEB_OS_LIST, RPM_OS_LIST, SELINUX_OS_LIST
from ..executor import Executors
from ..executor.linux_files import LinuxFilesExecutor
from ..utils import os_in_list


class HardwareFactCollector(ShellCollector):
    fact = Hardware

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Hardware:

        num_cpus_cmd = shell_executor.execute("nproc")
        try:
            num_cpus = num_cpus_cmd.stdout
            num_cpus = int(num_cpus[0])
        except (ValueError, IndexError):
            num_cpus = -1
            self.add_error("Could not determine number of CPUs", fatal=False)

        # Yes, this is a different command from the memory-usage metric
        # This command reads actual physical memory; some of which is reserved by firmware
        # and thus not visible in the memory metric
        memory_cmd = shell_executor.execute("lsmem --raw --bytes", fail_silent=True)
        try:
            memory = []
            # First line is a header
            for line in memory_cmd.stdout[1:]:
                # If a memrange is offline, it will have the removable column
                # empty; represented by a double-space
                if "  " in line:
                    line = line.replace("  ", " unknown ")
                mem_range, size, state, removable, block = line.split()
                removable = removable == "yes"
                size = int(size)
                memory.append(
                    MemoryRange(
                        range=mem_range,
                        size=size,
                        state=state,
                        removable=removable,
                        block=block,
                    )
                )

        except Exception as e:
            memory = []
            self.add_error(f"Could not determine memory size: {e}", fatal=False)

        total_memory_gb = sum([range.size for range in memory]) / 1024 / 1024 // 1024

        block_devices_cmd = shell_executor.execute("lsblk")
        block_devices = []
        block_devices_data = jc.parse("lsblk", block_devices_cmd.stdout_str)
        try:
            # The first line is a header, hence the [1:] slice
            for block_device in block_devices_data:
                block_devices.append(
                    BlockDevice(
                        name=block_device.get("name", ""),
                        type=block_device.get("type", ""),
                        size=block_device.get("size", ""),
                        model=block_device.get("model", ""),
                    )
                )
        except (ValueError, IndexError):
            self.add_error("Could not determine block devices", fatal=False)

        pci_devices = shell_executor.execute("lspci", fail_silent=True)

        usb_devices = shell_executor.execute("lsusb", fail_silent=True)

        return Hardware(
            num_cpus=num_cpus,
            memory=memory,
            block_devices=block_devices,
            pci_devices=pci_devices.stdout,
            usb_devices=usb_devices.stdout,
            total_memory_gb=total_memory_gb,
        )


class LshwFactCollector(ShellCollector):
    fact = Lshw
    required_facts = [HostnameCtl]

    # Keys that are copied over as-is (as a string) from the lshw output
    STRING_KEYS = (
        "handle",
        "description",
        "product",
        "vendor",
        "serial",
        "version",
        "physid",
        "businfo",
        "dev",
        "slot",
        "units",
    )

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Lshw | None:

        # Debian versions older than 12 have a fundamentally broken Lshw JSON output
        # So we skip it...
        hostname_ctl_data: HostnameCtl = info.required_facts.get(HostnameCtl)  # NoQA
        os = hostname_ctl_data.os
        if "Debian" in os and any(version in os for version in ["10", "11"]):
            return None

        # lshw needs to run as root; without it, it cannot read the DMI tables
        # and most of the interesting information is simply missing
        lshw_cmd = shell_executor.execute("sudo lshw -json", fail_silent=True)

        if lshw_cmd.return_code != 0:
            self.add_error(
                "Could not run 'sudo lshw -json'; is lshw installed?",
                metadata=ScanErrorMetadata(
                    stderr="\n".join(lshw_cmd.stderr),
                    exit_code=lshw_cmd.return_code,
                ),
                fatal=True,
            )

        try:
            data = json.loads("\n".join(lshw_cmd.stdout))
        except json.JSONDecodeError as e:
            self.add_error(f"Could not parse lshw output: {e}", fatal=True)
            return None

        # Some lshw versions wrap the system node(s) in a list
        if isinstance(data, dict):
            data = [data]

        root_nodes = [node for node in data or [] if isinstance(node, dict)]

        if not root_nodes:
            self.add_error("lshw did not report a system node", fatal=True)
            return None

        system_node = root_nodes[0]

        return Lshw(
            product=self._parse_str(system_node.get("product")),
            vendor=self._parse_str(system_node.get("vendor")),
            serial=self._parse_str(system_node.get("serial")),
            nodes=[self._parse_node(node) for node in root_nodes],
        )

    def _parse_node(self, node: dict) -> LshwNode:
        # A node can have either a single logical name or a list of them
        logical_names = node.get("logicalname") or []
        if not isinstance(logical_names, list):
            logical_names = [logical_names]

        strings = {key: self._parse_str(node.get(key)) for key in self.STRING_KEYS}

        # The children are kept nested; that way it stays visible what a
        # device is attached to
        children = [
            self._parse_node(child)
            for child in node.get("children") or []
            if isinstance(child, dict)
        ]

        return LshwNode(
            id=self._parse_str(node.get("id")) or "unknown",
            node_class=self._parse_str(node.get("class")) or "unknown",
            logical_names=[str(name) for name in logical_names],
            children=children,
            size=self._parse_int(node.get("size")),
            capacity=self._parse_int(node.get("capacity")),
            clock=self._parse_int(node.get("clock")),
            width=self._parse_int(node.get("width")),
            claimed=bool(node.get("claimed", False)),
            disabled=bool(node.get("disabled", False)),
            configuration=self._parse_dict(node.get("configuration")),
            capabilities=self._parse_dict(node.get("capabilities")),
            **strings,
        )

    @staticmethod
    def _parse_str(value) -> str | None:
        if value is None:
            return None

        return str(value)

    @staticmethod
    def _parse_int(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_dict(value) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}

        # lshw reports items without a description (mostly capabilities) as
        # `true`, which would end up as a useless 'True' string
        return {key: "" if item is True else str(item) for key, item in value.items()}


class BlocksMetricCollector(ShellCollector):
    metric = Blocks

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Blocks:
        blocks = []

        result = shell_executor.execute("df -BM")
        data = jc.parse("df", result.stdout_str)

        for block in data:
            try:
                name: str = block.get("filesystem", "")

                # Loop devices are always 100%; non-/ block devices aren't actual disks
                if name.startswith("/dev/loop") or not name.startswith("/dev"):
                    continue

                size: int = block.get("size", 0) / 1024 // 1024
                used: int = block.get("used", 0) / 1024 // 1024
                available: int = block.get("available", 0) / 1024 // 1024
                use_percent: int = block.get("use_percent", 0)
                mount: str = block.get("mounted_on", "")

                blocks.append(
                    Block(
                        name=name.strip(),
                        size_mb=size,
                        used_mb=used,
                        available_mb=available,
                        use_percent=use_percent,
                        mount=mount,
                    )
                )
            except ValueError:
                self.add_error("Failed to parse block output", fatal=True)

        return Blocks(blocks)


class GroupsFactCollector(FileCollector):
    fact = Groups

    def collect_from_files(
        self, files_executor: LinuxFilesExecutor, info: CollectInfo
    ) -> Groups:
        groups = []

        with files_executor.open("/etc/group") as file:
            contents = str(file.read(), encoding="utf-8")
            for group in jc.parse("group", contents):
                groups.append(
                    Group(
                        name=group.get("group_name", ""),
                        gid=group.get("gid", -1),
                        users=group.get("members", []),
                    )
                )

        return Groups(groups)


class UsersFactCollector(FileCollector):
    fact = Users

    def collect_from_files(
        self, files_executor: LinuxFilesExecutor, info: CollectInfo
    ) -> Users:
        users = []

        with files_executor.open("/etc/passwd") as file:
            contents = str(file.read(), encoding="utf-8")

            for user in jc.parse("passwd", contents):
                users.append(
                    User(
                        name=user.get("username", ""),
                        uid=user.get("uid", -1),
                        gid=user.get("gid", -1),
                        info=user.get("comment", None),
                        home=user.get("home", ""),
                        shell=user.get("shell", ""),
                    )
                )

        return Users(users)


class MemoryMetricCollector(ShellCollector):
    metric = Memory

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Memory:
        result = shell_executor.execute("free -m")

        data = jc.parse("free", result.stdout_str)

        output = Memory(
            total_mb=0,
            used_mb=0,
            free_mb=0,
            swap_total_mb=0,
            swap_used_mb=0,
            swap_free_mb=0,
        )

        for entry in data:
            if entry.get("type") == "Mem":
                output.total_mb, output.used_mb, output.free_mb = (
                    entry.get("total", 0),
                    entry.get("used", 0),
                    entry.get("free", 0),
                )
            elif entry.get("type") == "Swap":
                output.swap_total_mb, output.swap_used_mb, output.swap_free_mb = (
                    entry.get("total", 0),
                    entry.get("used", 0),
                    entry.get("free", 0),
                )

        return output


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


class PackageManagerInfoFactCollector(Collector):
    fact = PackageManagerInfo
    required_facts = [HostnameCtl]
    required_executors = [Executors.SHELL, Executors.FILES]

    def collect(self, info: CollectInfo) -> PackageManagerInfo:
        shell_executor: LinuxShellExecutor = info.executors.get(Executors.SHELL)
        files_executor: LinuxFilesExecutor = info.executors.get(Executors.FILES)

        if not shell_executor or not files_executor:
            raise RuntimeError("Required executors not available")

        hostname_ctl: HostnameCtl = info.required_facts.get(HostnameCtl)

        os = hostname_ctl.os

        output = PackageManagerInfo()

        if os_in_list(os, DEB_OS_LIST):
            output.installed_packages = self._collect_apt_packages(shell_executor)
            output.repositories = self._collect_apt_repositories(files_executor)

            if transaction_info := self._get_last_apt_transaction_info(files_executor):
                output.last_transaction_dt = transaction_info[0]
                output.last_transaction_changed = transaction_info[1]

        elif os_in_list(os, RPM_OS_LIST):
            output.installed_packages = self._collect_rpm_packages(shell_executor)
            output.repositories = self._collect_dnf_repositories(files_executor)

            if transaction_info := self._get_last_dnf_transaction_info(shell_executor):
                output.last_transaction_dt = transaction_info[0]
                output.last_transaction_changed = transaction_info[1]
        else:
            self.add_error("Unknown OS")

        return output

    ##
    ## Apt
    ##

    APT_NEW_VERSION_KEY = "upgradable to:"
    APT_LIST_FILE = "/etc/apt/sources.list"
    APT_SOURCE_FILE = "/etc/apt/sources.sources"
    APT_SOURCES_DIR = "/etc/apt/sources.list.d"
    APT_HISTORY_FILE = "/var/log/apt/history.log"

    def _collect_apt_packages(
        self, shell_executor: LinuxShellExecutor
    ) -> list[InstalledPackage]:

        result = shell_executor.execute("apt list --installed")

        if result.return_code != 0:
            self.add_error("Failed to collect apt packages")
            return []

        output = []

        for line in result.stdout:
            if package := self._parse_apt_package_info(line):
                output.append(package)

        return output

    def _parse_apt_package_info(self, line: str) -> InstalledPackage | None:

        # Example output to parse:
        # adduser/stable,now 3.152 all [installed]
        # alloy/stable,now 1.19.2-1 amd64 [installed,upgradable to: 1.20.1-1]
        # alsa-topology-conf/stable,now 1.2.5.1-3 all [installed,automatic]

        try:
            package_identifier, version, arch, meta = line.split(" ", maxsplit=3)
            package_name, package_sources = package_identifier.split("/")

            # Split into list and filter out "now"; "now" is a synonym for "installed"
            # in this case....
            package_sources = [
                source for source in package_sources.split(",") if source != "now"
            ]

            upgrade_available = False
            new_version = None

            # Meta is
            if meta:
                # Strip [ and ]
                meta = meta[1:-1]
                meta_items = meta.split(",")

                for item in meta_items:
                    if item.startswith(self.APT_NEW_VERSION_KEY):
                        upgrade_available = True
                        new_version = item.split(":")[1]
                        if new_version:
                            new_version = new_version.strip()
                        break

            return InstalledPackage(
                name=package_name,
                current_version=version,
                arch=arch,
                sources=package_sources,
                upgrade_available=upgrade_available,
                new_version=new_version,
            )

        except ValueError:
            return None

    def _collect_apt_repositories(
        self, files_executor: LinuxFilesExecutor
    ) -> list[AptRepository]:

        files = [Path(self.APT_SOURCE_FILE), Path(self.APT_LIST_FILE)]
        for file in files_executor.list_dir(self.APT_SOURCES_DIR):
            if file.name.endswith(".list") or file.name.endswith(".sources"):
                files.append(file)

        sources = []
        for file in files:
            try:
                if file.name.endswith(".list"):
                    if repository := self._collect_apt_list_file(file, files_executor):
                        sources.extend(repository)
                elif file.name.endswith(".sources"):
                    if repository := self._collect_apt_source_file(
                        file, files_executor
                    ):
                        sources.extend(repository)
            except FileNotFoundError:
                continue

        return sources

    def _collect_apt_list_file(
        self, file: Path, files_executor: LinuxFilesExecutor
    ) -> list[AptRepository]:
        parsed_entries = []

        # Regex to match: [type] [options] [uri] [distribution] [components...]
        # Example: deb [arch=amd64 signed-by=...] http://deb.debian.org/debian bookworm main contrib
        APT_LINE_REGEX = re.compile(
            r"^(?P<type>deb|deb-src)\s+"  # Match type
            r"(?:\[(?P<options>[^\]]+)\]\s+)?"  # Match optional [...] options
            r"(?P<uri>\S+)\s+"  # Match URI
            r"(?P<dist>\S+)\s+"  # Match distribution/suite
            r"(?P<components>.+)$"  # Match rest as components
        )

        with files_executor.open(file) as f:
            for line in f:
                # files_executor returns bytes always, but can be safely cast to str
                line = line.decode("utf-8").partition("#")[0].strip()
                # Ignore empty lines
                if not line:
                    continue

                match = APT_LINE_REGEX.match(line)
                if match:
                    data = match.groupdict()

                    # Parse options if they exist
                    options = {}
                    if data["options"]:
                        options = dict(
                            opt.split("=") for opt in data["options"].split()
                        )

                    parsed_entries.append(
                        AptRepository(
                            dist=data["dist"],
                            source_file=str(file),
                            uri=data["uri"],
                            components=data["components"].split(),
                            options=options,
                        )
                    )

        return parsed_entries

    def _collect_apt_source_file(
        self, file: Path, files_executor: LinuxFilesExecutor
    ) -> list[AptRepository]:
        parsed_entries = []
        paragraphs = []
        current_paragraph = {}
        current_key = None

        with files_executor.open(file) as f:
            for raw_bytes in f:
                raw_line = raw_bytes.decode("utf-8").rstrip("\r\n")
                line = raw_line.strip()

                if line.startswith("#"):
                    continue

                if not line:
                    if current_paragraph:
                        paragraphs.append(current_paragraph)
                        current_paragraph = {}
                        current_key = None
                    continue

                if raw_line.startswith((" ", "\t")) and current_key:
                    current_paragraph[current_key] += " " + line
                elif ":" in line:
                    key, _, value = line.partition(":")
                    current_key = key.strip()
                    current_paragraph[current_key] = value.strip()

        if current_paragraph:
            paragraphs.append(current_paragraph)

        for paragraph in paragraphs:
            field_map = {k.lower(): v for k, v in paragraph.items()}

            uris_val = field_map.get("uris") or field_map.get("uri")
            suites_val = field_map.get("suites") or field_map.get("suite")
            components_val = (
                field_map.get("components") or field_map.get("component") or ""
            )

            if not uris_val or not suites_val:
                continue

            options = {
                k: v
                for k, v in paragraph.items()
                if k.lower()
                not in ("uris", "uri", "suites", "suite", "components", "component")
            }

            components = components_val.split()

            for uri in uris_val.split():
                for suite in suites_val.split():
                    parsed_entries.append(
                        AptRepository(
                            dist=suite,
                            source_file=str(file),
                            uri=uri,
                            components=components,
                            options=options,
                        )
                    )

        return parsed_entries

    def _get_last_apt_transaction_info(
        self, files_executor: LinuxFilesExecutor
    ) -> tuple[datetime, int] | None:

        try:
            with files_executor.open(self.APT_HISTORY_FILE) as f:
                lines = f.read().decode("utf-8").splitlines()

                last_transaction_index = -1

                for index, line in enumerate(reversed(lines)):
                    if line.startswith("Start-Date:"):
                        last_transaction_index = len(lines) - index - 1
                        break

                if last_transaction_index == -1:
                    return None

                last_transaction = lines[last_transaction_index:]

                if last_transaction:
                    date_part = last_transaction[0].partition(":")[2].strip()
                    try:
                        date_parts = date_part.split(None, 1)
                        if len(date_parts) != 2:
                            return None
                        date_str, time_str = date_parts
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                        time = datetime.strptime(time_str, "%H:%M:%S").time()
                        dt = datetime.combine(date, time)
                    except (ValueError, IndexError):
                        return None

                    changed_count = 0

                    for line in last_transaction:
                        if ":" in line:
                            key, _, value = line.partition(":")
                            if key.strip() in ["Install", "Upgrade", "Remove"]:
                                changed_count += len(value.strip().split(","))

                    return dt, changed_count
                else:
                    return None

        except FileNotFoundError:
            return None

    ##
    ## DNF
    ##

    DNF_REPO_DIR = "/etc/yum.repos.d"

    def _collect_rpm_packages(
        self, shell_executor: LinuxShellExecutor
    ) -> list[InstalledPackage]:
        list_packages_result = shell_executor.execute("dnf list installed -y")

        if list_packages_result.return_code != 0:
            self.add_error("Failed to collect RPM packages")
            return []

        check_update_result = shell_executor.execute(
            "dnf check-update -y", fail_silent=True
        )

        upgradable_packages = {}

        # dnf check-update returns 100 when there are updates available, so
        # we need to 'pass' on that status as well.
        if (
            check_update_result.return_code != 0
            and check_update_result.return_code != 100
        ):
            self.add_error("Failed to check for RPM package updates")
        else:
            for line in check_update_result.stdout:
                parts = line.split()

                # Only parse lines with exactly 3 parts; other stuff is irrelevant output
                if len(parts) != 3:
                    continue

                package_identifier, version, _ = parts

                upgradable_packages[package_identifier] = version

        output = []

        for line in list_packages_result.stdout:
            parts = line.split()
            # Only parse lines with exactly 3 parts; other stuff is irrelevant output
            if len(parts) != 3:
                continue

            package_identifier, version, source = parts

            # We do an rsplit to handle package names with dots in them
            if "." in package_identifier:
                package_name, package_arch = package_identifier.rsplit(".", maxsplit=1)
            else:
                package_name, package_arch = package_identifier, None

            new_version = upgradable_packages.get(package_identifier)

            output.append(
                InstalledPackage(
                    name=package_name,
                    current_version=version,
                    sources=[source],
                    arch=package_arch,
                    upgrade_available=new_version is not None,
                    new_version=new_version,
                )
            )

        return output

    def _collect_dnf_repositories(
        self, files_executor: LinuxFilesExecutor
    ) -> list[RpmRepository]:
        files = [
            file
            for file in files_executor.list_dir(self.DNF_REPO_DIR)
            if file.name.endswith(".repo")
        ]

        output = []

        for file in files:
            with files_executor.open(file) as f:
                config_parser = configparser.ConfigParser()
                config_parser.read_string(f.read().decode("utf-8"))

                for section in config_parser.sections():
                    data = {}
                    for key, value in config_parser[section].items():
                        data[key] = value

                    options = {
                        k: v
                        for k, v in config_parser[section].items()
                        if k
                        not in (
                            "name",
                            "baseurl",
                            "mirrorlist",
                            "metalink",
                            "enabled",
                            "gpgcheck",
                            "gpgkey",
                        )
                    }

                    output.append(
                        RpmRepository(
                            id=section,
                            source_file=str(file),
                            name=data.get("name", section),
                            base_url=data.get("baseurl"),
                            mirrorlist=data.get("mirrorlist"),
                            metalink=data.get("metalink"),
                            enabled=data.get("enabled", "1") == "1",
                            gpg_check=data.get("gpgcheck") == "1",
                            gpg_key=data.get("gpgkey"),
                            options=options,
                        )
                    )

        return output

    def _get_last_dnf_transaction_info(
        self, shell_executor: LinuxShellExecutor
    ) -> tuple[datetime, int] | None:
        output = shell_executor.execute("dnf history list last")
        if output.return_code != 0:
            return None

        for line in reversed(output.stdout):
            line = line.strip()
            if not line:
                continue

            parts = [part.strip() for part in line.split("|")]
            if len(parts) != 5:
                continue

            _id, command, _datetime, actions, changed = parts

            try:
                dt = datetime.strptime(_datetime, "%Y-%m-%d %H:%M")
            except ValueError:
                continue

            if " " in changed:
                changed = changed.split(" ")[0]

            try:
                changed = int(changed)
            except ValueError:
                changed = 0

            return dt, changed

        return None


class NetworkInterfacesFactCollector(ShellCollector):
    fact = NetworkInterfaces

    required_facts = [HostnameCtl]

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> NetworkInterfaces | None:

        # CentOS 7 is not compatible with this code, as it lacks the -j flag
        # And I really cannot be bothered to write CentOS 7 compatible code,
        # as it's a pain to parse!
        host_info: HostnameCtl = info.required_facts[HostnameCtl]
        if host_info.cpe_os_name == "cpe:/o:centos:centos:7":
            return None

        ip_cmd = shell_executor.execute("ip -j addr show")

        data = json.loads(ip_cmd.stdout_str)

        interfaces = []

        for interface in data:
            addresses = []
            for address in interface["addr_info"]:
                addresses.append(
                    AddressInfo(
                        family=address["family"],
                        address=f"{address['local']}/{address['prefixlen']}",
                        scope=address["scope"],
                    )
                )

            interfaces.append(
                NetworkInterface(
                    name=interface["ifname"],
                    altnames=interface.get("altnames", []),
                    link_type=interface["link_type"],
                    mac_address=interface["address"],
                    flags=interface["flags"],
                    addresses=addresses,
                )
            )

        return NetworkInterfaces(interfaces)


class SELinuxFactCollector(ShellCollector):
    fact = SELinux

    required_facts = [HostnameCtl]

    STATUS_KEY = "SELinux status"
    POLICY_KEY = "Loaded policy name"
    MODE_KEY = "Current mode"

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> SELinux | None:

        # We only check if we think this OS supports selinux
        host_info: HostnameCtl = info.required_facts[HostnameCtl]
        if not os_in_list(host_info.os, SELINUX_OS_LIST):
            return None

        sestatus_command = shell_executor.execute(
            # We need to use a full path, as /usr/sbin isn't always in PATH for some reason
            "/usr/sbin/sestatus",
            fail_silent=True,
        )

        if sestatus_command.return_code != 0:
            return None

        enabled = False
        policy_name = None
        mode = None

        for line in sestatus_command.stdout:
            key, value = line.strip().split(":")
            stripped_key = key.strip()
            stripped_value = value.strip()

            match stripped_key:
                case self.STATUS_KEY:
                    enabled = stripped_value.lower() == "enabled"
                case self.POLICY_KEY:
                    policy_name = stripped_value
                case self.MODE_KEY:
                    mode = stripped_value

        return SELinux(
            enabled=enabled,
            policy_name=policy_name,
            mode=mode,
        )


class SystemDFactCollector(ShellCollector):
    fact = Systemd
    required_facts = [HostnameCtl]

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Systemd | None:

        # CentOS 7 and Debian 10 are not compatible with this code, as it lacks
        # the -o flag
        # And I really cannot be bothered to write compatible code,
        # as it's hard to parse and those OS's should be phased out anyway.
        host_info: HostnameCtl = info.required_facts[HostnameCtl]
        if (
            host_info.cpe_os_name == "cpe:/o:centos:centos:7"
            or host_info.os == "Debian GNU/Linux 10 (buster)"
        ):
            return None

        result = shell_executor.execute("systemctl list-units --output json")

        try:
            unit_data = json.loads("".join(result.stdout))
        except json.JSONDecodeError:
            self.add_error("Failed to parse systemctl output")
            return None

        units = []

        for datum in unit_data:
            units.append(SystemdUnit(**datum))

        return Systemd(units=units)


class IPTableFactCollector(ShellCollector):
    fact = IPTables

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> IPTables | None:

        iptable_cmd = shell_executor.execute("sudo iptables -nvL")
        iptable_data = jc.parse("iptables", iptable_cmd.stdout_str)

        if not iptable_data:
            return None

        chains = []
        for chain_data in iptable_data:
            chains.append(IPTablesChain(**chain_data))

        return IPTables(
            chains=chains,
            port_access=self._summarize_port_access(chains),
        )

    ALLOW_TARGETS = ("ACCEPT",)
    DENY_TARGETS = ("DROP", "REJECT")
    RETURN_TARGET = "RETURN"
    PORT_PROTOCOLS = ("tcp", "udp", "all")
    ANY_SOURCE = "0.0.0.0/0"
    ANY_INTERFACE = "*"

    # Matches '[tcp|udp] dpt:22', 'dpts:1000:2000', 'multiport dports 80,443'
    _PORT_RE = re.compile(r"\bdpts?:(\S+)|\bdports?\s+(\S+)")
    _STATE_RE = re.compile(r"\b(?:ct)?state\s+(\S+)")

    @classmethod
    def _summarize_port_access(
        cls, chains: list[IPTablesChain]
    ) -> list[IPTablesPortAccess]:
        """Build a per-port overview of allowed/denied sources from the
        INPUT chain.

        For every destination port/protocol that is mentioned in the rules, the
        INPUT chain is walked in order like iptables would do for a new
        connection to that port: the first rule that matches a given source
        decides. Rules (or the parts of them) that are shadowed by an earlier
        rule are not reported, jumps into custom chains are followed and the
        default policy of the chain is applied to whatever is left over.

        Only source address, input interface, protocol, destination port and
        connection state are taken into account; other matches (limits, owner,
        mac, ...) are ignored.
        """
        chain_map = {chain.chain: chain for chain in chains}
        input_chain = chain_map.get("INPUT")
        if input_chain is None:
            return []

        summaries = []
        for port, protocol in cls._collect_port_keys(input_chain, chain_map):
            summary = IPTablesPortAccess(port=port, protocol=protocol)
            decided = _IPTablesCoverage()

            cls._walk_chain(
                chain=input_chain,
                chain_map=chain_map,
                port=port,
                protocol=protocol,
                decided=decided,
                summary=summary,
                scope_networks=[_IPTablesCoverage.ANY_NETWORK],
                scope_source=cls.ANY_SOURCE,
                scope_interface=cls.ANY_INTERFACE,
                visited=frozenset({input_chain.chain}),
            )

            # Whatever was not matched by any rule falls back to the policy
            if not decided.covers_everything():
                if input_chain.default_policy in cls.ALLOW_TARGETS:
                    cls._record_verdict(
                        summary, True, cls.ANY_SOURCE, cls.ANY_INTERFACE
                    )
                elif input_chain.default_policy in cls.DENY_TARGETS:
                    cls._record_verdict(
                        summary, False, cls.ANY_SOURCE, cls.ANY_INTERFACE
                    )

            if cls.ANY_SOURCE in summary.denied_from:
                summary.denied_from = [cls.ANY_SOURCE]

            summaries.append(summary)

        return sorted(
            summaries,
            key=lambda s: (s.port is not None, cls._port_sort_key(s.port), s.protocol),
        )

    @classmethod
    def _collect_port_keys(
        cls,
        chain: IPTablesChain,
        chain_map: dict[str, IPTablesChain],
        visited: frozenset[str] = frozenset(),
    ) -> list[tuple[str | None, str]]:
        """Return every (port, protocol) combination that is mentioned in the
        given chain and in the custom chains it jumps to, in order of first
        appearance.
        """
        visited = visited | {chain.chain}
        keys: dict[tuple[str | None, str], None] = {}

        for rule in chain.rules:
            if rule.prot in cls.PORT_PROTOCOLS and cls._matches_new_connections(rule):
                for port in cls._extract_ports(rule.options):
                    if port is not None and rule.prot == "all":
                        # Ports only make sense for tcp/udp
                        continue
                    keys.setdefault((port, rule.prot), None)

            if rule.target in chain_map and rule.target not in visited:
                for key in cls._collect_port_keys(
                    chain_map[rule.target], chain_map, visited
                ):
                    keys.setdefault(key, None)

        return list(keys)

    @classmethod
    def _walk_chain(
        cls,
        chain: IPTablesChain,
        chain_map: dict[str, IPTablesChain],
        port: str | None,
        protocol: str,
        decided: "_IPTablesCoverage",
        summary: IPTablesPortAccess,
        scope_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
        scope_source: str,
        scope_interface: str,
        visited: frozenset[str],
    ) -> None:
        """Walk a chain in order for traffic to the given port/protocol,
        restricted to the sources/interface that jumped into this chain.

        Every source that gets a final verdict is added to ``decided`` so
        later rules no longer apply to it, mimicking iptables' first-match
        behaviour. Sources hitting RETURN (or the end of the chain) fall back
        to the calling chain.
        """
        # Sources that RETURNed from this chain; they are no longer matched by
        # the remaining rules in this chain, but are still undecided
        returned = _IPTablesCoverage()

        for rule in chain.rules:
            if not cls._rule_applies_to(rule, port, protocol):
                continue

            interface = cls._combine_interfaces(scope_interface, rule.in_)
            if interface is None:
                continue

            rule_networks = cls._parse_networks(rule.source)
            if rule_networks is None:
                continue

            networks = _IPTablesCoverage.intersect(scope_networks, rule_networks)
            networks = decided.remaining(networks, interface)
            networks = returned.remaining(networks, interface)
            if not networks:
                # Fully shadowed by earlier rules
                continue

            # Report the most specific source spec we have
            source = rule.source
            if source == cls.ANY_SOURCE:
                source = scope_source

            if rule.target in cls.ALLOW_TARGETS:
                cls._record_verdict(summary, True, source, interface)
                decided.add(networks, interface)
            elif rule.target in cls.DENY_TARGETS:
                cls._record_verdict(summary, False, source, interface)
                decided.add(networks, interface)
            elif rule.target == cls.RETURN_TARGET:
                returned.add(networks, interface)
            elif rule.target in chain_map and rule.target not in visited:
                cls._walk_chain(
                    chain=chain_map[rule.target],
                    chain_map=chain_map,
                    port=port,
                    protocol=protocol,
                    decided=decided,
                    summary=summary,
                    scope_networks=networks,
                    scope_source=source,
                    scope_interface=interface,
                    visited=visited | {rule.target},
                )
            # LOG, comments, unknown targets, etc. are non-terminating

    @classmethod
    def _rule_applies_to(
        cls, rule: IPTableRules, port: str | None, protocol: str
    ) -> bool:
        """Check if a rule can match a new connection to the given
        port/protocol combination.
        """
        if rule.prot not in cls.PORT_PROTOCOLS:
            return False

        if rule.prot != "all" and rule.prot != protocol:
            return False

        # A rule for a specific protocol does not cover 'all protocols'
        if protocol == "all" and rule.prot != "all":
            return False

        if not cls._matches_new_connections(rule):
            return False

        if not cls._destination_applies(rule.destination):
            return False

        rule_ports = cls._extract_ports(rule.options)
        if rule_ports == [None]:
            return True

        # A rule for specific ports does not cover 'all ports'
        if port is None:
            return False

        return any(cls._port_in_spec(port, spec) for spec in rule_ports)

    @classmethod
    def _matches_new_connections(cls, rule: IPTableRules) -> bool:
        # Rules that only match existing connections do not open ports
        state_match = cls._STATE_RE.search(rule.options)
        return not state_match or "NEW" in state_match.group(1).split(",")

    @classmethod
    def _destination_applies(cls, destination: str) -> bool:
        """Check if a rule's destination can apply to traffic addressed to
        this host. Rules for multicast/broadcast destinations (or with
        unparsable netmasks) are skipped; a specific unicast destination is
        assumed to be one of the host's own addresses.
        """
        if destination == cls.ANY_SOURCE:
            return True

        networks = cls._parse_networks(destination)
        if networks is None:
            return False

        return not any(
            network.is_multicast or network.is_reserved for network in networks
        )

    @classmethod
    def _combine_interfaces(cls, scope_interface: str, interface: str) -> str | None:
        """Combine the interface of a jump rule with the one of a rule in the
        target chain; None if they conflict.
        """
        interface = interface or cls.ANY_INTERFACE
        if scope_interface == cls.ANY_INTERFACE:
            return interface
        if interface == cls.ANY_INTERFACE or interface == scope_interface:
            return scope_interface
        return None

    @classmethod
    def _parse_networks(
        cls, source: str
    ) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None:
        """Parse an iptables source spec into a list of networks; None if it
        cannot be parsed (e.g. non-contiguous netmasks).
        """
        negated = source.startswith("!")
        source = source.lstrip("!").strip()

        _address, _sep, mask = source.partition("/")
        if "." in mask:
            # iptables shows dotted masks as netmasks, which may be
            # non-contiguous (e.g. 0.0.0.255); python would happily read
            # those as hostmasks, which means something else entirely
            try:
                mask_bits = int(ipaddress.IPv4Address(mask))
            except ValueError:
                return None
            host_bits = ~mask_bits & 0xFFFFFFFF
            if host_bits & (host_bits + 1):
                return None

        try:
            network = ipaddress.ip_network(source, strict=False)
        except ValueError:
            return None

        if negated:
            return _IPTablesCoverage.subtract(
                [_IPTablesCoverage.ANY_NETWORK], [network]
            )
        return [network]

    @classmethod
    def _record_verdict(
        cls,
        summary: IPTablesPortAccess,
        allowed: bool,
        source: str,
        interface: str,
    ) -> None:
        if interface != cls.ANY_INTERFACE:
            source = f"{source}@{interface}"

        target_list = summary.allowed_from if allowed else summary.denied_from
        if source not in target_list:
            target_list.append(source)

        if allowed and source == cls.ANY_SOURCE:
            summary.default_open = True
        elif not allowed and source == cls.ANY_SOURCE:
            summary.default_closed = True

    @classmethod
    def _extract_ports(cls, options: str) -> list[str | None]:
        """Return the destination ports a rule applies to; [None] if the rule
        is not restricted to a port.
        """
        match = cls._PORT_RE.search(options)
        if not match:
            return [None]

        port_spec = match.group(1) or match.group(2)
        return [port for port in port_spec.split(",") if port]

    @classmethod
    def _port_in_spec(cls, port: str, spec: str) -> bool:
        """Check if a port (or port range) falls completely within a port spec
        from a rule. Both are formatted as either 'port' or 'start:end'.
        """
        port_range = cls._parse_port_range(port)
        spec_range = cls._parse_port_range(spec)
        if port_range is None or spec_range is None:
            return port == spec

        return spec_range[0] <= port_range[0] and port_range[1] <= spec_range[1]

    @staticmethod
    def _parse_port_range(port: str) -> tuple[int, int] | None:
        start, _, end = port.partition(":")
        try:
            start_num = int(start) if start else 0
            end_num = int(end) if end else (start_num if not _ else 65535)
        except ValueError:
            return None
        return start_num, end_num

    @staticmethod
    def _port_sort_key(port: str | None) -> int:
        if port is None:
            return -1
        try:
            # Port ranges are formatted as 'start:end'
            return int(port.split(":")[0])
        except ValueError:
            return 0


_Network = ipaddress.IPv4Network | ipaddress.IPv6Network


class _IPTablesCoverage:
    """Keeps track of which source networks already got a verdict from an
    earlier iptables rule, per input interface.

    Rules bound to a specific interface only cover traffic on that interface,
    while rules without an interface cover traffic on every interface.
    """

    ANY_NETWORK = ipaddress.ip_network("0.0.0.0/0")
    ANY_INTERFACE = IPTableFactCollector.ANY_INTERFACE

    def __init__(self):
        self._covered: dict[str, list[_Network]] = {}

    def add(self, networks: list[_Network], interface: str) -> None:
        self._covered.setdefault(interface, []).extend(networks)

    def remaining(self, networks: list[_Network], interface: str) -> list[_Network]:
        """Return the parts of the given networks that are not covered yet
        for traffic on the given interface.
        """
        networks = self.subtract(networks, self._covered.get(self.ANY_INTERFACE, []))
        if interface != self.ANY_INTERFACE:
            networks = self.subtract(networks, self._covered.get(interface, []))
        return networks

    def covers_everything(self) -> bool:
        return not self.remaining([self.ANY_NETWORK], self.ANY_INTERFACE)

    @staticmethod
    def subtract(networks: list[_Network], exclude: list[_Network]) -> list[_Network]:
        for excluded in exclude:
            result = []
            for network in networks:
                if network.version != excluded.version or not network.overlaps(
                    excluded
                ):
                    result.append(network)
                elif network.subnet_of(excluded):
                    continue
                else:
                    result.extend(network.address_exclude(excluded))
            networks = result
            if not networks:
                break
        return networks

    @staticmethod
    def intersect(left: list[_Network], right: list[_Network]) -> list[_Network]:
        result = []
        for a in left:
            for b in right:
                if a.version != b.version or not a.overlaps(b):
                    continue
                # Networks either nest or are disjoint; keep the smaller one
                result.append(a if a.subnet_of(b) else b)
        return result
