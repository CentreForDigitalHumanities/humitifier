import django_filters
from django.forms import Form

from main.models import AccessProfile, User


class FiltersForm(Form):
    template_name = 'base/page_parts/filters_form_template.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            self.fields[field_name].widget.attrs['placeholder'] = field.label


class UserFilters(django_filters.FilterSet):
    class Meta:
        model = User
        fields = ['is_active', 'is_local_account', 'access_profile']
        form = FiltersForm

    is_active = django_filters.ChoiceFilter(
        empty_label="Is active",
        field_name="is_active",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ]
    )

    is_local_account = django_filters.ChoiceFilter(
        empty_label="Is local account",
        field_name="is_local_account",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ]
    )

    access_profile = django_filters.ModelChoiceFilter(
        field_name="access_profile",
        queryset=AccessProfile.objects.all(),
        empty_label="Access profile",
    )