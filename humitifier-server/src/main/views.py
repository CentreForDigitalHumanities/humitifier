from django.db.models import Count
from django.urls import reverse
from django.views.generic import ListView, RedirectView, TemplateView

from hosts.filters import AlertFilters
from hosts.models import Alert, AlertType, Host


###
### Generic views
###

class FilteredListView(ListView):
    filterset_class = None
    page_sizes = [10, 25, 50, 100, 1000]
    ordering_fields = {}

    def get_queryset(self):
        queryset = super().get_queryset()

        self.filterset = self.filterset_class(self.request.GET, queryset=queryset)

        return self.filterset.qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['filterset'] = self.filterset
        context['page_sizes'] = self.page_sizes
        context['ordering'] = self.get_ordering()
        context['ordering_fields'] = self.get_ordering_fields()

        return context

    def get_paginate_by(self, queryset):
        # Never paginate if we don't have a default page size
        if self.paginate_by is None:
            return None

        return self.request.GET.get('page_size', self.paginate_by)

    def get_ordering(self):
        # Never order if we don't have ordering fields
        if not self.ordering_fields:
            return None

        ordering = self.request.GET.get('ordering')
        if ordering and ordering.lstrip('-') in self.ordering_fields:
            return ordering

        if self.ordering:
            return self.ordering

        if self.model._meta.ordering:
            return self.model._meta.ordering[0]

        return None

    def get_ordering_fields(self):
        ordering_fields = {}

        for field, label in self.ordering_fields.items():
            ordering_fields[field] = f"{label} ↑"
            ordering_fields[f"-{field}"] = f"{label} ↓"

        return ordering_fields


###
### Page views
###

class HomeRedirectView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        # TODO: user preferences
        return reverse('hosts:list')


class DashboardView(FilteredListView):
    model = Alert
    filterset_class = AlertFilters
    paginate_by = 20
    template_name = 'main/dashboard.html'
    ordering_fields = {
        'host': 'Hostname',
        'level': 'Alert level',
        'type': 'Alert type',
    }

    def get_queryset(self):
        queryset = Alert.objects.get_for_user(self.request.user)

        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        self.filterset = self.filterset_class(self.request.GET, queryset=queryset)

        filtered_qs = self.filterset.qs
        # We're going to need the data for the alerts in the template
        # So, let's prefetch it here for _performance_
        filtered_qs = filtered_qs.select_related('host')

        return filtered_qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['os_stats'] = Host.objects.get_for_user(
            self.request.user
        ).values(
            'os'
        ).annotate(
            count=Count('os')
        )
        context['department_stats'] = Host.objects.get_for_user(
            self.request.user
        ).values(
            'department'
        ).annotate(
            count=Count('department')
        )

        return context

class UsersView(TemplateView):
    template_name = 'main/not_implemented.html'

class AccessProfilesView(TemplateView):
    template_name = 'main/not_implemented.html'

class OAuthApplicationsView(TemplateView):
    template_name = 'main/not_implemented.html'