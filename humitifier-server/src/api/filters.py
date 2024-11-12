import django_filters

from api.models import OAuth2Application
from main.filters import FiltersForm


class OAuth2ApplicationFilters(django_filters.FilterSet):
    class Meta:
        model = OAuth2Application
        fields = ['access_profile']
        form = FiltersForm