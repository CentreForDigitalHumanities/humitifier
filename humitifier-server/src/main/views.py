from urllib.parse import urlparse

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count
from django.forms import Form
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.urls import reverse
from django.views.generic import (
    DeleteView,
    ListView,
    RedirectView,
    TemplateView,
    UpdateView,
)
from django.views.generic.detail import (
    BaseDetailView,
    SingleObjectTemplateResponseMixin,
)
from django.views.generic.edit import CreateView, FormMixin
from rest_framework.reverse import reverse_lazy

from hosts.filters import AlertFilters
from hosts.models import Alert, Host
from main.filters import AccessProfileFilters, UserFilters
from main.forms import (
    AccessProfileForm,
    CreateSolisUserForm,
    SetPasswordForm,
    UserForm,
    UserProfileForm,
)
from main.models import AccessProfile, HomeOptions, User
from main.tables import AccessProfilesTable, UsersTable


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

        context["table"] = table_class(
            data=context["object_list"],
            paginator=context["paginator"],
            page_object=context["page_obj"],
            filterset=context["filterset"],
            ordering=context["ordering"],
            ordering_fields=context["ordering_fields"],
            page_sizes=context["page_sizes"],
            request=self.request,
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

        context["filterset"] = self.filterset
        context["page_sizes"] = self.page_sizes
        context["ordering"] = self.get_ordering()
        context["ordering_fields"] = self.get_ordering_fields()

        return context

    def get_paginate_by(self, queryset):
        # Never paginate if we don't have a default page size
        if self.paginate_by is None:
            return None

        return self.request.GET.get("page_size", self.paginate_by)

    def get_ordering(self):
        # Never order if we don't have ordering fields
        if not self.ordering_fields:
            return None

        ordering = self.request.GET.get("ordering")
        if ordering and ordering.lstrip("-") in self.ordering_fields:
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
        if self.request.user.default_home == HomeOptions.DASHBOARD:
            return reverse("main:dashboard")
        return reverse("hosts:list")


class DashboardView(LoginRequiredMixin, FilteredListView):
    model = Alert
    filterset_class = AlertFilters
    paginate_by = 20
    template_name = "main/dashboard.html"
    ordering_fields = {
        "host": "Hostname",
        "level": "Alert level",
        "type": "Alert type",
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
        filtered_qs = filtered_qs.select_related("host")

        return filtered_qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["os_stats"] = (
            Host.objects.get_for_user(self.request.user)
            .values("os")
            .annotate(count=Count("os"))
        )
        context["department_stats"] = (
            Host.objects.get_for_user(self.request.user)
            .values("department")
            .annotate(count=Count("department"))
        )

        return context


class UsersView(
    LoginRequiredMixin, SuperuserRequiredMixin, TableMixin, FilteredListView
):
    model = User
    table_class = UsersTable
    filterset_class = UserFilters
    paginate_by = 50
    template_name = "main/user_list.html"
    ordering = "username"
    ordering_fields = {
        "username": "Username",
        "email": "Email",
        "first_name": "First name",
        "last_name": "Last name",
        "access_profile": "Access profile",
    }

    def get_queryset(self):
        qs = super().get_queryset()

        return qs.prefetch_related("access_profiles")


class DeActivateUserView(
    LoginRequiredMixin,
    SuperuserRequiredMixin,
    SingleObjectTemplateResponseMixin,
    FormMixin,
    BaseDetailView,
):
    model = User
    form_class = Form
    template_name = "main/user_deactivate.html"

    def get_success_url(self):
        return reverse("main:users")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        success_url = self.get_success_url()

        self.object.is_active = not self.object.is_active
        self.object.save()

        return HttpResponseRedirect(success_url)


class CreateUserView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = User
    form_class = UserForm
    success_url = reverse_lazy("main:users")
    context_object_name = "form_user"  # needed to keep the view from
    # overriding the user object in the context


class CreateSolisUserView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = User
    form_class = CreateSolisUserForm
    success_url = reverse_lazy("main:users")
    context_object_name = "form_user"  # needed to keep the view from
    # overriding the user object in the context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["is_solis"] = True

        return context

    def form_valid(self, form):
        form.instance.is_local_account = False
        return super().form_valid(form)


class EditUserView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    success_url = reverse_lazy("main:users")
    context_object_name = "form_user"  # needed to keep the view from
    # overriding the user object in the context


class UserProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    success_url = reverse_lazy("main:user_profile")
    template_name = "main/user_profile.html"
    context_object_name = "form_user"  # needed to keep the view from
    # overriding the user object in the context

    def get_object(self, queryset=None):
        return self.request.user


class SetPasswordView(
    LoginRequiredMixin,
    UpdateView,
):
    model = User
    form_class = SetPasswordForm
    template_name = "main/user_set_password_form.html"
    success_url = reverse_lazy("main:users")
    context_object_name = "form_user"  # needed to keep the view from
    # overriding the user object in the context

    def dispatch(self, request, *args, **kwargs):
        requested_user = self.get_object()

        # Only local accounts can have their password changed
        if not requested_user.is_local_account:
            return self.handle_no_permission()

        # Only superusers can change the password of other users
        if not request.user.is_superuser and request.user != requested_user:
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class AccessProfilesView(
    LoginRequiredMixin, SuperuserRequiredMixin, TableMixin, FilteredListView
):
    model = AccessProfile
    table_class = AccessProfilesTable
    filterset_class = AccessProfileFilters
    paginate_by = 50
    template_name = "main/accessprofile_list.html"
    ordering = "name"
    ordering_fields = {
        "name": "name",
    }


class CreateAccessProfileView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = AccessProfile
    form_class = AccessProfileForm
    success_url = reverse_lazy("main:access_profiles")


class EditAccessProfileView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = AccessProfile
    form_class = AccessProfileForm
    success_url = reverse_lazy("main:access_profiles")


class DeleteAccessProfileView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = AccessProfile
    success_url = reverse_lazy("main:access_profiles")
