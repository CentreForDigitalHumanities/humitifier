from django.urls import reverse

from hosts.models import Host, DataSource
from main.easy_tables import (
    BaseTable,
    ButtonColumn,
    CompoundColumn,
    DateTimeColumn,
    LinkColumn,
    ModelValueColumn,
    TemplatedColumn,
    MethodColumn,
)


class DataSourcesTable(BaseTable):
    class Meta:
        model = DataSource
        columns = [
            "name",
            "identifier",
            "source_type",
            "scan_scheduling",
            "default_scan_spec",
            "num_hosts",
            "actions",
        ]

    num_hosts = MethodColumn("Number of hosts", method_name="get_num_hosts")

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Edit",
                button_class="btn light:btn-primary dark:btn-outline mr-2",
                url=lambda obj: reverse("hosts:edit_data_source", args=[obj.pk]),
            ),
        ],
    )

    @staticmethod
    def get_num_hosts(obj: DataSource):
        return obj.hosts.count()


class HostsTable(BaseTable):
    class Meta:
        model = Host
        columns = [
            "fqdn",
            "os",
            "last_scan_date",
            "created_at",
            "customer",
            "status",
        ]
        column_type_overrides = {
            "fqdn": LinkColumn(
                url=lambda obj: reverse("hosts:detail", args=[obj.fqdn]),
                text=lambda obj: obj.fqdn,
            ),
            "last_scan_date": DateTimeColumn,
            "created_at": DateTimeColumn,
            "os": ModelValueColumn(
                header="Operating System",
                value_attr="os",
            ),
        }
        column_breakpoint_overrides = {
            "os": "lg",
            "last_scan_date": "xl",
            "created_at": "2xl",
            "customer": "lg",
        }
        no_data_message = "No hosts found. Please check your filters."
        no_data_message_wild_wasteland = "Oh no! Where have our hosts gone?"

    status = TemplatedColumn(
        "Status",
        template_name="hosts/host_list_parts/host_status.html",
    )
