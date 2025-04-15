from datetime import datetime
from urllib.parse import urlparse

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.messages.views import SuccessMessageMixin
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
    DetailView,
    SingleObjectTemplateResponseMixin,
)
from django.views.generic.edit import CreateView, FormMixin
from django_celery_beat.admin import PeriodicTaskForm
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult
from rest_framework.reverse import reverse_lazy

from alerting.models import Alert, AlertSeverity
from humitifier_server import celery_app
from alerting.filters import AlertFilters
from hosts.models import Host
from main.filters import (
    AccessProfileFilters,
    PeriodicTaskFilters,
    TaskResultFilters,
    UserFilters,
)
from main.forms import (
    AccessProfileForm,
    CreateSolisUserForm,
    SetPasswordForm,
    UserForm,
    UserProfileForm,
)
from main.models import AccessProfile, HomeOptions, User
from main.tables import (
    AccessProfilesTable,
    PeriodicTaskTable,
    TaskResultTable,
    UsersTable,
)


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

#
# General views
#


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
        "severity": "Alert severity",
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

    def get_alert_stats(self):
        num_critical = Host.objects.filter(
            alerts__severity=AlertSeverity.CRITICAL,
            archived=False,
        ).count()
        num_warning = (
            Host.objects.filter(
                alerts__severity=AlertSeverity.WARNING,
                archived=False,
            )
            .exclude(
                alerts__severity=AlertSeverity.CRITICAL,
            )
            .count()
        )
        num_info = (
            Host.objects.filter(
                alerts__severity=AlertSeverity.INFO,
                archived=False,
            )
            .exclude(
                alerts__severity__in=[AlertSeverity.WARNING, AlertSeverity.CRITICAL],
            )
            .count()
        )
        num_fine = Host.objects.filter(alerts__isnull=True, archived=False).count()

        return num_critical, num_warning, num_info, num_fine

    def get_alert_count_by_message(self):
        return (
            Alert.objects.get_for_user(self.request.user)
            .values("short_message")
            .annotate(count=Count("id"))
        )

    def get_host_count_by_otap(self):
        return (
            Host.objects.get_for_user(self.request.user)
            .filter(archived=False)
            .values("otap_stage")
            .annotate(count=Count("id"))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["os_stats"] = (
            Host.objects.get_for_user(self.request.user)
            .filter(archived=False)
            .values("os")
            .annotate(count=Count("os"))
        )
        context["customer_stats"] = (
            Host.objects.get_for_user(self.request.user)
            .filter(archived=False)
            .values("customer")
            .annotate(count=Count("customer"))
        )

        num_critical, num_warning, num_info, num_fine = self.get_alert_stats()
        context["alert_message_counts"] = self.get_alert_count_by_message()
        context["otap_counts"] = self.get_host_count_by_otap()

        context["num_critical"] = num_critical
        context["num_warning"] = num_warning
        context["num_info"] = num_info
        context["num_fine"] = num_fine

        return context


class VersionView(LoginRequiredMixin, TemplateView):
    template_name = "main/version.html"


#
# User management views
#


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
    SuccessMessageMixin,
    FormMixin,
    BaseDetailView,
):
    model = User
    form_class = Form
    template_name = "main/user_deactivate.html"
    success_message = "User deactivated"

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


class CreateUserView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, CreateView
):
    model = User
    form_class = UserForm
    success_url = reverse_lazy("main:users")
    success_message = "User created"
    context_object_name = "form_user"  # needed to keep the view from
    # overriding the user object in the context


class CreateSolisUserView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, CreateView
):
    model = User
    form_class = CreateSolisUserForm
    success_url = reverse_lazy("main:users")
    success_message = "User created"
    context_object_name = "form_user"  # needed to keep the view from
    # overriding the user object in the context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["is_solis"] = True

        return context

    def form_valid(self, form):
        form.instance.is_local_account = False
        return super().form_valid(form)


class EditUserView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = User
    form_class = UserForm
    success_url = reverse_lazy("main:users")
    success_message = "User edited"
    context_object_name = "form_user"  # needed to keep the view from
    # overriding the user object in the context


class UserProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    success_url = reverse_lazy("main:user_profile")
    template_name = "main/user_profile.html"
    success_message = "Profile updated"
    context_object_name = "form_user"  # needed to keep the view from
    # overriding the user object in the context

    def get_object(self, queryset=None):
        return self.request.user


class SetPasswordView(
    LoginRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = User
    form_class = SetPasswordForm
    template_name = "main/user_set_password_form.html"
    success_url = reverse_lazy("main:users")
    success_message = "Password updated"
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


#
# Access profile views
#


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


class CreateAccessProfileView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, CreateView
):
    model = AccessProfile
    form_class = AccessProfileForm
    success_url = reverse_lazy("main:access_profiles")
    success_message = "Access profile created"


class EditAccessProfileView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = AccessProfile
    form_class = AccessProfileForm
    success_url = reverse_lazy("main:access_profiles")
    success_message = "Access profile updated"


class DeleteAccessProfileView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, DeleteView
):
    model = AccessProfile
    success_url = reverse_lazy("main:access_profiles")
    success_message = "Access profile deleted"


#
# Celery views
#


class CurrentTasksView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = "main/currenttasks_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        inspector = celery_app.control.inspect()

        active_tasks = inspector.active()
        scheduled_tasks = inspector.scheduled()

        active_tasks = self.transform_tasks(active_tasks, "SCHEDULED")
        scheduled_tasks = self.transform_tasks(scheduled_tasks, "ACTIVE")

        context["current_tasks"] = active_tasks
        context["scheduled_tasks"] = scheduled_tasks

        return context

    def transform_tasks(self, tasks_data, _type):
        output = []
        for _, tasks in tasks_data.items():
            for task in tasks:
                task["type"] = _type
                if "time_start" in task and isinstance(
                    task["time_start"], (int, float)
                ):
                    task["time_start"] = datetime.fromtimestamp(
                        task["time_start"]
                    ).strftime("%Y-%m-%d %H:%M:%S")

                output.append(task)

        return output


class TaskResultsView(
    LoginRequiredMixin, SuperuserRequiredMixin, TableMixin, FilteredListView
):
    model = TaskResult
    table_class = TaskResultTable
    filterset_class = TaskResultFilters
    paginate_by = 50
    template_name = "main/taskresult_list.html"
    ordering = "-date_created"
    ordering_fields = {
        "date_created": "date_created",
        "date_done": "date_done",
    }


class TaskResultDetailView(LoginRequiredMixin, SuperuserRequiredMixin, DetailView):
    model = TaskResult
    slug_field = "task_id"
    slug_url_kwarg = "task_id"
    template_name = "main/taskresult_details.html"


class PeriodicTasksView(
    LoginRequiredMixin, SuperuserRequiredMixin, TableMixin, FilteredListView
):
    model = PeriodicTask
    table_class = PeriodicTaskTable
    filterset_class = PeriodicTaskFilters
    paginate_by = 50
    template_name = "main/periodictask_list.html"
    ordering = "name"
    ordering_fields = {
        "name": "Name",
        "last_run_at": "Last run",
    }


class CreatePeriodicTaskView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, CreateView
):
    model = PeriodicTask
    form_class = PeriodicTaskForm
    success_url = reverse_lazy("main:periodic_tasks")
    success_message = "Periodic task created"
    template_name = "main/periodictask_form.html"


class EditPeriodicTaskView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = PeriodicTask
    form_class = PeriodicTaskForm
    success_url = reverse_lazy("main:periodic_tasks")
    success_message = "Periodic task updated"
    template_name = "main/periodictask_form.html"


class DeletePeriodicTaskView(
    LoginRequiredMixin, SuperuserRequiredMixin, SuccessMessageMixin, DeleteView
):
    model = PeriodicTask
    success_url = reverse_lazy("main:periodic_tasks")
    success_message = "Periodic task deleted"
    template_name = "main/periodictask_confirm_delete.html"
