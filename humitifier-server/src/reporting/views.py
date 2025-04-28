from decimal import Decimal
from typing import Tuple

from celery.bin.worker import Hostname
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    TemplateView,
    UpdateView,
)
from rest_framework.reverse import reverse_lazy

from hosts.models import Host, ScanData
from humitifier_common.artefacts import Hardware, HostnameCtl
from main.views import FilteredListView, SuperuserRequiredMixin, TableMixin
from reporting.filters import CostsSchemeFilters
from reporting.forms import (
    CostCalculatorForm,
    CostsOverviewForm,
    CostsReportForm,
    CostsSchemeForm,
)
from reporting.models import CostsScheme
from reporting.tables import CostsOverviewTable, CostsSchemeTable
from reporting.utils import calculate_costs, calculate_from_hardware_artefact
from reporting.utils.costs_excel_export import create_cost_excel
from reporting.utils.get_server_hardware import get_server_hardware


class CostsSchemeListView(
    LoginRequiredMixin, SuperuserRequiredMixin, TableMixin, FilteredListView
):
    model = CostsScheme
    table_class = CostsSchemeTable
    filterset_class = CostsSchemeFilters
    paginate_by = 50
    ordering = "name"
    ordering_fields = {
        "name": "Name",
        "cpu": "Price per CPU",
        "memory": "Price per 1Gb memory",
        "storage": "Price per 1Tb storage",
        "linux": "Price for Linux",
        "windows": "Price for Windows",
    }


class CostsSchemeCreateView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, CreateView
):
    model = CostsScheme
    form_class = CostsSchemeForm
    success_message = "Costs scheme created successfully"
    success_url = reverse_lazy("reporting:costs_list")


class CostsSchemeUpdateView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = CostsScheme
    form_class = CostsSchemeForm
    success_message = "Costs scheme updated successfully"
    success_url = reverse_lazy("reporting:costs_list")


class CostsSchemeDeleteView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, DeleteView
):
    model = CostsScheme
    success_url = reverse_lazy("reporting:costs_list")
    success_message = "Costs scheme deleted"


class CostCalculatorView(LoginRequiredMixin, FormView):
    form_class = CostCalculatorForm
    template_name = "reporting/cost_calculator.html"

    def form_valid(self, form):
        return self.render_to_response(self.get_context_data(form_valid=True))

    def get_initial(self):
        initial = super().get_initial()

        if "fqdn" in self.request.GET:
            try:
                host = Host.objects.get(fqdn=self.request.GET["fqdn"])
            except Host.DoesNotExist:
                return initial

            scan_obj: ScanData = host.get_scan_object()
            if not scan_obj.version >= 2:
                return initial

            if Hardware.__artefact_name__ not in scan_obj.parsed_data.facts:
                return initial

            if scan_obj.parsed_data.facts[Hardware.__artefact_name__] is None:
                return initial

            hardware_info: Hardware = scan_obj.parsed_data.facts[
                Hardware.__artefact_name__
            ]

            initial["num_cpu"] = hardware_info.num_cpus

            total_memory = sum([memrange.size for memrange in hardware_info.memory])
            total_memory = total_memory / 1024 / 1024 / 1024
            initial["memory"] = round(total_memory)

            disks = []
            for block_device in hardware_info.block_devices:
                if block_device.type == "disk":
                    disks.append(block_device)

            total_disk_space = 0
            for disk in disks:
                size = disk.size[:-1]
                unit = disk.size[-1]

                try:
                    size = int(size)
                except ValueError:
                    continue

                if unit == "M":
                    size = size / 1024

                total_disk_space += size

            initial["storage"] = total_disk_space

        return initial

    def get_context_data(self, form_valid=False, **kwargs):
        context = super().get_context_data(**kwargs)

        if form_valid:
            form = context["form"]
            form.full_clean()

            data = form.cleaned_data

            costs_scheme: CostsScheme = data["costs_scheme"]
            context["costs_scheme"] = costs_scheme

            context["costs"] = calculate_costs(
                num_cpu=data["num_cpu"],
                memory_in_gb=data["memory"],
                storage_in_gb=data["storage"],
                os=data["os"].lower(),
                costs_scheme=costs_scheme,
            )

        return context


class CostsReportView(SuperuserRequiredMixin, LoginRequiredMixin, FormView):
    form_class = CostsReportForm
    template_name = "reporting/costs_report.html"

    def form_valid(self, form):
        costs_scheme = form.cleaned_data["costs_scheme"]
        customers = form.cleaned_data["customers"]
        filename = form.cleaned_data["filename"]

        file_data = create_cost_excel(costs_scheme, filename, customers)

        response = HttpResponse(
            file_data.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response


class CostsOverviewView(LoginRequiredMixin, FormView):
    form_class = CostsOverviewForm
    template_name = "reporting/costs_overview.html"

    def form_valid(self, form):
        return self.render_to_response(self.get_context_data(form_valid=True))

    def get_context_data(self, form_valid=False, **kwargs):
        context = super().get_context_data(**kwargs)

        if form_valid:
            form = context["form"]
            form.full_clean()

            form_data = form.cleaned_data

            (
                total_vm_costs,
                total_storage,
                total_storage_costs,
                total_management_costs,
                total_costs,
                data,
            ) = self.get_data(
                customer=form_data.get("customer", None),
                costs_scheme=form_data.get("costs_scheme"),
            )

            context["total_vm_costs"] = total_vm_costs
            context["total_storage_usage"] = total_storage
            context["total_storage_costs"] = total_storage_costs
            context["total_management_costs"] = total_management_costs
            context["total_costs"] = total_costs

            context["table"] = CostsOverviewTable(
                data=data,
                request=self.request,
            )

        return context

    def get_data(
        self,
        customer,
        costs_scheme,
    ) -> Tuple[
        Decimal, Decimal, Decimal, Decimal, Decimal, list[CostsOverviewTable.Data]
    ]:
        hosts = Host.objects.get_for_user(self.request.user)
        if customer:
            hosts = hosts.filter(customer=customer)

        servers = get_server_hardware(hosts)

        data = []
        total_vm_costs = Decimal("0")
        total_storage = Decimal("0")
        total_storage_costs = Decimal("0")
        total_management_costs = Decimal("0")
        total_costs = Decimal("0")

        for server in servers:
            cost_breakdown = calculate_from_hardware_artefact(
                server.hardware,
                costs_scheme,
            )

            total_vm_costs += cost_breakdown.vm_costs
            total_storage += cost_breakdown.total_storage_usage
            total_storage_costs += cost_breakdown.total_storage_costs
            total_management_costs += cost_breakdown.management
            total_costs += cost_breakdown.total_costs

            data.append(
                CostsOverviewTable.Data(
                    fqdn=server.hostname,
                    scan_date=server.scan_date,
                    costs_breakdown=cost_breakdown,
                )
            )

        return (
            total_vm_costs,
            total_storage,
            total_storage_costs,
            total_management_costs,
            total_costs,
            data,
        )
