from django.urls import reverse

from hosts.models import Host
from main.easy_tables import BaseTable, DateTimeColumn, LinkColumn, TemplatedColumn


class HostsTable(BaseTable):
    class Meta:
        model = Host
        columns = [
            'fqdn',
            'os',
            'last_scan_date',
            'created_at',
            'department',
            'status',
        ]
        column_type_overrides = {
            'fqdn': LinkColumn(
                url=lambda obj: reverse('hosts:detail', args=[obj.fqdn]),
                text=lambda obj: obj.fqdn,
            ),
            'last_scan_date': DateTimeColumn,
            'created_at': DateTimeColumn,
        }
        column_breakpoint_overrides = {
            'os': 'lg',
            'last_scan_date': 'xl',
            'created_at': '2xl',
            'department': 'lg',
        }
        no_data_message = "No hosts found. Please check your filters."
        no_data_message_wild_wasteland = "Oh no! Where have our hosts gone?"

    status = TemplatedColumn(
        "Status",
        template_name='hosts/list_parts/host_status.html',
    )