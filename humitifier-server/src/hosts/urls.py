from django.urls import path

from .views import (
    ArchiveHostView,
    DataSourceCreateView,
    DataSourceEditView,
    DataSourcesView,
    HostDetailView,
    HostExportView,
    HostsListView,
    HostsRawDownloadView,
    TasksView,
)

app_name = "hosts"

urlpatterns = [
    path("", HostsListView.as_view(), name="list"),
    path("export/", HostExportView.as_view(), name="export"),
    path("host/<fqdn>/", HostDetailView.as_view(), name="detail"),
    path("host/<fqdn>/raw/", HostsRawDownloadView.as_view(), name="download_raw"),
    path("host/<fqdn>/archive/", ArchiveHostView.as_view(), name="archive"),
    path("tasks/", TasksView.as_view(), name="tasks"),
    path("data-sources/", DataSourcesView.as_view(), name="data_sources"),
    path(
        "data-sources/create/",
        DataSourceCreateView.as_view(),
        name="create_data_source",
    ),
    path(
        "data-sources/<pk>/edit/", DataSourceEditView.as_view(), name="edit_data_source"
    ),
]
