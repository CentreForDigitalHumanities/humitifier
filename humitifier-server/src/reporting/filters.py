from django_filters import FilterSet

from main.filters import FiltersForm
from reporting.models import CostsScheme, GeneratedReport


class CostsSchemeFilters(FilterSet):
    class Meta:
        model = CostsScheme
        fields = ["name", "platform"]
        form = FiltersForm


class GeneratedReportFilters(FilterSet):
    class Meta:
        model = GeneratedReport
        fields = ["status"]
        form = FiltersForm
