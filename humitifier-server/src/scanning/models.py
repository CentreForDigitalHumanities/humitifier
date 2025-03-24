from pprint import pformat
from typing import TYPE_CHECKING

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe

if TYPE_CHECKING:
    from hosts.models import Host

from humitifier_common.artefacts import registry
from humitifier_common.scan_data import ArtefactScanOptions, ScanInput


class ScanSpec(models.Model):

    name = models.CharField(max_length=100)

    artefact_groups = ArrayField(
        models.CharField(max_length=100),
        default=list,
    )

    _default_scan_options = models.JSONField(
        default=dict,
    )

    parent = models.ForeignKey(
        "ScanSpec",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )

    @cached_property
    def inherited_artefact_groups(self):
        if self.parent:
            return self.parent.inherited_artefact_groups + self.parent.artefact_groups

        return []

    @cached_property
    def inherited_artefacts(self):
        if self.parent:
            items = self.parent.inherited_artefacts

            for artefact in self.parent.artefacts.all():
                items.append(artefact)

            return items

        return []

    @cached_property
    def default_scan_options(self) -> ArtefactScanOptions:
        options = (
            self._default_scan_options
            if isinstance(self._default_scan_options, dict)
            else {}
        )

        return ArtefactScanOptions(**options)

    def _build_artefact_scan_input(self) -> dict[str, ArtefactScanOptions]:
        artefacts = {}

        # First, inherit the artefacts from the parent if one is present
        if self.parent:
            artefacts = self.parent._build_artefact_scan_input()

        # Secondly, add a list of artefacts from the specified groups
        for group in self.artefact_groups:
            group_artefacts = registry.get_all_in_group(group)
            for artefact in group_artefacts:
                artefacts[artefact.__artefact_name__] = self.default_scan_options

        # Lastly, apply any manually specified artefact
        for artefact in self.artefacts.all():
            if artefact.knockout and artefact.artefact_name in artefacts:
                del artefacts[artefact.artefact_name]
                continue

            artefacts[artefact.artefact_name] = artefact.scan_options

        return artefacts

    def build_scan_input(self, host: "Host") -> ScanInput:
        return ScanInput(
            hostname=host.fqdn,
            artefacts=self._build_artefact_scan_input(),
        )

    def preview(self):
        return pformat(
            ScanInput(
                hostname="",
                artefacts=self._build_artefact_scan_input(),
            ).dict()
        )

    def __str__(self):
        return self.name

    def get_artefacts_display(self):
        out = ""
        items = []

        for artefact in self.artefacts.all():
            artefact_str = artefact.artefact_name
            if artefact.knockout:
                artefact_str = (
                    f"<span class='line-through'>{artefact.artefact_name}</span>"
                )
            items.append(artefact_str)

        if self.inherited_artefacts:
            parent_items = []

            for artefact in self.inherited_artefacts:
                artefact_str = artefact.artefact_name
                if artefact.knockout:
                    artefact_str = (
                        f"<span class='line-through'>{artefact.artefact_name}</span>"
                    )
                parent_items.append(artefact_str)

            parent_str = ", ".join(parent_items)
            if items:
                parent_str += ", "
            out += f"<span class='text-gray-500'>{parent_str}</span>"

        out += ", ".join(items)

        return mark_safe(out)

    def get_artefact_groups_display(self):
        out = ""
        items = self.artefact_groups

        if self.inherited_artefact_groups:
            parent_items = [group for group in self.inherited_artefact_groups]
            parent_str = ", ".join(parent_items)
            if items:
                parent_str += ", "
            out += f"<span class='text-gray-500'>{parent_str}</span>"

        out += ", ".join(items)

        return mark_safe(out)


class ArtefactSpec(models.Model):

    artefact_name = models.CharField(
        max_length=255,
    )

    _scan_options = models.JSONField(
        default=dict,
    )

    knockout = models.BooleanField(
        help_text="If enabled, the specified artefact will NOT be included. This can "
        "be used to disable a specific artefact included through a group.",
        default=False,
    )

    scan_spec = models.ForeignKey(
        ScanSpec,
        on_delete=models.CASCADE,
        related_name="artefacts",
    )

    @property
    def is_valid_config(self) -> bool:
        return registry.get(self.artefact_name) is not None

    @property
    def scan_options(self) -> ArtefactScanOptions:
        options = self._scan_options if isinstance(self._scan_options, dict) else {}

        return ArtefactScanOptions(**options)
