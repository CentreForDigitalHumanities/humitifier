import django_filters

from main.filters import FiltersForm
from .models import IPInfo, Network


class NetworkFilters(django_filters.FilterSet):
    class Meta:
        model = Network
        fields = {
            "name": ["icontains"],
            "vlan": ["exact"],
            "cidr_range": ["icontains"],
        }
        form = FiltersForm


class IPInfoFilters(django_filters.FilterSet):
    class Meta:
        model = IPInfo
        fields = ["network", "active"]
        form = FiltersForm
