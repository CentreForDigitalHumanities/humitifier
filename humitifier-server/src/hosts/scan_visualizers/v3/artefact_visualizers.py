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
                aside = '<span class="px-3 py-1 mr-auto rounded-sm bg-red-500 text-white font-bold">Upgrade available</span>'

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
            [access for access in port_access if access["open_to_all"]]
        )
        context["chains"] = chains
        context["num_rules"] = sum(len(chain["rules"]) for chain in chains)

        context["alpinejs_settings"]["show_rules"] = "false"
        context["alpinejs_settings"]["rule_search"] = "''"

        return context

    def _get_port_access_item(self, access: IPTablesPortAccess) -> dict:
        allowed_from = [self._format_source(source) for source in access.allowed_from]
        denied_from = [self._format_source(source) for source in access.denied_from]

        # Sources that are only allowed on a specific interface (like 'lo') are
        # not reachable from the outside, so they are not counted as 'open'
        external_allowed = [
            source for source in access.allowed_from if "@" not in source
        ]

        if access.open_to_all:
            status = "Open to everyone"
            color = "gray"
        elif external_allowed:
            status = len(external_allowed)
            color = "green"
        elif access.allowed_from:
            status = "Local only"
            color = "gray"
        else:
            status = "Denied only"
            color = "gray"

        return {
            "port": self._format_port(access.port),
            "protocol": access.protocol,
            "status": status,
            "color": color,
            "open_to_all": access.open_to_all,
            "allowed_from": allowed_from,
            "denied_from": denied_from,
        }

    @staticmethod
    def _format_port(port: str | None) -> str:
        if port is None:
            return "Any port"

        # Port ranges are formatted as 'start:end'
        return port.replace(":", "\u2013")

    def _format_source(self, source: str) -> str:
        interface = None
        if "@" in source:
            source, interface = source.split("@", 1)

        if source == self.ANY_SOURCE:
            source = "anyone"

        if interface:
            return f"{source} via {interface}"

        return source

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
