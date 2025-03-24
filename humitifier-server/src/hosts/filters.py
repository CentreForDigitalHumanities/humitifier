import django_filters
from django.db.models.expressions import RawSQL
from django_filters import ChoiceFilter
from drf_spectacular.types import OpenApiTypes

from alerting.backend.registry import alert_generator_registry
from alerting.models import AlertSeverity
from hosts.models import DataSource, Host
from main.filters import (
    BooleanChoiceFilter,
    FiltersForm,
    MultipleChoiceFilterWidget,
    _get_choices,
)


#
# DataSource filters
#


class DataSourceFilters(django_filters.FilterSet):
    class Meta:
        model = DataSource
        fields = ["source_type"]
        form = FiltersForm


#
# Host filters
#


class TextSearchFilter(django_filters.Filter):

    def filter(self, qs, value):
        if value:
            kwargs = {f"{self.field_name}__icontains": value}
            return qs.filter(**kwargs)
        return qs


class PackageFilter(django_filters.Filter):
    _spectacular_annotation = {
        "field": OpenApiTypes.STR,
    }

    def filter(self, qs, value):
        if value:
            qs = qs.annotate(
                package_exists=RawSQL(
                    "SELECT 1 FROM jsonb_array_elements(\"hosts_host\".\"last_scan_cache\"->'PackageList') AS pkg WHERE pkg->>'name' = %s",
                    [value],
                )
            )
            return qs.filter(package_exists__isnull=False)
        return qs


class HostAlertSeverityFilter(ChoiceFilter):

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = AlertSeverity.choices
        kwargs["field_name"] = "alerts__severity"
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            return qs.filter(alerts__level=value)
        return qs


class HostAlertTypeFilter(ChoiceFilter):

    def __init__(self, *args, **kwargs):
        choices = alert_generator_registry.get_alert_types()
        kwargs["choices"] = [(choice, choice) for choice in choices]
        kwargs["field_name"] = "alerts__short_message"
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            return qs.filter(alerts__short_message=value)
        return qs


class IncludeArchivedFilter(ChoiceFilter):
    def __init__(self, *args, **kwargs):
        kwargs["choices"] = [
            (True, "Include archived servers"),
        ]
        kwargs["field_name"] = "archived"
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if not value:
            return qs.filter(archived=False)
        return qs


class HostFilters(django_filters.FilterSet):
    class Meta:
        model = Host
        fields = ["fqdn"]
        form = FiltersForm

    fqdn = TextSearchFilter(
        label="Hostname",
        field_name="fqdn",
    )

    os = django_filters.MultipleChoiceFilter(
        label="Operating System",
        field_name="os",
        choices=lambda: _get_choices(Host, "os"),
        widget=MultipleChoiceFilterWidget,
    )

    alert_severity = HostAlertSeverityFilter(
        empty_label="Alert severity",
    )

    alert_type = HostAlertTypeFilter(
        empty_label="Alert Type",
    )

    department = django_filters.MultipleChoiceFilter(
        label="Department",
        field_name="department",
        choices=lambda: _get_choices(Host, "department", strip_quotes=False),
        widget=MultipleChoiceFilterWidget,
    )

    customer = django_filters.MultipleChoiceFilter(
        label="Customer",
        field_name="customer",
        choices=lambda: _get_choices(Host, "customer", strip_quotes=False),
        widget=MultipleChoiceFilterWidget,
    )

    contact = django_filters.MultipleChoiceFilter(
        label="Contact",
        field_name="contact",
        choices=lambda: _get_choices(Host, "contact", strip_quotes=False),
        widget=MultipleChoiceFilterWidget,
    )

    otap_stage = django_filters.MultipleChoiceFilter(
        label="OTAP",
        field_name="otap_stage",
        choices=lambda: _get_choices(Host, "otap_stage", strip_quotes=False),
        widget=MultipleChoiceFilterWidget,
    )

    package = PackageFilter(
        label="Package",
    )

    is_wp = BooleanChoiceFilter(
        empty_label="Is WordPress",
        field_name="last_scan_cache__IsWordpress__is_wp",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )

    data_source = django_filters.ModelMultipleChoiceFilter(
        label="Data Source",
        field_name="data_source",
        queryset=DataSource.objects.all(),
        widget=MultipleChoiceFilterWidget,
    )

    archived = IncludeArchivedFilter(
        empty_label="Exclude archived servers",
    )
