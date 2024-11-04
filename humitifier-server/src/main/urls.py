from django.contrib.auth.views import LoginView
from django.urls import path

from .views import AccessProfilesView, DashboardView, HomeRedirectView, \
    OAuthApplicationsView, \
    UsersView

app_name = 'main'

urlpatterns = [
    path("", HomeRedirectView.as_view(), name="home"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("users/", UsersView.as_view(), name="users"),
    path("access-profiles/", AccessProfilesView.as_view(), name="access_profiles"),
    path("oauth-applications/", OAuthApplicationsView.as_view(), name="oauth_applications"),

    path("login", LoginView.as_view(), name="login"),
]
