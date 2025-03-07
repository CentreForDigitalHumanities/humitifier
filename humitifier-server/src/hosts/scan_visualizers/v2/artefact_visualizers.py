from datetime import datetime

from cron_descriptor import (
    FormatException,
    Options,
    get_description as get_cron_description,
)
from django.utils.safestring import mark_safe

from hosts.scan_visualizers.base_components import (
    ArtefactVisualizer,
    Bar,
    BarsArtefactVisualizer,
    Card,
    ItemizedArtefactVisualizer,
    SearchableCardsVisualizer,
)

from hosts.templatetags.host_tags import size_from_mb, uptime
from humitifier_common.artefacts import (
    Blocks,
    Groups,
    Hardware,
    HostMeta,
    HostnameCtl,
    IsWordpress,
    Memory,
    NetworkInterfaces,
    PackageList,
    PuppetAgent,
    RebootPolicy,
    Uptime,
    Users,
    ZFS,
)


class HostMetaVisualizer(ItemizedArtefactVisualizer):
    artefact = HostMeta
    title = "GenDoc metadata"
    attributes = {
        "update_policy": "Update policy",
        "webdav": "Webdav share",
        "fileservers": "Fileservers",
    }

    def get_items(self) -> list[dict[str, str]]:
        items = super().get_items()

        if self.artefact_data.databases:
            for database_software, databases in self.artefact_data.databases.items():
                items.append(
                    {
                        "label": f"{database_software.capitalize()} DB's",
                        "value": ", ".join(databases),
                    }
                )

        return items

    @staticmethod
    def get_fileservers_display(value):
        return ", ".join(value)

    @staticmethod
    def get_update_policy_display(value):
        output = "<div class='flex gap-2'>"

        if value["enable"]:
            output += f"<span class='text-green-500'>Enabled</span>"
        else:
            output += f"<span class='text-red'>Disabled</span>"

        if value["apply_updates"]:
            output += f"<span class='text-green-500'>Applied</span>"
        else:
            output += f"<span class='text-red'>Not applied</span>"

        output += "</div>"

        return mark_safe(output)


class HostMetaVHostsVisualizer(SearchableCardsVisualizer):
    artefact = HostMeta
    title = "Apache vhosts"

    def show(self):
        if not super().show():
            return False

        return hasattr(self.artefact_data, "vhosts") and self.artefact_data.vhosts

    def get_items(self) -> list[Card]:
        items = []

        merged_dict = {}

        for vhost in self.artefact_data.vhosts:
            merged_dict.update(vhost)

        for vhost, data in merged_dict.items():
            content = None
            search_value = f"{vhost} {data.docroot}"
            if data.serveraliases:
                content = {
                    "aliases": ", ".join(data.serveraliases),
                }
                search_value += f" {" ".join(data.serveraliases)}"

            items.append(
                Card(
                    title=vhost,
                    aside=data.docroot,
                    content_items=content,
                    search_value=search_value,
                )
            )

        return items


class HostnameCtlVisualizer(ItemizedArtefactVisualizer):
    artefact = HostnameCtl
    title = "Host metadata"
    attributes = {
        "hostname": "Hostname",
        "os": "OS",
        "cpe_os_name": "CPE OS name",
        "kernel": "Kernel",
        "virtualization": "Virtualization",
    }


class UptimeVisualizer(ArtefactVisualizer):
    title = "Host uptime"
    artefact = Uptime

    def get_context(self, **kwargs):
        context = super().get_context(**kwargs)

        if not self.artefact:
            context["content"] = '<div class="text-gray-500">Unknown</div>'
        else:
            host_uptime = uptime(self.artefact_data, self.scan_date)

            context["content"] = mark_safe(
                f"<div class='flex align-center h-100'" f">{host_uptime}</div>"
            )

        return context


class MemoryVisualizer(BarsArtefactVisualizer):
    title = "Memory usage"
    artefact = Memory

    def get_bar_items(self) -> list[Bar]:
        return [
            Bar(
                label_1="Memory",
                used=size_from_mb(self.artefact_data.used_mb),
                total=size_from_mb(self.artefact_data.total_mb),
                percentage=self.artefact_data.used_mb
                / self.artefact_data.total_mb
                * 100,
            ),
            Bar(
                label_1="Swap",
                used=size_from_mb(self.artefact_data.swap_used_mb),
                total=size_from_mb(self.artefact_data.swap_total_mb),
                percentage=self.artefact_data.swap_used_mb
                / self.artefact_data.swap_total_mb
                * 100,
            ),
        ]


class BlocksVisualizer(BarsArtefactVisualizer):
    title = "Disk usage"
    artefact = Blocks

    def get_bar_items(self) -> list[Bar]:
        block_data = []
        for block in self.artefact_data:
            block_data.append(
                Bar(
                    label_1=block.name,
                    label_2=block.mount,
                    used=size_from_mb(block.used_mb),
                    total=size_from_mb(block.size_mb),
                    percentage=block.use_percent,
                )
            )

        return block_data


