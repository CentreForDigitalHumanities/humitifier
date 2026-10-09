import ipaddress
import re
import socket
from django.template.defaultfilters import date
from django.utils.safestring import mark_safe

from hosts.scan_visualizers.base_components import (
    ArtefactVisualizer,
    Card,
    SearchableCardsWithHeaderVisualizer,
)
from hosts.templatetags.host_tags import uptime
from humitifier_common.artefacts import (
    V3Uptime,
    PackageManagerInfo,
    RpmRepository,
    AptRepository,
    IPTables,
    IPTablesChain,
    IPTablesPortAccess,
    IPTablesPortAccessSource,
)


class UptimeVisualizer(ArtefactVisualizer):
    title = "Host uptime"
    artefact = V3Uptime

    def get_context(self, **kwargs):
        context = super().get_context(**kwargs)

        artefact_data: V3Uptime | None = self.artefact_data

        if not artefact_data:
            context["content"] = '<div class="text-gray-500">Unknown</div>'
        else:
            host_uptime = uptime(artefact_data.uptime, self.scan_date)

            context["content"] = mark_safe(
                f"<div class='flex align-center'>"
                f"{host_uptime}&nbsp;"
                f"<span class='italic'>"
                f"(up since {date(artefact_data.since, "Y-m-d H:i")})"
                f"</span></div>"
            )

        return context


class PackageListVisualizer(SearchableCardsWithHeaderVisualizer):
    title = "Packages"
    artefact = PackageManagerInfo
    search_placeholder = "Search packages"

    def get_header_content(self):
        artefact_data: PackageManagerInfo = self.artefact_data

        upgradable_packages_count = len(
            [a for a in artefact_data.installed_packages if a.upgrade_available]
        )

        return mark_safe(
            f'<div class="flex justify-between"><span class="font-semibold">Upgradable packages</span><span>{upgradable_packages_count}</span></div>'
        )

    def get_items(self) -> list[Card]:
        output = []

        artefact_data: PackageManagerInfo = self.artefact_data

        for package in artefact_data.installed_packages:

            content_items = {
                "Installed version": package.current_version,
            }
            search_value = f"{package.name} {package.current_version}"
            aside = ""

            if package.upgrade_available:
                search_value += f" {package.new_version} upgrade"
                content_items["Available version"] = package.new_version or ""
                aside = '<span class="px-3 py-1 mr-auto rounded-sm text-xs border border-red-500/40 bg-red-200 dark:bg-red-900 text-red-950 dark:text-red-100 font-bold">Upgrade available</span>'

            if package.arch:
                content_items["Arch"] = package.arch

            if package.sources:
                content_items["Sources"] = ", ".join(package.sources)

            output.append(
                Card(
                    title=package.name,
                    aside=mark_safe(aside),
                    search_value=search_value,
                    content_items=content_items,
                )
            )

        return output


class PackageManagerInfoVisualizer(SearchableCardsWithHeaderVisualizer):
    title = "Package manager info"
    artefact = PackageManagerInfo
    search_placeholder = "Search repositories"

    def get_header_content(self) -> list[dict]:
        artefact_data: PackageManagerInfo = self.artefact_data

        return [
            {
                "label": "Last transaction time",
                "value": date(artefact_data.last_transaction_dt, "Y-m-d H:i"),
            },
            {
                "label": "Last transaction actions",
                "value": artefact_data.last_transaction_changed,
            },
            {  # Fake item to provide a header for the cards below
                "label": "Repositories",
                "value": " ",
            },
        ]

    def get_items(self) -> list[Card]:
        artefact_data: PackageManagerInfo = self.artefact_data

        output = []

        for repo in artefact_data.repositories:
            # RHEL has a bunch of repositories that are not enabled, which aren't
            # that interesting to list
            if isinstance(repo, RpmRepository) and repo.enabled:
                output.append(self._get_rpm_repo_card(repo))
            elif isinstance(repo, AptRepository):
                output.append(self._get_apt_repo_card(repo))

        return output

    def _get_rpm_repo_card(self, repo: RpmRepository) -> Card:
        content_items: dict[str, str] = {
            "Identifier": repo.id,
            "Source file": repo.source_file,
        }
        if repo.base_url:
            content_items["Base url"] = repo.base_url
        if repo.mirrorlist:
            content_items["Mirrorlist"] = repo.mirrorlist
        if repo.metalink:
            content_items["Metalink"] = repo.metalink
        if repo.gpg_key:
            content_items["GPG key"] = repo.gpg_key
        if repo.gpg_check:
            content_items["Gpg check"] = "Yes" if repo.gpg_check else "No"
        if repo.options:
            content_items["Other options"] = mark_safe(
                "<br>".join([f"{k}: {v}" for k, v in repo.options.items()])
            )

        return Card(
            title=repo.name,
            search_value=f"{repo.name} {repo.id}",
            content_items=content_items,
        )

    def _get_apt_repo_card(self, repo: AptRepository) -> Card:
        content_items: dict[str, str] = {
            "Source file": repo.source_file,
            "Distribution": repo.dist,
            "Components": ", ".join(repo.components),
        }

        if repo.options:
            content_items["Other options"] = mark_safe(
                "<br>".join([f"{k}: {v}" for k, v in repo.options.items()])
            )

        return Card(
            title=repo.uri,
            search_value=repo.uri,
            content_items=content_items,
        )


class FormattedSource:
    def __init__(self, source: str, title: str | None = None):
        self.source = source
        self.title = title

    @property
    def resolved_hostname(self) -> str | None:
        return self.title

    def __str__(self) -> str:
        return self.source

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.source == other
        if isinstance(other, FormattedSource):
            return self.source == other.source and self.title == other.title
        return False


