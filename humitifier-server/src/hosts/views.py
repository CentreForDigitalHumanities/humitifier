import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import Form
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.detail import BaseDetailView, \
    SingleObjectTemplateResponseMixin
from django.views.generic.edit import FormMixin

from main.views import FilteredListView, SuperuserRequiredMixin, TableMixin

from .filters import HostFilters
from .models import Host
from .tables import HostsTable


class HostsListView(LoginRequiredMixin, TableMixin, FilteredListView):
    model = Host
    table_class = HostsTable
    filterset_class = HostFilters
    paginate_by = 50
    template_name = 'hosts/list.html'
    ordering_fields = {
        'fqdn': 'Hostname',
        'os': 'Operating System',
        'department': 'Department',
        'contact': 'Contact',
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
        filtered_qs = filtered_qs.prefetch_related('alerts')

        return filtered_qs.distinct()

class HostDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'hosts/detail.html'

    LATEST_KEY = 'latest'

    def get_current_scan(self):
        return self.request.GET.get('scan', self.LATEST_KEY)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        host = Host.objects.get_for_user(self.request.user).get(fqdn=kwargs['fqdn'])
        scan_data = host.last_scan_cache
        current_scan = self.get_current_scan()
        current_scan_date = host.last_scan_date
        scan = None

        try:
            if current_scan != self.LATEST_KEY:
                scan = host.scans.get(created_at=current_scan)
                scan_data = scan.data
                current_scan_date = scan.created_at
        except (ValidationError, ObjectDoesNotExist):
            current_scan = self.LATEST_KEY

        is_latest_scan = (current_scan == self.LATEST_KEY or scan.created_at ==
                          host.last_scan_date)

        context['host'] = host
        context['scan_data'] = scan_data
        context['current_scan'] = current_scan
        context['current_scan_date'] = current_scan_date
        context['all_scans'] = host.scans.values_list('created_at', flat=True)
        context['is_latest_scan'] = is_latest_scan
        context['alerts'] = host.alerts.order_by('level')

        return context


class HostsRawDownloadView(LoginRequiredMixin, View):

    def get(self, request, fqdn):
        host = Host.objects.get_for_user(request.user).get(fqdn=fqdn)
        scan_data = host.last_scan_cache
        scan_date = host.last_scan_date

        requested_scan = request.GET.get('scan', None)
        if requested_scan:
            try:
                scan = host.scans.get(created_at=requested_scan)
                scan_data = scan.data
                scan_date = scan.created_at
            except (ObjectDoesNotExist, ValidationError):
                pass

        response = HttpResponse(json.dumps(scan_data, indent=4), content_type='application/json')
        response['Content-Disposition'] = (
            f'attachment; filename="scan_{fqdn}_{scan_date}.json"'
        )

        return response


class ArchiveHostView(
    LoginRequiredMixin,
    SuperuserRequiredMixin,
    SingleObjectTemplateResponseMixin,
    FormMixin,
    BaseDetailView
):
    model = Host
    form_class = Form
    template_name = 'hosts/archive.html'
    slug_field = 'fqdn'
    slug_url_kwarg = 'fqdn'

    def get_queryset(self):
        return Host.objects.get_for_user(self.request.user)

    def get_success_url(self):
        return reverse('hosts:detail', kwargs={'fqdn': self.object.fqdn})

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        success_url = self.get_success_url()

        if self.object.archived:
            self.object.archived = False
            self.object.archival_date = None
            self.object.save()
            self.object.regenerate_alerts()
        else:
            self.object.archived = True
            self.object.archival_date = timezone.now()
            self.object.save()
            self.object.alerts.all().delete()

        return HttpResponseRedirect(success_url)


class ExportView(LoginRequiredMixin, TemplateView):
    template_name = 'main/not_implemented.html'

class TasksView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = 'main/not_implemented.html'

class ScanProfilesView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = 'main/not_implemented.html'

class DataSourcesView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = 'main/not_implemented.html'