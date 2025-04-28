import django_filters
from django.db.models import QuerySet
from django.forms import (
    Form,
    NullBooleanSelect,
    Select,
    SelectMultiple,
)
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult

from main.models import AccessProfile, User

#
# Helpers
#


def _get_choices(model, field, strip_quotes=True):
    # The empty order_by() is required to remove the default ordering
    # which would otherwise mess up the distinct() call.
    # (It would add the ordering field to the SELECT list, which means postgres
    # would view every row as distinct.)
    db_values = model.objects.values_list(field, flat=True).order_by().distinct()
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


#
# Widgets
#


class MultipleChoiceFilterWidget(SelectMultiple):
    class Media:
        js = ["main/js/alpine.multiselect.js"]

    template_name = "django/forms/widgets/multi_select_filter.html"


#
# Base Filters
#


class NullFilterWidget(NullBooleanSelect):

    def __init__(self, attrs=None, label=None):
        choices = [
            (
                "unknown",
                label or "All",
            ),
            (
                "true",
                "Yes",
            ),
            (
                "false",
                "No",
            ),
        ]
        super(Select, self).__init__(attrs, choices)


class NullFilter(django_filters.BooleanFilter):
    """
    Implements a filter that can be used to include or exclude null values in a
    queryset.

    This class can be used as a boolean-filter where false and true will
    exclude or include null values (depending on the exclude_null setting).

    For example, with filter_on_false and exclude_null both set to true, this filter
    will do the following:

    If filter set to:
        - None: no filter is applied
        - True: all non-null values are filtered out
        - False: all null values are filtered out

    Alternatively, it can be used as a 'flag' where setting the filter to false
    will not filter anything using the `filter_on_false` setting.

    Note: setting the filter to 'None' will always result in a no-op, not applying
    a filter.

    Parameters:
        field_name (str): The name of the model field to be filtered.
        filter_on_false (bool): If True (default), a filter-value of false will apply
                                the inverse of the filter to the QS. If False, a filter
                                value of false will be regarded as None, not applying
                                any filter to the QS.
        exclude_null (bool): If True (default), only returns objects where the field is
                             not-null. If False, only returns objects where the field is
                             null.
        option_labels (dict[str, str]): A dictionary of labels to use for the filter
                                        options. The keys should be "all", "true", and
                                        "false" for the 'all', 'not-null', and 'null'
                                        options respectively.
    """

    def __init__(
        self,
        field_name: str,
        filter_on_false: bool = True,
        exclude_null: bool = True,
        **kwargs,
    ):
        self.filter_on_false = filter_on_false
        self.exclude_null = exclude_null

        label = None
        if "label" in kwargs:
            label = kwargs["label"]

        kwargs["widget"] = NullFilterWidget(attrs={}, label=label)

        super().__init__(field_name=field_name, **kwargs)

    def filter(self, qs: QuerySet, value: bool) -> QuerySet:
        # Filter not set, so we do nothing
        if value is None:
            return qs

        # Filter was set to false; do nothing if the filter is configured to do nothing
        # in this case
        if value is False and not self.filter_on_false:
            return qs

        should_exclude = self.exclude_null
        # Invert our actions if the filter is set to false
        if value is False:
            should_exclude = not should_exclude

        if should_exclude:
            return qs.exclude(**{self.field_name: None})

        return qs.filter(**{self.field_name: None})


class NotNullFilter(NullFilter):
    """
    A filter that excludes null values from a given field, only if the filter
    is set to 'true'. Otherwise, the filter will not filter anything.

    Use `NullFilter` if you want false to exclude non-null values instead.

    Parameters:
        field_name (str): The name of the field to filter on.

    """

    def __init__(self, field_name: str, **kwargs):
        kwargs["exclude_null"] = True
        kwargs["filter_on_false"] = False
        super().__init__(field_name, **kwargs)


class IsNullFilter(NullFilter):
    """
    A filter that excludes non-null values from a given field, only if the filter
    is set to 'true'. Otherwise, the filter will not filter anything.

    Use `NullFilter` if you want false to exclude null values instead.

    Parameters:
        field_name (str): The name of the field to filter on.
    """

    def __init__(self, field_name: str, **kwargs):
        kwargs["exclude_null"] = False
        kwargs["filter_on_false"] = False
        super().__init__(field_name, **kwargs)


class BooleanChoiceFilter(django_filters.ChoiceFilter):

    def filter(self, qs, value):
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False

        return super().filter(qs, value)


#
# Base filter form
#


class FiltersForm(Form):
    template_name = "base/page_parts/filters_form_template.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            self.fields[field_name].widget.attrs["placeholder"] = field.label


#
# Actual filtersets
#


class UserFilters(django_filters.FilterSet):
    class Meta:
        model = User
        fields = ["is_active", "is_local_account", "access_profile"]
        form = FiltersForm

    is_active = django_filters.ChoiceFilter(
        empty_label="Is active",
        field_name="is_active",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )

    is_local_account = django_filters.ChoiceFilter(
        empty_label="Is local account",
        field_name="is_local_account",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )

    access_profile = django_filters.ModelChoiceFilter(
        field_name="access_profile",
        queryset=AccessProfile.objects.all(),
        empty_label="Access profile",
    )


class AccessProfileFilters(django_filters.FilterSet):
    class Meta:
        model = AccessProfile
        fields = ["departments"]
        form = FiltersForm

    departments = django_filters.CharFilter(
        field_name="departments",
        lookup_expr="icontains",
    )


class TaskResultFilters(django_filters.FilterSet):
    class Meta:
        model = TaskResult
        fields = []
        form = FiltersForm

    task_name = django_filters.MultipleChoiceFilter(
        label="Task name",
        field_name="task_name",
        choices=lambda: _get_choices(TaskResult, "task_name", strip_quotes=False),
        widget=MultipleChoiceFilterWidget,
    )

    worker = django_filters.MultipleChoiceFilter(
        label="Worker",
        field_name="worker",
        choices=lambda: _get_choices(TaskResult, "worker", strip_quotes=False),
        widget=MultipleChoiceFilterWidget,
    )


class PeriodicTaskFilters(django_filters.FilterSet):
    class Meta:
        model = PeriodicTask
        fields = []
        form = FiltersForm

    enabled = BooleanChoiceFilter(
        empty_label="Enabled",
        field_name="enabled",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )
