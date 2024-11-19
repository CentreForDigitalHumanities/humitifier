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
