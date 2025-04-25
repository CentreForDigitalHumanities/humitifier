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

    storage = forms.DecimalField(
        label="Storage in GB",
        initial=50,
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

    customer = forms.ChoiceField(
        label="Customer",
        choices=lambda: _get_choices(Host, "customer", strip_quotes=False)
        + [(None, "-" * 9)],
        required=False,
    )
