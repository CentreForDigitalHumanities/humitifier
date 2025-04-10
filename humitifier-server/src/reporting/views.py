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

            ##
            ## CPU
            ##
            context["chosen_num_cpu"] = data["num_cpu"]
            cpu_cost = data["num_cpu"] * costs_scheme.cpu
            context["cpu_cost"] = cpu_cost

            ##
            ## Memory
            ##
            context["chosen_memory"] = data["memory"]
            memory_cost = data["memory"] * costs_scheme.memory
            context["memory_cost"] = memory_cost

            if data["cpu_memory_bundle"]:
                # With bundling enabled, each CPU includes the cost of 2 Gb of memory
                max_bundled_memory = data["num_cpu"] * 2
                # If we chose less memory than the max included, we use the lower number
                actual_bundled_memory = min(data["memory"], max_bundled_memory)

                # Calculate the discount we need to apply
                bundled_memory_cost = actual_bundled_memory * costs_scheme.memory
            else:
                bundled_memory_cost = 0
                actual_bundled_memory = 0

            context["memory_bundle_discount"] = bundled_memory_cost
            context["actual_bundled_memory"] = actual_bundled_memory

            ##
            ## Storage
            ##
            # We have price per TB, but ask for GB
            storage_per_gig = costs_scheme.storage / 1024
            context["storage_per_gig"] = round(storage_per_gig, 4)

            context["chosen_storage"] = data["storage"]
            storage_cost = data["storage"] * storage_per_gig
            context["storage_cost"] = round(storage_cost, 4)

            context["redundant_storage"] = data["redundant_storage"]
            redundant_storage_cost = 0
            if data["redundant_storage"]:
                redundant_storage_cost = round(storage_cost, 4)

            ##
            ## OS
            ##
            chosen_os = data["os"]
            if chosen_os == "Linux":
                os_cost = costs_scheme.linux
            elif chosen_os == "Windows":
                os_cost = costs_scheme.windows
            else:
                os_cost = 0

            context["os_costs"] = os_cost

            ##
            ## Totals
            ##
            context["total_before_discount"] = cpu_cost + memory_cost + os_cost
            context["total_vm_costs"] = (
                context["total_before_discount"] - bundled_memory_cost
            )
            context["total_storage_costs"] = round(
                storage_cost + redundant_storage_cost, 2
            )
            context["total_costs"] = round(
                context["total_vm_costs"] + context["total_storage_costs"], 2
            )

        return context
