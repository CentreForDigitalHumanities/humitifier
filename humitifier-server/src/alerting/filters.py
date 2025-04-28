#
# Alert filters
#
import django_filters

from alerting.models import Alert, AlertAcknowledgment, AlertSeverity
from hosts.models import Host
from main.filters import (
    BooleanChoiceFilter,
    FiltersForm,
    MultipleChoiceFilterWidget,
    NotNullFilter,
    _get_choices,
)
from main.models import User


class AlertFilters(django_filters.FilterSet):
    class Meta:
        model = Alert
        fields = ["severity"]
        form = FiltersForm

    severity = django_filters.ChoiceFilter(
        label="Alert severity",
        field_name="severity",
        choices=AlertSeverity.choices,
        empty_label="Alert level",
    )

    type = django_filters.MultipleChoiceFilter(
        label="Alert type",
        field_name="short_message",
        choices=lambda: _get_choices(Alert, "short_message", strip_quotes=False),
        widget=MultipleChoiceFilterWidget,
    )

    exclude_type = django_filters.MultipleChoiceFilter(
        label="Alert type (exclude)",
        field_name="short_message",
        choices=lambda: _get_choices(Alert, "short_message", strip_quotes=False),
        widget=MultipleChoiceFilterWidget,
        exclude=True,
    )

    acknowledged = NotNullFilter(
        label="Alert acknowledged",
        field_name="acknowledgement",
    )


class AlertAcknowledgmentFilters(django_filters.FilterSet):
    class Meta:
        model = AlertAcknowledgment
        fields = []
        form = FiltersForm

    host = django_filters.ModelMultipleChoiceFilter(
        label="Host",
        field_name="host",
        queryset=Host.objects.filter(archived=False),
        widget=MultipleChoiceFilterWidget,
    )

    acknowledged_by = django_filters.ModelMultipleChoiceFilter(
        label="Acknowledged by",
        field_name="acknowledged_by",
        queryset=User.objects.filter(is_superuser=True),
        widget=MultipleChoiceFilterWidget,
    )

    alert_type = django_filters.MultipleChoiceFilter(
        label="Department",
        field_name="department",
        choices=lambda: _get_choices(Host, "department", strip_quotes=False),
        widget=MultipleChoiceFilterWidget,
    )

    persistent = BooleanChoiceFilter(
        empty_label="Is persistent",
        field_name="persistent",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )
