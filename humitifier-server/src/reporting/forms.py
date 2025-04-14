from django import forms

from hosts.models import Host
from main.filters import _get_choices
from reporting.models import CostsScheme


class CostsSchemeForm(forms.ModelForm):
    class Meta:
        model = CostsScheme
        fields = "__all__"


class CostCalculatorForm(forms.Form):

    costs_scheme = forms.ModelChoiceField(
        label="Costs Scheme",
        queryset=CostsScheme.objects,
    )

    num_cpu = forms.IntegerField(
        label="Number of CPUs",
        initial=1,
    )

    memory = forms.DecimalField(
        label="Memory in GB",
        initial=2,
    )

    cpu_memory_bundle = forms.BooleanField(
        label="CPU costs include 2Gb of memory", required=False
    )

    storage = forms.DecimalField(
        label="Storage in GB",
        initial=50,
    )

    redundant_storage = forms.BooleanField(
        label="Redundant storage", initial=True, required=False
    )

    os = forms.ChoiceField(
        label="Operating System",
        choices=(
            ("Linux", "Linux"),
            ("Windows", "Windows"),
        ),
    )


class CostsOverviewForm(forms.Form):
    costs_scheme = forms.ModelChoiceField(
        label="Costs Scheme",
        queryset=CostsScheme.objects,
    )

    department = forms.ChoiceField(
        label="Department",
        choices=lambda: _get_choices(Host, "department", strip_quotes=False)
        + [(None, "-" * 9)],
        required=False,
    )

    customer = forms.ChoiceField(
        label="Customer",
        choices=lambda: _get_choices(Host, "customer", strip_quotes=False)
        + [(None, "-" * 9)],
        required=False,
    )

    redundant_storage = forms.BooleanField(
        label="Redundant storage", initial=True, required=False
    )

    cpu_memory_bundle = forms.BooleanField(
        label="CPU costs include 2Gb of memory", required=False
    )
