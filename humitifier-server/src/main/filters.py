import django_filters
from django.forms import Form, SelectMultiple
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
