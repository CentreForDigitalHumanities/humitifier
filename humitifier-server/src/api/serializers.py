from drf_spectacular.utils import extend_schema_field
from pydantic import ValidationError
from rest_framework import serializers

from hosts.models import Host
from humitifier_common.artefacts import RebootPolicy

REBOOT_POLICY_SCHEMA = {
    "type": "object",
    "properties": {
        "configured": {
            "type": "boolean",
            "description": "Indicates whether the reboot policy is configured.",
            "example": True,
        },
        "enabled": {
            "type": "boolean",
            "description": "Indicates whether the reboot policy is enabled. Nullable.",
            "nullable": True,
            "example": False,
        },
        "cron_minute": {
            "type": "string",
            "description": "Cron expression for the minute. Nullable.",
            "nullable": True,
            "example": "0",
        },
        "cron_hour": {
            "type": "string",
            "description": "Cron expression for the hour. Nullable.",
            "nullable": True,
            "example": "3",
        },
        "cron_monthday": {
            "type": "string",
            "description": "Cron expression for the day of the month. Nullable.",
            "nullable": True,
            "example": "15",
        },
    },
    "required": ["configured"],  # Only "configured" is required based on provided model
    "example": {
        "configured": True,
        "enabled": False,
        "cron_minute": "0",
        "cron_hour": "3",
        "cron_monthday": "15",
    },
}


class HostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Host
        fields = [
            "fqdn",
            "created_at",
            "archived",
            "archival_date",
            "department",
            "customer",
            "contact",
            "os",
            "link",
            "reboot_policy",
        ]

    link = serializers.HyperlinkedIdentityField(
        view_name="hosts:detail", lookup_field="fqdn"
    )

    reboot_policy = serializers.SerializerMethodField(
        required=False,
        allow_null=True,
    )

    @extend_schema_field(REBOOT_POLICY_SCHEMA)
    def get_reboot_policy(self, obj: Host) -> None | RebootPolicy:
        if not obj.last_scan_cache:
            return None

        scan_data = obj.get_scan_object()

        if scan_data.version == 1:
            return None

        if "server.RebootPolicy" not in scan_data.raw_data["facts"]:
            return None

        return scan_data.raw_data["facts"]["server.RebootPolicy"]


class DataSourceSyncHostSerializer(serializers.Serializer):

    fqdn = serializers.CharField()

    department = serializers.CharField()

    customer = serializers.CharField()

    contact = serializers.CharField()

    has_tofu_config = serializers.BooleanField()

    otap_stage = serializers.CharField()


class DataSourceSyncSerializer(serializers.Serializer):

    data_source = serializers.UUIDField()

    hosts = DataSourceSyncHostSerializer(many=True)


class ScanSpecSerializer(serializers.Serializer):

    hostname = serializers.CharField()
    artefacts = serializers.DictField(child=serializers.DictField())
