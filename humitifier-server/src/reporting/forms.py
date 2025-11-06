from django import forms

from hosts.models import Host
from main.filters import MultipleChoiceFilterWidget, _get_choices
from reporting.models import CostsScheme


class CostsSchemeForm(forms.ModelForm):
    class Meta:
        model = CostsScheme
        fields = "__all__"


class CostCalculatorForm(forms.Form):

    costs_scheme = forms.ModelChoiceField(
        label="Costs Scheme",
        queryset=CostsScheme.objects,
        help_text="Please note that future pricing schemes may not be definitive.",
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


class CostsReportForm(forms.Form):
    filename = forms.CharField(
        label="Filename",
        initial="costs_report.xlsx",
    )

    costs_scheme = forms.ModelChoiceField(
        label="Costs Scheme",
        queryset=CostsScheme.objects,
    )

    customers = forms.MultipleChoiceField(
        label="Customer",
        choices=lambda: _get_choices(Host, "customer", strip_quotes=False),
        required=False,
        widget=MultipleChoiceFilterWidget(attrs={"placeholder": "All customers"}),
    )

    start_date = forms.DateField(
        label="Start Date",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="The first month included in the report. The day value is ignored; "
        "for example, any date in januari will start the report from januari",
    )

    end_date = forms.DateField(
        label="End Date",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="The last month included in the report. The day value is ignored; "
        "for example, any date in september will run the report up to and "
        "including september.",
    )
