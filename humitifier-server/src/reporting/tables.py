from django.urls.base import reverse

from main.easy_tables import BaseTable, ButtonColumn, CompoundColumn
from reporting.models import CostsScheme


class CostsSchemeTable(BaseTable):
    class Meta:
        model = CostsScheme
        columns = [
            "name",
            "cpu",
            "memory",
            "storage",
            "linux",
            "windows",
            "actions",
        ]

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Edit",
                button_class="btn btn-outline",
                url=lambda obj: reverse("reporting:costs_update", args=[obj.pk]),
            ),
        ],
    )
