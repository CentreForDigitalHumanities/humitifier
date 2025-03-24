import django_filters

from main.filters import FiltersForm
from scanning.models import ScanSpec


class ScanSpecFilters(django_filters.FilterSet):
    class Meta:
        model = ScanSpec
        fields = []
        form = FiltersForm
