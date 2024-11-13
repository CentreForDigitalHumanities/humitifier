import django_filters
from django.db.models.expressions import RawSQL
from django_filters import ChoiceFilter
from drf_spectacular.types import OpenApiTypes

from hosts.models import Alert, AlertLevel, AlertType, Host
from main.filters import FiltersForm, MultipleChoiceFilterWidget


def _get_choices(field, strip_quotes=True):
    # The empty order_by() is required to remove the default ordering
    # which would otherwise mess up the distinct() call.
    # (It would add the ordering field to the SELECT list, which means postgres
    # would view every row as distinct.)
    db_values = Host.objects.values_list(field, flat=True).order_by().distinct()
    # Not needed, but just to be sure
    db_values = set(db_values)
    values = []

    for db_value in db_values:
        if db_value:
            human_label = db_value
            if strip_quotes:
                human_label = human_label[1:-1]

            values.append((db_value, human_label))

    values = sorted(values, key=lambda x: x[1])

    return values


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


class HostAlertLevelFilter(ChoiceFilter):

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = AlertLevel.choices
        kwargs["field_name"] = "alerts__level"
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            return qs.filter(alerts__level=value)
        return qs


class HostAlertTypeFilter(ChoiceFilter):

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = AlertType.choices
        kwargs["field_name"] = "alerts__type"
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            return qs.filter(alerts__type=value)
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
        choices=lambda: _get_choices("os"),
        widget=MultipleChoiceFilterWidget,
    )

    alert_level = HostAlertLevelFilter(
        empty_label="Alert level",
    )

    alert_type = HostAlertTypeFilter(
        empty_label="Alert Type",
    )

    department = django_filters.MultipleChoiceFilter(
        label="Department",
        field_name="department",
        choices=lambda: _get_choices("department"),
        widget=MultipleChoiceFilterWidget,
    )

    contact = django_filters.MultipleChoiceFilter(
        label="Contact",
        field_name="contact",
        choices=lambda: _get_choices("contact"),
        widget=MultipleChoiceFilterWidget,
    )

    package = PackageFilter(
        label="Package",
    )

    is_wp = django_filters.ChoiceFilter(
        empty_label="Is WordPress",
        field_name="last_scan_cache__IsWordpress__is_wp",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )

    archived = IncludeArchivedFilter(
        empty_label="Exclude archived servers",
    )


class AlertFilters(django_filters.FilterSet):
    class Meta:
        model = Alert
        fields = ["level", "type"]
        form = FiltersForm

    level = django_filters.ChoiceFilter(
        label="Alert level",
        field_name="level",
        choices=AlertLevel.choices,
        empty_label="Alert level",
    )

    type = django_filters.MultipleChoiceFilter(
        label="Alert type",
        field_name="type",
        choices=AlertType.choices,
    )
