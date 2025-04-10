from django import forms

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
