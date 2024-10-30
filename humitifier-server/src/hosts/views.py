import json

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView

from main.views import FilteredListView

from .filters import HostFilters
from .models import Host

# Create your views here.

class HostsListView(FilteredListView):
    model = Host
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

class HostDetailView(TemplateView):
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


class HostsRawDownloadView(View):

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


class ExportView(TemplateView):
    template_name = 'main/not_implemented.html'

class TasksView(TemplateView):
    template_name = 'main/not_implemented.html'

class ScanProfilesView(TemplateView):
    template_name = 'main/not_implemented.html'

class DataSourcesView(TemplateView):
    template_name = 'main/not_implemented.html'