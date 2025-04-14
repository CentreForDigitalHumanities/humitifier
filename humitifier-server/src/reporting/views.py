from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, FormView, UpdateView
from rest_framework.reverse import reverse_lazy

from hosts.models import Host, ScanData
from humitifier_common.artefacts import Hardware
from main.views import FilteredListView, SuperuserRequiredMixin, TableMixin
from reporting.filters import CostsSchemeFilters
from reporting.forms import CostCalculatorForm, CostsSchemeForm
from reporting.models import CostsScheme
from reporting.tables import CostsSchemeTable
from reporting.utils import calculate_costs


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
                redundant_storage=data["redundant_storage"],
                bundle_memory=data["cpu_memory_bundle"],
            )

        return context
