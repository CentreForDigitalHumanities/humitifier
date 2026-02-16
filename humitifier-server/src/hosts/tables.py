from django.urls import reverse

from hosts.models import Host, DataSource, SavedSearch
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
            "hypervisor",
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
            "hypervisor": "xl",
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


class SavedSearchesTable(BaseTable):
    class Meta:
        model = SavedSearch
        columns = [
            "title",
            "description",
            "creator",
            "visibility",
            "updated_at",
            "actions",
        ]
        column_type_overrides = {
            "title": LinkColumn(
                url=lambda obj: reverse("hosts:saved_search_load", args=[obj.pk]),
                text=lambda obj: obj.title,
            ),
            "updated_at": DateTimeColumn,
        }
        column_breakpoint_overrides = {
            "description": "lg",
            "visibility": "md",
            "updated_at": "xl",
        }
        no_data_message = "No saved searches yet. Create one from the advanced search page."

    description = ModelValueColumn(
        "Description",
        value_attr="description",
        empty_value="—",
    )

    visibility = TemplatedColumn(
        "Visibility",
        template_name="hosts/saved_search_list_parts/visibility.html",
    )

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Load",
                button_class="btn btn-sm btn-outline mr-2",
                url=lambda obj: reverse("hosts:saved_search_load", args=[obj.pk]),
            ),
            ButtonColumn(
                text="Edit",
                button_class="btn btn-sm btn-outline mr-2",
                url=lambda obj: reverse("hosts:saved_search_edit", args=[obj.pk]),
                condition=lambda obj, request: obj.creator == request.user or obj.is_public,
            ),
            ButtonColumn(
                text="Delete",
                button_class="btn btn-sm btn-outline text-red-600 dark:text-red-400",
                url=lambda obj: reverse("hosts:saved_search_delete", args=[obj.pk]),
                is_form_submit=True,
                confirm_message="Are you sure you want to delete this saved search?",
                condition=lambda obj, request: obj.creator == request.user or obj.is_public,
            ),
        ],
    )
