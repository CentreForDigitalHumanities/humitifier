from django.urls import path

from .views import (
    AlertAcknowledgmentCreateView,
    AlertAcknowledgementsListView,
    AlertAcknowledgmentDeleteView,
)

app_name = "alerting"

urlpatterns = [
    path(
        "acknowledgments/",
        AlertAcknowledgementsListView.as_view(),
        name="acknowledgments_list",
    ),
    path(
        "<int:alert_id>/acknowledge/",
        AlertAcknowledgmentCreateView.as_view(),
        name="acknowledge",
    ),
    path(
        "<int:pk>/delete/",
        AlertAcknowledgmentDeleteView.as_view(),
        name="delete_acknowledgment",
    ),
]
