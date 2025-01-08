from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiTypes, inline_serializer
from oauth2_provider.contrib.rest_framework import TokenHasScope
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import TokenHasApplication
from api.serializers import DataSourceSyncSerializer
from hosts.models import DataSource, DataSourceType, Host


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

        return Response(len(scans))


class DatastoreSyncView(APIView):
    permission_classes = [TokenHasApplication, TokenHasScope]
    required_scopes = ["system"]

    @extend_schema(
        operation_id="inventory_sync",
        request=DataSourceSyncSerializer,
        responses={
            200: OpenApiTypes.INT,
            400: DataSourceSyncSerializer.errors,
            500: OpenApiTypes.STR,
        },
    )
    def post(self, request):
        """
        Sync inventory data
        """
        serializer = DataSourceSyncSerializer(data=request.data)

        data_source, validation_errors = self.validate(serializer)

        if validation_errors:
            return validation_errors

        return self.sync(serializer, data_source)

    def validate(
        self, serializer: DataSourceSyncSerializer
    ) -> (DataSource | None, Response | None):
        """
        Validates the given serializer to determine if it corresponds to a valid
        data source for the application linked to the current request. If valid,
        returns the matching DataSource instance. If validation or determination
        fails, returns an appropriate HTTP response describing the failure.

        :param serializer: Serializer containing data to validate against
        :return: A tuple where the first element is a DataSource instance or None
            if validation fails, and the second element is a Response instance
            or None if the validation is successful
        """
        if not hasattr(self.request, "application"):
            return None, Response(
                "Somehow we could not figure out who you are?",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        app = self.request.application

        # Run initial serializer validation
        if serializer.is_valid():
            # See if the OAuth app has access to this data source
            data_sources = DataSource.objects.get_for_application(app).filter(
                identifier=serializer.data["data_source"]
            )

            # This check could also be `==0`, as more than one _should_ be impossible
            # However, stranger things have happened
            if data_sources.count() != 1:
                return None, Response(
                    {
                        "data_source": "The specified data source could not be found.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data_source = data_sources[0]

            # See if this data source allows syncing over the API
            if data_source.source_type != DataSourceType.API:
                return None, Response(
                    {
                        "data_source": "The specified data source does not allow API syncing",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if all specified hosts are either un-owned or owned by this data source
            all_existing_hosts = Host.objects.filter(
                fqdn__in=[host["fqdn"] for host in serializer.data["hosts"]],
            )

            hosts_owned_by_other_datasource = all_existing_hosts.exclude(
                Q(data_source=data_source) | Q(data_source=None)
            )

            if hosts_owned_by_other_datasource.count() != 0:
                formatted = ", ".join(
                    hosts_owned_by_other_datasource.values_list("fqdn", flat=True)
                )
                return None, Response(
                    {
                        "hosts": f"The following hosts are owned by other data sources: {formatted}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # All checks passed, return the found data source
            return data_source, None

        # The initial serializer validation failed, send back the found errors
        return None, Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def sync(
        self, serializer: DataSourceSyncSerializer, data_source: DataSource
    ) -> Response:
        hosts = serializer.data["hosts"]
        # Transform the list of hosts into a dict with the fqdn as key. Simplifies logic later on
        hosts_dict = {host["fqdn"]: host for host in hosts}

        # Get all hosts that we already know about and are either owned by this data source or currently unowned
        existing_hosts = Host.objects.filter(
            fqdn__in=hosts_dict.keys(),
        ).filter(Q(data_source=data_source) | Q(data_source=None))

        # Find any hosts that are not in our database yet
        new_hosts = [
            fqdn
            for fqdn in hosts_dict.keys()
            if fqdn not in existing_hosts.values_list("fqdn", flat=True)
        ]

        # Find any hosts that we know of, but are not provided by our API client
        # These hosts should be archived
        removed_hosts = Host.objects.filter(
            data_source=data_source,
        ).exclude(
            fqdn__in=hosts_dict.keys(),
        )

        #
        for removed_host in removed_hosts:
            if not removed_host.archived:
                removed_host.archive()

        # Then, let's update our existing hosts
        for host in existing_hosts:
            new_data = hosts_dict.get(host.fqdn)

            # TODO: update any relevant info

            # If this host is unclaimed, we set the data_source attr to claim it
            if host.data_source is None:
                host.data_source = data_source

            host.save()

            if host.archived:
                host.unarchive()

        # Lastly, create new hosts
        for fqdn in new_hosts:
            new_data = hosts_dict.get(fqdn)

            # TODO: set any relevant info
            Host.objects.create(
                fqdn=fqdn,
                data_source=data_source,
            )

        return Response(
            {
                "updated": [host.fqdn for host in existing_hosts],
                "created": new_hosts,
                "archived": [host.fqdn for host in removed_hosts],
            }
        )
