from django.contrib.auth.views import LoginView
from django.urls import path

from .views import AccessProfilesView, CreateSolisUserView, CreateUserView, \
    DashboardView, \
    DeActivateUserView, \
    EditUserView, HomeRedirectView, \
    OAuthApplicationsView, \
    SetPasswordView, UserProfileView, UsersView

app_name = 'main'

urlpatterns = [
    path("", HomeRedirectView.as_view(), name="home"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("user_profile/", UserProfileView.as_view(), name="user_profile"),
    path("users/", UsersView.as_view(), name="users"),
    path("users/create/", CreateUserView.as_view(), name="create_user"),
    path("users/create-solis/", CreateSolisUserView.as_view(),
         name="create_solis_user"),
    path("users/<int:pk>/edit/", EditUserView.as_view(),
         name="edit_user"),
    path("users/<int:pk>/change-password/", SetPasswordView.as_view(),
         name="user_change_password"),
    path("users/<int:pk>/deactivate/", DeActivateUserView.as_view(), name="deactivate_user"),
    path("access-profiles/", AccessProfilesView.as_view(), name="access_profiles"),
    path("oauth-applications/", OAuthApplicationsView.as_view(), name="oauth_applications"),

    path("login", LoginView.as_view(), name="login"),
]
