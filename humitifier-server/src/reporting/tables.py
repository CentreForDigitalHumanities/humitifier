from dataclasses import dataclass
from datetime import datetime

from django.urls.base import reverse

from main.easy_tables import (
    BaseTable,
    ButtonColumn,
    CompoundColumn,
    DateTimeColumn,
    MethodColumn,
    ValueColumn,
)
from reporting.models import CostsScheme
from reporting.utils import CostsBreakdown


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


class CostsOverviewTable(BaseTable):
    @dataclass
    class Data:
        fqdn: str
        costs_breakdown: CostsBreakdown
        scan_date: datetime

    class Meta:
        columns = []

    fqdn = ValueColumn(header="Host", value_attr="fqdn")

    date = DateTimeColumn(header="Date", value_attr="scan_date")

    num_cpus = MethodColumn(header="CPU", method_name="get_num_cpus")
    memory = MethodColumn(header="Memory", method_name="get_memory")
    storage = MethodColumn(header="Storage", method_name="get_storage")

    vm_costs = MethodColumn(header="VM Costs", method_name="get_vm_costs")
    storage_costs = MethodColumn(
        header="Storage Costs", method_name="get_storage_costs"
    )
    total_costs = MethodColumn(header="Total Costs", method_name="get_total_costs")

    @staticmethod
    def get_num_cpus(obj: "CostsOverviewTable.Data"):
        return obj.costs_breakdown.num_cpu

    @staticmethod
    def get_memory(obj: "CostsOverviewTable.Data"):
        return f"{obj.costs_breakdown.memory_size} GB"

    @staticmethod
    def get_storage(obj: "CostsOverviewTable.Data"):
        return f"{obj.costs_breakdown.storage_size} GB"

    @staticmethod
    def get_vm_costs(obj: "CostsOverviewTable.Data"):
        return round(obj.costs_breakdown.net_vm_costs, 2)

    @staticmethod
    def get_storage_costs(obj: "CostsOverviewTable.Data"):
        return round(obj.costs_breakdown.total_storage_costs, 2)

    @staticmethod
    def get_total_costs(obj: "CostsOverviewTable.Data"):
        return round(obj.costs_breakdown.total_costs, 2)
