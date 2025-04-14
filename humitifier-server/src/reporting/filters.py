from django_filters import FilterSet

from main.filters import FiltersForm
from reporting.models import CostsScheme


class CostsSchemeFilters(FilterSet):
    class Meta:
        model = CostsScheme
        fields = []
        form = FiltersForm
