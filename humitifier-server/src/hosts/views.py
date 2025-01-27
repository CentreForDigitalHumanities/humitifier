import csv
import json
from datetime import datetime
from io import StringIO

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import Form
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView, UpdateView
from django.views.generic.detail import (
    BaseDetailView,
    SingleObjectTemplateResponseMixin,
)
from django.views.generic.edit import CreateView, FormMixin
from rest_framework.reverse import reverse_lazy

from main.views import FilteredListView, SuperuserRequiredMixin, TableMixin

from .filters import DataSourceFilters, HostFilters
from .forms import DataSourceForm
from .models import DataSource, Host
from .scan_visualizers import get_scan_visualizer
from .tables import DataSourcesTable, HostsTable

##
## Host views
##


class HostsListView(LoginRequiredMixin, TableMixin, FilteredListView):
    model = Host
    table_class = HostsTable
    filterset_class = HostFilters
    paginate_by = 50
    template_name = "hosts/host_list.html"
    ordering_fields = {
        "fqdn": "Hostname",
        "os": "Operating System",
        "department": "Department",
        "customer": "Customer",
        "contact": "Contact",
        "last_scan_date": "Last Scan Date",
    }

    def get_queryset(self):
        queryset = Host.objects.get_for_user(self.request.user)

        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        self.filterset = self.filterset_class(self.request.GET, queryset=queryset)

        filtered_qs = self.filterset.qs
        # We're going to need the data for the alerts in the template
        # So, let's prefetch it here for _performance_
        filtered_qs = filtered_qs.prefetch_related("alerts")

        return filtered_qs.distinct()


class HostExportView(LoginRequiredMixin, FilteredListView):
    model = Host
    filterset_class = HostFilters
    template_name = "hosts/host_export.html"

    def get_queryset(self):
        queryset = Host.objects.get_for_user(self.request.user)

        data = self.request.GET.copy()
        data.update(self.request.POST)

        self.filterset = self.filterset_class(data, queryset=queryset)

        return self.filterset.qs.distinct()

    def post(self, request, *args, **kwargs):
        content = ""
        content_type = "text/plain"
        file_name = datetime.now().isoformat()
        file_name = f"humitifier_export_{file_name}"

        if "csv" in request.POST:
            content = self._get_csv()
            content_type = "text/csv"
            file_name = f"{file_name}.csv"
        elif "host-list" in request.POST:
            content = self._get_host_list()
            file_name = f"{file_name}.txt"

        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"',
        }

        return HttpResponse(content, content_type=content_type, headers=headers)

    def _get_csv(self):
        buffer = StringIO()

        csv_file = csv.DictWriter(
            f=buffer,
            fieldnames={
                "fqdn": "Hostname",
                "os": "Operating System",
                "department": "Department",
                "customer": "Customer",
                "contact": "Contact",
                "created_at": "Created At",
                "archived": "Archived",
                "archival_date": "Archival Date",
                "last_scan_date": "Last Scan Date",
            },
        )
        csv_file.writeheader()

        for host in self.get_queryset():
            csv_file.writerow(
                {
                    "fqdn": host.fqdn,
                    "os": host.os,
                    "department": host.department,
                    "customer": host.customer,
                    "contact": host.contact,
                    "created_at": host.created_at,
                    "archived": host.archived,
                    "archival_date": host.archival_date,
                    "last_scan_date": host.last_scan_date,
                }
            )

        return buffer.getvalue()

    def _get_host_list(self):
        buffer = StringIO()

        for host in self.get_queryset():
            buffer.write(f"{host.fqdn}\n")

        return buffer.getvalue()


class HostDetailView(LoginRequiredMixin, TemplateView):
    template_name = "hosts/host_detail.html"

    LATEST_KEY = "latest"

    def get_current_scan(self):
        return self.request.GET.get("scan", self.LATEST_KEY)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        host = Host.objects.get_for_user(self.request.user).get(fqdn=kwargs["fqdn"])
        scan_data = host.get_scan_object()
        current_scan = self.get_current_scan()
        current_scan_date = host.last_scan_date
        scan = None

        try:
            if current_scan != self.LATEST_KEY:
                scan = host.scans.get(created_at=current_scan)
                scan_data = scan.get_scan_object()
                current_scan_date = scan.created_at
        except (ValidationError, ObjectDoesNotExist):
            current_scan = self.LATEST_KEY

        is_latest_scan = (
            current_scan == self.LATEST_KEY or scan.created_at == host.last_scan_date
        )

        visualizer_context = {
            "current_scan": current_scan,
            "current_scan_date": current_scan_date,
            "all_scans": host.scans.values_list("created_at", flat=True),
            "is_latest_scan": is_latest_scan,
            "alerts": host.alerts.order_by("level"),
        }

        visualizer = get_scan_visualizer(host, scan_data, visualizer_context)
        visualizer.request = self.request

        context["host"] = host
        context["scan_visualizer"] = visualizer

        return context


class HostsRawDownloadView(LoginRequiredMixin, View):

    def get(self, request, fqdn):
        host = Host.objects.get_for_user(request.user).get(fqdn=fqdn)
        scan_data = host.last_scan_cache
        scan_date = host.last_scan_date

        requested_scan = request.GET.get("scan", None)
        if requested_scan:
            try:
                scan = host.scans.get(created_at=requested_scan)
                scan_data = scan.data
                scan_date = scan.created_at
            except (ObjectDoesNotExist, ValidationError):
                pass

        response = HttpResponse(
            json.dumps(scan_data, indent=4), content_type="application/json"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="scan_{fqdn}_{scan_date}.json"'
        )

        return response


class ArchiveHostView(
    LoginRequiredMixin,
    SuperuserRequiredMixin,
    SingleObjectTemplateResponseMixin,
    FormMixin,
    BaseDetailView,
):
    model = Host
    form_class = Form
    template_name = "hosts/host_archive.html"
    slug_field = "fqdn"
    slug_url_kwarg = "fqdn"

    def get_queryset(self):
        return Host.objects.get_for_user(self.request.user)

    def get_success_url(self):
        return reverse("hosts:detail", kwargs={"fqdn": self.object.fqdn})

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        success_url = self.get_success_url()

        self.object.switch_archived_status()

        return HttpResponseRedirect(success_url)


class TasksView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = "main/not_implemented.html"


class ScanProfilesView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = "main/not_implemented.html"


##
## Data source views
##


class DataSourcesView(LoginRequiredMixin, TableMixin, FilteredListView):
    template_name = "hosts/datasource_list.html"
    model = DataSource
    table_class = DataSourcesTable
    filterset_class = DataSourceFilters
    ordering_fields = {
        "name": "Name",
        "source_type": "Source Type",
    }
    paginate_by = 10


class DataSourceCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    template_name = "hosts/datasource_form.html"
    model = DataSource
    form_class = DataSourceForm
    success_url = reverse_lazy("hosts:data_sources")


class DataSourceEditView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    template_name = "hosts/datasource_form.html"
    model = DataSource
    form_class = DataSourceForm
    success_url = reverse_lazy("hosts:data_sources")
