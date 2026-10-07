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
