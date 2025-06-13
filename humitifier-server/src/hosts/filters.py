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
        """Main filter method to determine which package filter to apply."""
        if not value:
            return qs

        if "==" in value:
            package, version = value.split("==", maxsplit=1)
            return self.filter_package_exact_version(qs, package, version)
        elif "~=" in value:
            package, version = value.split("~=", maxsplit=1)
            return self.filter_package_start_version(qs, package, version)

        return self.filter_package(qs, value)

    def _build_package_query(self, name_filter, version_filter=None, exact_match=False):
        """
        Helper method to build the common SQL query for package filtering.

        :param name_filter: The name filter pattern (string).
        :param version_filter: The version filter pattern (string), optional.
        :param exact_match: Whether to use an exact match for the `version_filter`.
        :return: Tuple of raw SQL and params.
        """
        query = (
            "SELECT count(*) FROM jsonb_array_elements("
            "\"hosts_host\".\"last_scan_cache\"->'facts'->'generic.PackageList'"
            ") AS pkg WHERE pkg->>'name' LIKE %s"
        )
        params = [f"%{name_filter}%"]

        if version_filter:
            operator = "=" if exact_match else "LIKE"
            query += f" AND pkg->>'version' {operator} %s"
            params.append(version_filter if exact_match else f"%{version_filter}%")

        return query, params

    def filter_package(self, qs, value):
        """
        Filters the queryset based on package existence.
        """
        query, params = self._build_package_query(value)
        qs = qs.annotate(package_exists=RawSQL(query, params))
        return qs.filter(package_exists__gt=0)

    def filter_package_exact_version(self, qs, package, version):
        """
        Filters the queryset for an exact package version match.
        """
        query, params = self._build_package_query(package, version, exact_match=True)
        qs = qs.annotate(package_exists=RawSQL(query, params))
        return qs.filter(package_exists__gt=0)

    def filter_package_start_version(self, qs, package, version):
        """
        Filters the queryset for a package version starting with `version`.
        """
        query, params = self._build_package_query(package, version, exact_match=False)
        qs = qs.annotate(package_exists=RawSQL(query, params))
        return qs.filter(package_exists__gt=0)


class HostAlertSeverityFilter(ChoiceFilter):

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = AlertSeverity.choices
        kwargs["field_name"] = "alerts__severity"
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            return qs.filter(alerts__severity=value)
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

    open_tofu = BooleanChoiceFilter(
        empty_label="Is OpenTofu managed",
        field_name="has_tofu_config",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )

    package = PackageFilter(
        label="Package",
    )

    is_wp = BooleanChoiceFilter(
        empty_label="Is WordPress",
        field_name="last_scan_cache__facts__server.IsWordpress__is_wp",
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
