from django.urls import reverse
from django.utils.safestring import mark_safe

from main.easy_tables import (
    BaseTable,
    BooleanColumn,
    ButtonColumn,
    CompoundColumn,
    DateTimeColumn,
    MethodColumn,
    ModelValueColumn,
)
from .models import IPInfo, Network


class NetworksTable(BaseTable):
    class Meta:
        model = Network
        columns = [
            "name",
            "vlan",
            "cidr_range",
            "actions",
        ]
        no_data_message = "No networks found."
        no_data_message_wild_wasteland = (
            "How can you access this server if you have no networks?"
        )

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Edit",
                button_class="btn btn-primary mr-2",
                url=lambda obj: reverse("network:edit", args=[obj.pk]),
            ),
            ButtonColumn(
                text="Delete",
                button_class="btn btn-danger",
                url=lambda obj: reverse("network:delete", args=[obj.pk]),
            ),
        ],
    )


class IPInfoTable(BaseTable):
    class Meta:
        model = IPInfo
        columns = [
            "ip_address",
            "active",
            "ping_time",
            "hosts_from_ip",
            "reverse_dns_entries",
            "port_status",
            "last_indexed",
        ]
        column_type_overrides = {
            "ip_address": ModelValueColumn(column_classes=["font-bold"]),
            "active": BooleanColumn(
                yes_no_values={True: "✅", False: "❌", None: "How"},
                column_classes=["text-center"],
            ),
            "last_indexed": DateTimeColumn,
        }
        no_data_message = "No IP addresses found."
        no_data_message_wild_wasteland = "Awfully quiet around these parts; maybe you should start creating some networks?"

    reverse_dns_entries = MethodColumn(
        "Reverse DNS entries", method_name="get_reverse_dns_entries", mark_safe=True
    )

    hosts_from_ip = MethodColumn(
        "Humitifier Host", method_name="get_hosts_from_ip", mark_safe=True
    )

    port_status = MethodColumn(
        "Open ports", method_name="get_port_status", mark_safe=True
    )

    @staticmethod
    def get_reverse_dns_entries(obj: IPInfo):
        if not obj.reverse_dns_entries:
            return ""

        hosts_from_dns = obj.hosts_from_dns.all()

        output = []

        for entry in obj.reverse_dns_entries:
            stripped_entry = entry[:-1] if entry.endswith(".") else entry
            qs = hosts_from_dns.filter(fqdn=stripped_entry)
            if qs.exists():
                item = qs.first()
                output.append(
                    f'<a href="{reverse('hosts:detail', args=[item.fqdn])}" class="underline">{stripped_entry}</a>'
                )
            else:
                output.append(stripped_entry)

        return ", ".join(output)

    @staticmethod
    def get_hosts_from_ip(obj: IPInfo):
        output = []

        for host in obj.hosts_from_ip.all():
            output.append(
                f'<a href="{reverse('hosts:detail', args=[host.fqdn])}" class="underline">{host}</a>'
            )

        return ", ".join(output)

    @staticmethod
    def get_port_status(obj: IPInfo):
        if not obj.port_status:
            return ""

        output = []

        for port, is_open in obj.port_status.items():
            if is_open:
                output.append(port)

        return ", ".join(output)
