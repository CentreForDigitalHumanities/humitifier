import configparser
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
