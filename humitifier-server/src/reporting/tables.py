from dataclasses import dataclass
from datetime import datetime

from django.urls.base import reverse

from main.easy_tables import (
    BaseTable,
    ButtonColumn,
    CompoundColumn,
    DateColumn,
    DateTimeColumn,
    MethodColumn,
    ValueColumn,
)
from reporting.models import CostsScheme, GeneratedReport
from reporting.utils import CostsBreakdown


class GeneratedReportTable(BaseTable):
    class Meta:
        model = GeneratedReport
        columns = [
            "filename",
            "status_display",
            "created_at",
            "customers_display",
            "costs_schemes",
            "start_date",
            "end_date",
            "actions",
        ]

    status_display = MethodColumn("Status", method_name="get_status_display")

    customers_display = MethodColumn("Customers", method_name="get_customers_display")

    created_at = DateTimeColumn(header="Created", value_attr="created_at")
    start_date = DateColumn(header="Start Date", value_attr="start_date")
    end_date = DateColumn(header="End Date", value_attr="end_date")

    costs_schemes = MethodColumn("Costs Schemes", method_name="get_costs_schemes")

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Download",
                button_class="btn btn-primary",
                url=lambda obj: reverse("reporting:report_download", args=[obj.pk]),
                show_check_function=lambda obj: obj.status == GeneratedReport.Status.COMPLETED,
            ),
            ButtonColumn(
                text="Rerun",
                button_class="btn btn-secondary",
                url=lambda obj: reverse("reporting:report_rerun", args=[obj.pk]),
            ),
            ButtonColumn(
                text="Delete",
                button_class="btn btn-danger",
                url=lambda obj: reverse("reporting:report_delete", args=[obj.pk]),
            ),
        ],
    )

    @staticmethod
    def get_status_display(obj: GeneratedReport):
        if obj.status == GeneratedReport.Status.PENDING:
            return "⏳ Generating…"
        elif obj.status == GeneratedReport.Status.COMPLETED:
            return "✓ Ready"
        elif obj.status == GeneratedReport.Status.FAILED:
            return "✗ Failed"
        return obj.status

    @staticmethod
    def get_customers_display(obj: GeneratedReport):
        if len(obj.customers) == 0:
            return "All"
        return ", ".join([customer for customer in obj.customers])

    @staticmethod
    def get_costs_schemes(obj: GeneratedReport):
        return ", ".join([str(scheme) for scheme in obj.costs_schemes.all()])


class CostsSchemeTable(BaseTable):
    class Meta:
        model = CostsScheme
        columns = [
            "name",
            "platform",
            "cpu",
            "memory",
            "storage",
            "linux",
            "windows",
            "management",
            "redundant_storage",
            "actions",
        ]

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Edit",
                button_class="btn btn-secondary",
                url=lambda obj: reverse("reporting:costs_update", args=[obj.pk]),
            ),
            ButtonColumn(
                text="Delete",
                button_class="btn btn-danger",
                url=lambda obj: reverse("reporting:costs_delete", args=[obj.pk]),
            ),
        ],
    )


class CostsOverviewTable(BaseTable):
    @dataclass
    class Data:
        fqdn: str
        platform: str
        costs_breakdown: CostsBreakdown
        scan_date: datetime

    class Meta:
        columns = []

    fqdn = ValueColumn(header="Host", value_attr="fqdn")

    platform = ValueColumn(header="Platform", value_attr="platform")

    date = DateTimeColumn(header="Date", value_attr="scan_date")

    num_cpus = MethodColumn(header="CPU", method_name="get_num_cpus")
    memory = MethodColumn(header="Memory", method_name="get_memory")
    storage = MethodColumn(header="Storage", method_name="get_storage")

    vm_costs = MethodColumn(header="VM Costs", method_name="get_vm_costs")
    storage_costs = MethodColumn(
        header="Storage Costs", method_name="get_storage_costs"
    )
    management_costs = MethodColumn(
        header="Support Costs", method_name="get_management_costs"
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
        return round(obj.costs_breakdown.vm_costs, 2)

    @staticmethod
    def get_storage_costs(obj: "CostsOverviewTable.Data"):
        return round(obj.costs_breakdown.total_storage_costs, 2)

    @staticmethod
    def get_management_costs(obj: "CostsOverviewTable.Data"):
        return obj.costs_breakdown.management

    @staticmethod
    def get_total_costs(obj: "CostsOverviewTable.Data"):
        return round(obj.costs_breakdown.total_costs, 2)
