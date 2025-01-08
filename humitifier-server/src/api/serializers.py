from rest_framework import serializers

from hosts.models import Host


class HostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Host
        fields = [
            "fqdn",
            "created_at",
            "archived",
            "archival_date",
            "department",
            "contact",
            "os",
            "link",
        ]

    link = serializers.HyperlinkedIdentityField(
        view_name="hosts:detail", lookup_field="fqdn"
    )


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
