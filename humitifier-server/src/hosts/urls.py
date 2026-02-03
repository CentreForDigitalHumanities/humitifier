from django.urls import path

from .views import (
    ArchiveHostView,
    DataSourceCreateView,
    DataSourceEditView,
    DataSourcesView,
    HostCreateView, HostDetailView,
    HostExportView,
    HostScanSpecUpdateView, HostUpdateView, HostsListView,
    HostsRawDownloadView,
    AdvancedSearchView,
    SavedSearchListView,
    SavedSearchCreateView,
    SavedSearchUpdateView,
    SavedSearchDeleteView,
    SavedSearchLoadView,
)

app_name = "hosts"

urlpatterns = [
    path("", HostsListView.as_view(), name="list"),
    path("export/", HostExportView.as_view(), name="export"),
    path("advanced_search/", AdvancedSearchView.as_view(), name="advanced_search"),
    path("saved_searches/", SavedSearchListView.as_view(), name="saved_searches"),
    path("saved_searches/create/", SavedSearchCreateView.as_view(), name="saved_search_create"),
    path("saved_searches/<int:pk>/edit/", SavedSearchUpdateView.as_view(), name="saved_search_edit"),
    path("saved_searches/<int:pk>/delete/", SavedSearchDeleteView.as_view(), name="saved_search_delete"),
    path("saved_searches/<int:pk>/load/", SavedSearchLoadView.as_view(), name="saved_search_load"),
    path("host/new/", HostCreateView.as_view(), name="create"),
    path("host/<fqdn>/", HostDetailView.as_view(), name="detail"),
    path("host/<fqdn>/raw/", HostsRawDownloadView.as_view(), name="download_raw"),
    path("host/<fqdn>/edit/", HostUpdateView.as_view(), name="edit"),
    path("host/<fqdn>/change-scan-spec/", HostScanSpecUpdateView.as_view(), name="change-scan-spec"),
    path("host/<fqdn>/archive/", ArchiveHostView.as_view(), name="archive"),
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
