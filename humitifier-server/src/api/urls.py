from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from oauth2_provider import views as oauth_views

from .views import (
    CreateOAuthApplicationView,
    DeleteOAuthApplicationView,
    EditOAuthApplicationView,
    DatastoreSyncView,
    UploadScans,
    OAuthApplicationsView,
)
from .router import urlpatterns as router_urlpatterns

app_name = "api"

urlpatterns = [
    # API Endpoints
    path("upload_scans/", UploadScans.as_view(), name="upload_scans"),
    path("inventory_sync/", DatastoreSyncView.as_view(), name="inventory_sync"),
    # OAuth2
    path("oauth/authorize/", oauth_views.AuthorizationView.as_view(), name="authorize"),
    path("oauth/token/", oauth_views.TokenView.as_view(), name="token"),
    path(
        "oauth/revoke_token/",
        oauth_views.RevokeTokenView.as_view(),
        name="revoke-token",
    ),
    path(
        "oauth/introspect/",
        oauth_views.IntrospectTokenView.as_view(),
        name="introspect",
    ),
    path(
        "oauth/applications/",
        OAuthApplicationsView.as_view(),
        name="oauth_applications",
    ),
    path(
        "oauth/applications/create/",
        CreateOAuthApplicationView.as_view(),
        name="create_oauth_application",
    ),
    path(
        "oauth/applications/<int:pk>/edit/",
        EditOAuthApplicationView.as_view(),
        name="edit_oauth_application",
    ),
    path(
        "oauth/applications/<int:pk>/delete/",
        DeleteOAuthApplicationView.as_view(),
        name="delete_oauth_application",
    ),
    # OpenAPI schema + Redoc
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/redoc/",
        SpectacularRedocView.as_view(url_name="api:schema"),
        name="redoc",
    ),
] + router_urlpatterns
