from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView

from main.views import FilteredListView, SuperuserRequiredMixin, TableMixin

from .filters import IPInfoFilters, NetworkFilters
from .forms import NetworkForm
from .models import IPInfo, Network
from .tables import IPInfoTable, NetworksTable


class IPInfoListView(
    LoginRequiredMixin, SuperuserRequiredMixin, TableMixin, FilteredListView
):
    model = IPInfo
    table_class = IPInfoTable
    filterset_class = IPInfoFilters
    paginate_by = 50
    template_name = "network/ip_list.html"
    ordering = "ip_address"
    ordering_fields = {
        "ip_address": "IP",
        "active": "Active",
    }


class NetworkListView(
    LoginRequiredMixin, SuperuserRequiredMixin, TableMixin, FilteredListView
):
    model = Network
    table_class = NetworksTable
    filterset_class = NetworkFilters
    paginate_by = 50
    template_name = "network/network_list.html"
    ordering = "name"
    ordering_fields = {
        "name": "Name",
        "vlan": "VLAN",
        "cidr_range": "CIDR Range",
    }


class NetworkCreateView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, CreateView
):
    model = Network
    form_class = NetworkForm
    template_name = "network/network_form.html"
    success_url = reverse_lazy("network:list")
    success_message = "Network created successfully."


class NetworkUpdateView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = Network
    form_class = NetworkForm
    template_name = "network/network_form.html"
    success_url = reverse_lazy("network:list")
    success_message = "Network updated successfully."


class NetworkDeleteView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, DeleteView
):
    model = Network
    template_name = "network/network_confirm_delete.html"
    success_url = reverse_lazy("network:list")
    success_message = "Network deleted successfully."