class IPTablesVisualizer(ArtefactVisualizer):
    """Shows the firewall configuration, with the focus on which ports are
    reachable from where. The raw chains and rules are available too, but are
    tucked away behind a toggle as they tend to be long and rarely needed.
    """

    title = "Firewall"
    artefact = IPTables
    template = "hosts/scan_visualizer/components/iptables_component.html"

    ANY_SOURCE = "0.0.0.0/0"
    # The chains that are always present; custom chains are listed after these
    BUILTIN_CHAINS = ("INPUT", "FORWARD", "OUTPUT")
    CUSTOM_SERVICES: dict[tuple[str, int], str] = {
        ("tcp", 1936): "haproxy-stats",
        ("tcp", 5000): "",
        ("tcp", 7000): "",
        ("tcp", 8000): "",
        ("tcp", 8080): "http-alt",
        ("tcp", 8443): "https-alt",
        ("tcp", 9000): "",
        ("tcp", 21047): "InsightVM",
        ("udp", 31400): "InsightVM",
    }

    def show(self):
        return super().show() and bool(self.artefact_data.chains)

    def get_context(self, **kwargs) -> dict:
        context = super().get_context(**kwargs)

        artefact_data: IPTables = self.artefact_data

        port_access = [
            self._get_port_access_item(access) for access in artefact_data.port_access
        ]
        chains = [self._get_chain_item(chain) for chain in artefact_data.chains]

        context["port_access"] = port_access
        context["open_to_all_count"] = len(
            [access for access in port_access if access["default_open"]]
        )
        context["chains"] = chains
        context["num_rules"] = sum(len(chain["rules"]) for chain in chains)

        context["alpinejs_settings"]["show_rules"] = "false"
        context["alpinejs_settings"]["rule_search"] = "''"

        return context

    def _get_port_access_item(self, access: IPTablesPortAccess) -> dict:
        allowed_from = [
            self._format_source(source)
            for source in sorted(access.allowed_from, key=self._ip_sort_key)
        ]
        denied_from = [
            self._format_source(source)
            for source in sorted(access.denied_from, key=self._ip_sort_key)
        ]

        return {
            "port": self._format_port(access.port),
            "protocol": access.protocol,
            "service": self._get_port_service(access.port, access.protocol),
            "default_open": access.default_open,
            "default_closed": access.default_closed,
            "allowed_from": allowed_from,
            "denied_from": denied_from,
        }

    def _get_port_service(
        self, port: str | None, protocol: str | None = None
    ) -> str | None:
        if not port:
            return None
        try:
            port_num = int(port)
        except ValueError:
            return None

        proto = (
            protocol.lower()
            if protocol and protocol.lower() in ("tcp", "udp")
            else None
        )

        if proto:
            if (proto, port_num) in self.CUSTOM_SERVICES:
                return self.CUSTOM_SERVICES[(proto, port_num)]
            try:
                return socket.getservbyport(port_num, proto)
            except OSError:
                pass

        try:
            return socket.getservbyport(port_num)
        except OSError:
            return None

    @staticmethod
    def _ip_sort_key(
        item: IPTablesPortAccessSource | str,
    ) -> tuple[int, int, int, int, str]:
        raw = item.source if hasattr(item, "source") else str(item)
        if "@" in raw:
            ip_str = raw.split("@", 1)[0]
        else:
            ip_str = raw

        if ip_str == "anyone":
            ip_str = "0.0.0.0/0"

        try:
            net = ipaddress.ip_network(ip_str, strict=False)
            return (0, net.version, int(net.network_address), int(net.netmask), raw)
        except ValueError:
            return (1, 0, 0, 0, raw)

    @staticmethod
    def _format_port(port: str | None) -> str:
        if port is None:
            return "Any port"

        # Port ranges are formatted as 'start:end'
        return port.replace(":", "\u2013")

    def _format_source(self, source: IPTablesPortAccessSource | str) -> FormattedSource:
        if hasattr(source, "source") and hasattr(source, "resolved_hostname"):
            raw_source = source.source
            title = source.resolved_hostname
        else:
            raw_source = str(source)
            title = None

        interface = None
        if "@" in raw_source:
            raw_source, interface = raw_source.split("@", 1)

        if raw_source == self.ANY_SOURCE:
            formatted = "anyone"
        else:
            formatted = raw_source

        if interface:
            formatted = f"{formatted} via {interface}"

        return FormattedSource(source=formatted, title=title)

    def _get_chain_item(self, chain: IPTablesChain) -> dict:
        rules = []
        for rule in chain.rules:
            target = rule.target or ""
            rules.append(
                {
                    "target": target,
                    "target_color": self._get_target_color(target),
                    "prot": rule.prot,
                    "in": rule.in_,
                    "out": rule.out,
                    "source": rule.source,
                    "destination": rule.destination,
                    "options": rule.options,
                    "pkts": rule.pkts,
                    "search_value": " ".join(
                        [
                            target,
                            rule.prot,
                            rule.in_,
                            rule.out,
                            rule.source,
                            rule.destination,
                            rule.options,
                        ]
                    ),
                }
            )

        return {
            "chain": chain.chain,
            "default_policy": chain.default_policy,
            "rules": rules,
            "search_value": " ".join(rule["search_value"] for rule in rules),
        }

    @staticmethod
    def _get_target_color(target: str) -> str:
        if target == "ACCEPT":
            return "green"
        if target in ("DROP", "REJECT"):
            return "red"

        return "gray"
