from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import CreateView, DeleteView

from alerting.filters import AlertAcknowledgmentFilters
from alerting.forms import AlertAcknowledgmentForm
from alerting.models import Alert, AlertAcknowledgment
from alerting.tables import AlertAcknowledgmentTable
from main.views import FilteredListView, SuperuserRequiredMixin, TableMixin


class AlertAcknowledgmentCreateView(
    LoginRequiredMixin, SuperuserRequiredMixin, CreateView
):
    model = AlertAcknowledgment
    form_class = AlertAcknowledgmentForm

    @cached_property
    def alert(self):
        return Alert.objects.get(pk=self.kwargs["alert_id"])

    def get_initial(self):
        return {
            "_alert": self.alert,
            "_creator": self.alert._creator,
            "custom_identifier": self.alert.custom_identifier,
            "host": self.alert.host,
            "acknowledged_by": self.request.user,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["alert"] = self.alert

        return context

    def get_success_url(self):
        return reverse("hosts:detail", args=[self.alert.host])


class AlertAcknowledgmentDeleteView(
    LoginRequiredMixin, SuperuserRequiredMixin, DeleteView
):
    model = AlertAcknowledgment

    def get_success_url(self):
        return reverse("hosts:detail", args=[self.object.host.fqdn])


class AlertAcknowledgementsListView(
    LoginRequiredMixin, SuperuserRequiredMixin, TableMixin, FilteredListView
):
    model = AlertAcknowledgment
    table_class = AlertAcknowledgmentTable
    filterset_class = AlertAcknowledgmentFilters
    paginate_by = 50
    template_name = "alerting/alertacknowledgment_list.html"
    ordering = "acknowledged_at"
    ordering_fields = {
        "reason": "reason",
        "acknowledged_at": "Acknowledged at",
        "acknowledged_by": "Acknowledged by",
    }
