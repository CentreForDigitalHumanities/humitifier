from django.urls import reverse
from django.utils.safestring import mark_safe

from main.easy_tables import (
    BaseTable,
    ButtonColumn,
    CompoundColumn,
    MethodColumn,
    TemplatedColumn,
)
from scanning.models import ScanSpec


class ScanSpecTable(BaseTable):
    class Meta:
        model = ScanSpec
        columns = [
            "name",
            "parent",
            "artefact_groups",
            "artefacts",
            "actions",
        ]
        no_data_message = "No scan specifications found. Please check your filters."
        no_data_message_wild_wasteland = mark_safe(
            "<a href='https://www.youtube.com/watch?v=M-Vfte0lOsA' "
            "target='_blank'>Nothing on scans Captain</a>"
        )

    artefacts = MethodColumn("Individual artefacts", method_name="get_artefacts")
    artefact_groups = MethodColumn("Artefact groups", method_name="get_artefact_groups")

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Edit",
                button_class="btn light:btn-primary dark:btn-outline mr-2",
                url=lambda obj: reverse("scanning:edit_scan_spec", args=[obj.pk]),
            ),
            ButtonColumn(
                text="Delete",
                button_class="btn btn-danger mr-2",
                url=lambda obj: reverse("scanning:delete_scan_spec", args=[obj.pk]),
            ),
            TemplatedColumn(
                "Preview",
                template_name="scanning/scanspec_list_scaninput_preview.html",
            ),
        ],
    )

    @classmethod
    def get_artefacts(cls, obj: ScanSpec):
        return obj.get_artefacts_display()

    @classmethod
    def get_artefact_groups(cls, obj: ScanSpec):
        return obj.get_artefact_groups_display()
