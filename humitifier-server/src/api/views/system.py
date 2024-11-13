from drf_spectacular.utils import extend_schema, OpenApiTypes, inline_serializer
from oauth2_provider.contrib.rest_framework import TokenHasScope
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import TokenHasApplication
from hosts.models import Host
from hosts.utils import historical_clean


class UploadScans(APIView):
    permission_classes = [TokenHasApplication, TokenHasScope]
    required_scopes = ["system"]

    @extend_schema(
        operation_id="upload_scans",
        request=inline_serializer(
            "Scan",
            fields={
                "host": serializers.CharField(required=True),
                "data": serializers.JSONField(required=True),
            },
            many=True,
        ),
        responses={200: OpenApiTypes.INT},
    )
    def post(self, request, format=None):
        """
        Upload one or more scans for a host
        """
        scans = request.data
        hosts = []

        if not isinstance(scans, list):
            scans = [scans]

        for scan in scans:
            if "host" not in scan or "data" not in scan:
                raise APIException("Invalid scan data")

            host, created = Host.objects.get_or_create(fqdn=scan["host"])
            host.add_scan(scan["data"])

            hosts.append(host)

        historical_clean()

        return Response(len(scans))


class InventorySync(APIView):
    permission_classes = [TokenHasApplication, TokenHasScope]
    required_scopes = ["system"]

    @extend_schema(
        operation_id="inventory_sync",
        request=inline_serializer(
            "InventorySync",
            fields={
                "inventory": serializers.UUIDField(required=True),
                "hosts": serializers.ListField(
                    child=serializers.CharField(),
                    required=True,
                ),
            },
        ),
        responses={200: OpenApiTypes.INT},
    )
    def post(self, request, format=None):
        """
        Sync inventory data
        """
        # TODO: implement :D
        raise NotImplementedError("Not implemented")
