from django.urls import path

from .views import DataSourcesView, ExportView, HostDetailView, HostsListView, \
    HostsRawDownloadView, ScanProfilesView, TasksView

app_name = 'hosts'

urlpatterns = [
    path("", HostsListView.as_view(), name="list"),
    path("host/<fqdn>/", HostDetailView.as_view(), name="detail"),
    path("host/<fqdn>/raw/", HostsRawDownloadView.as_view(),
         name="download_raw"),
    path("export/", ExportView.as_view(), name="export"),
    path("tasks/", TasksView.as_view(), name="tasks"),
    path("scan-profiles/", ScanProfilesView.as_view(), name="scan_profiles"),
    path("data-sources/", DataSourcesView.as_view(), name="data_sources"),
]
