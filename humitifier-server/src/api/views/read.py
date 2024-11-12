from django_filters.rest_framework import DjangoFilterBackend
from oauth2_provider.contrib.rest_framework import TokenHasScope
from rest_framework import viewsets

from api.permissions import TokenHasApplication
from api.serializers import HostSerializer
from hosts.filters import HostFilters
from hosts.models import Host


class HostsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset for viewing and editing user instances.
    """
    permission_classes = [
        TokenHasApplication,
        TokenHasScope
    ]
    required_scopes = ['read']
    serializer_class = HostSerializer
    lookup_field = 'fqdn'
    filter_backends = [DjangoFilterBackend]
    filterset_class = HostFilters

    def get_queryset(self):
        # Needed for DRF Spectacular's introspection;
        # The attribute is set in the TokenHasApplication permission
        if not hasattr(self.request, 'application'):
            return Host.objects.none()
        app = self.request.application
        return Host.objects.get_for_application(app)