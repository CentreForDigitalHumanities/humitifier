from django.urls import path

from .views import (
    CreateScanSpecView,
    DeleteScanSpecView,
    EditScanSpecView,
    ScanSpecView,
)

app_name = "scanning"

urlpatterns = [
    path("scan-specs/", ScanSpecView.as_view(), name="scan_specs"),
    path("scan-specs/create/", CreateScanSpecView.as_view(), name="create_scan_spec"),
    path(
        "scan-specs/<int:pk>/edit/", EditScanSpecView.as_view(), name="edit_scan_spec"
    ),
    path(
        "scan-specs/<int:pk>/delete/",
        DeleteScanSpecView.as_view(),
        name="delete_scan_spec",
    ),
]
