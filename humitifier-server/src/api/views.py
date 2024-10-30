from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from hosts.models import Host
from hosts.utils import historical_clean


# Create your views here.
class UploadScans(APIView):
    """
    View to list all users in the system.

    * Requires token authentication.
    * Only admin users are able to access this view.
    """

    def post(self, request, format=None):
        """
        Return a list of all users.
        """
        scans = request.data
        hosts = []

        if isinstance(scans, list):
            for scan in scans:
                if 'host' not in scan or 'data' not in scan:
                    raise APIException("Invalid scan data")

                host, created = Host.objects.get_or_create(fqdn=scan['host'])
                host.add_scan(scan['data'])

                hosts.append(host)

        historical_clean()

        return Response("ok")