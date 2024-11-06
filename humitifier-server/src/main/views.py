from urllib.parse import urlparse

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count
from django.shortcuts import resolve_url
from django.urls import reverse
from django.views.generic import ListView, RedirectView, TemplateView

from hosts.filters import AlertFilters
from hosts.models import Alert, Host

###
### Mixins
###

class SuperuserRequiredMixin(AccessMixin):
    """
    Require users to be superusers to access the view.
    """

    def dispatch(self, request, *args, **kwargs):
        """Call the appropriate handler if the user is a superuser"""
        if not request.user.is_superuser:
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def handle_no_permission(self):
        """Redirect to the login page if the user is not a superuser"""
        path = self.request.build_absolute_uri()
        resolved_login_url = resolve_url(self.get_login_url())
        # If the login url is the same scheme and net location then use the
        # path as the "next" url.
        login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
        current_scheme, current_netloc = urlparse(path)[:2]
        if (not login_scheme or login_scheme == current_scheme) and (
                not login_netloc or login_netloc == current_netloc
        ):
            path = self.request.get_full_path()
        return redirect_to_login(
            path,
            resolved_login_url,
            self.get_redirect_field_name(),
        )

class TableMixin:
    table_class = None

    def get_table_class(self):
        return self.table_class

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        table_class = self.get_table_class()

        context['table'] = table_class(
            data=context['object_list'],
            paginator=context['paginator'],
            page_object=context['page_obj'],
            ordering=context['ordering'],
            ordering_fields=context['ordering_fields'],
            page_sizes=context['page_sizes'],
        )

        return context

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

class HomeRedirectView(LoginRequiredMixin, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        # TODO: user preferences
        return reverse('hosts:list')


class DashboardView(LoginRequiredMixin, FilteredListView):
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

class UsersView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = 'main/not_implemented.html'

class AccessProfilesView(
    LoginRequiredMixin,
    SuperuserRequiredMixin,
    TemplateView
):
    template_name = 'main/not_implemented.html'

class OAuthApplicationsView(
    LoginRequiredMixin,
    SuperuserRequiredMixin,
    TemplateView
):
    template_name = 'main/not_implemented.html'