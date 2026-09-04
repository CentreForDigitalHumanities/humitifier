from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiTypes, inline_serializer
from oauth2_provider.contrib.rest_framework import TokenHasScope
from rest_framework import serializers, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import TokenHasApplication
from api.serializers import DataSourceSyncSerializer, ScanSpecSerializer
from api.tasks import datasource_sync
from hosts.models import DataSource, DataSourceType, Host
from humitifier_common.scan_data import ScanOutput
from humitifier_server.logger import logger
from scanning.utils import _get_processing_chain


class GetScanSpecView(RetrieveAPIView):
    """
    A view for retrieving scan specifications based on the host's fully qualified domain name (FQDN).
    """

    permission_classes = [TokenHasApplication, TokenHasScope]
    required_scopes = ["system"]
    serializer_class = ScanSpecSerializer
    lookup_field = "fqdn"

    def retrieve(self, request, *args, **kwargs):
        instance: Host = self.get_object()
        serializer = self.get_serializer(
            instance.get_scan_input().model_dump(mode="json")
        )
        return Response(serializer.data)

    def get_queryset(self):
        # Needed for DRF Spectacular's introspection;
        # The attribute is set in the TokenHasApplication permission
        if not hasattr(self.request, "application"):
            return Host.objects.none()
        app = self.request.application

        # We cannot use the `get_for_application` of the Host manager,
        # as that is written for the read scope. So, this is the right
        # stuff for the system scope
        data_sources = DataSource.objects.get_for_application(app)
        return Host.objects.filter(data_source__in=data_sources)


class UploadScans(APIView):
    permission_classes = [TokenHasApplication, TokenHasScope]
    required_scopes = ["system"]

    @extend_schema(
        operation_id="upload_scans",
        request=inline_serializer(
            "Scan",
            fields={
                "version": serializers.IntegerField(required=True),
                "scan_date": serializers.DateTimeField(required=True),
                "original_input": serializers.JSONField(required=True),
                "hostname": serializers.CharField(required=True),
                "facts": serializers.JSONField(required=True),
                "metrics": serializers.JSONField(required=True),
                "errors": serializers.ListField(
                    child=serializers.JSONField(), required=True
                ),
            },
        ),
        responses={200: OpenApiTypes.BOOL},
    )
    def post(self, request, format=None):
        """
        Upload one or more scans for a host
        """
        scan = request.data

        try:
            parsed_scan = ScanOutput(**scan)
        except Exception as e:
            logger.error(e)
            return Response(
                "Malformed data send",
                status=status.HTTP_400_BAD_REQUEST,
            )

        host = Host.objects.get(fqdn=parsed_scan.hostname)

        if host.can_schedule_scan:
            return Response(
                "Cannot upload scan for non-manually scheduled hosts",
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_data_sources = DataSource.objects.get_for_application(
            self.request.application
        )

        if not host.data_source in allowed_data_sources:
            return Response(
                "This client may not upload results to this data source",
                status=status.HTTP_403_FORBIDDEN,
            )

        process_task = _get_processing_chain(initial_args=(scan,))

        process_task.apply_async()

        return Response(True)


class DatastoreSyncView(APIView):
    permission_classes = [TokenHasApplication, TokenHasScope]
    required_scopes = ["system"]

    @extend_schema(
        operation_id="inventory_sync",
        request=DataSourceSyncSerializer,
        responses={
            200: OpenApiTypes.BOOL,
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

        datasource_sync.delay(serializer.data["hosts"], data_source.pk)

        return Response(True)

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