class UsersVisualizer(SearchableCardsVisualizer):
    title = "Users"
    artefact = Users
    search_placeholder = "Search groups"

    def get_items(self) -> list[Card]:
        output = []

        for user in self.artefact_data:
            output.append(
                Card(
                    title=user.name,
                    content_items={
                        "Info": user.info,
                        "Group ID": user.gid,
                        "User ID": user.uid,
                        "Homedir": user.home,
                        "shell": user.shell,
                    },
                    search_value=f"{user.name} {user.uid} {user.info}",
                )
            )

        return output


class GroupsVisualizer(SearchableCardsVisualizer):
    title = "Groups"
    artefact = Groups
    search_placeholder = "Search groups"

    def get_items(self) -> list[Card]:
        output = []
        for group in self.artefact_data:
            output.append(
                Card(
                    title=group.name,
                    aside=group.gid,
                    content=", ".join(group.users),
                    search_value=f"{group.name} {group.gid}",
                )
            )

        return output


class PackageListVisualizer(SearchableCardsVisualizer):
    title = "Packages"
    artefact = PackageList
    search_placeholder = "Search packages"

    def get_items(self) -> list[Card]:
        output = []
        for package in self.artefact_data:
            output.append(
                Card(
                    title=package.name,
                    aside=package.version,
                    search_value=f"{package.name} {package.version}",
                )
            )

        return output


class PuppetAgentVisualizer(ArtefactVisualizer):
    title = "Puppet Agent"
    artefact = PuppetAgent

    template = "hosts/scan_visualizer/components/puppet_component.html"

    def get_context(self, **kwargs) -> dict:
        context = super().get_context(**kwargs)

        last_run = None
        if self.artefact_data.last_run:
            last_run = datetime.fromisoformat(self.artefact_data.last_run)

        context["puppet"] = self.artefact_data
        context["last_run"] = last_run

        return context


class IsWordpressVisualizer(ArtefactVisualizer):
    title = "Is Wordpress?"
    artefact = IsWordpress

    def show(self):
        return self.artefact_data and self.artefact_data.is_wp

    def get_context(self, **kwargs) -> dict:
        context = super().get_context(**kwargs)

        # We only show this component if it's wordpress, sooo
        context["content"] = "Yes!"

        return context


class HardwareVisualizer(ArtefactVisualizer):
    title = "Hardware"
    artefact = Hardware
    template = "hosts/scan_visualizer/components/hardware_component.html"

    def get_context(self, **kwargs) -> dict:
        context = super().get_context(**kwargs)

        context["hardware"] = self.artefact_data

        total_memory = sum([memrange.size for memrange in self.artefact_data.memory])
        context["total_memory"] = total_memory

        return context


class NetworkInterfacesVisualizer(SearchableCardsVisualizer):
    title = "Network Interfaces"
    artefact = NetworkInterfaces

    def get_items(self) -> list[Card]:
        output = []

        for interface in self.artefact_data:
            content_items = {
                "Altnames": ", ".join(interface.altnames),
                "Link type": interface.link_type,
                "Flags": ", ".join(interface.flags),
            }
            search_value = f"{interface.name} {interface.altnames}"
            for address in interface.addresses:
                search_value += f" {address.address}"
                content_items[address.family] = address.address

            output.append(
                Card(
                    title=interface.name,
                    aside=interface.mac_address,
                    content_items=content_items,
                    search_value=search_value,
                )
            )

        return output


class ZFSVisualizer(ArtefactVisualizer):
    title = "ZFS"
    artefact = ZFS
    template = "hosts/scan_visualizer/components/zfs_component.html"

    def get_context(self, **kwargs) -> dict:
        context = super().get_context(**kwargs)

        context["zfs"] = self.artefact_data

        return context


class RebootPolicyVisualizer(ArtefactVisualizer):
    title = "Reboot Policy"
    artefact = RebootPolicy
    template = "hosts/scan_visualizer/components/reboot_policy.html"

    def parse_cron(self) -> str:
        if not (
            self.artefact_data.cron_minute
            and self.artefact_data.cron_hour
            and self.artefact_data.cron_monthday
        ):
            return ""

        cron_line = "{} {} {} * *".format(
            self.artefact_data.cron_minute,
            self.artefact_data.cron_hour,
            self.artefact_data.cron_monthday,
        )

        options = Options()
        options.verbose = True
        options.use_24hour_time_format = True

        try:
            return get_cron_description(cron_line, options)
        except FormatException:
            return ""

    def get_context(self, **kwargs) -> dict:
        context = super().get_context(**kwargs)

        context["reboot_policy"] = self.artefact_data
        context["cron_description"] = self.parse_cron()

        return context
