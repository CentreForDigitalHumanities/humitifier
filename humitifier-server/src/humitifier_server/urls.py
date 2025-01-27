"""
URL configuration for humitifier_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from mozilla_django_oidc.urls import OIDCAuthenticateClass, OIDCCallbackClass
from mozilla_django_oidc.views import OIDCLogoutView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("hosts/", include("hosts.urls")),
    path("", include("main.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns

if hasattr(settings, "OIDC_RP_CLIENT_ID"):
    # Custom OIDC url conf, because we're hijacking an existing RP config
    urlpatterns += [
        path(
            "redirect_uri",  # NO TRAILING SLASH. IMPORTANT!
            OIDCCallbackClass.as_view(),
            name="oidc_authentication_callback",
        ),
        path(
            "oidc/authenticate/",
            OIDCAuthenticateClass.as_view(),
            name="oidc_authentication_init",
        ),
        path("oidc/logout/", OIDCLogoutView.as_view(), name="oidc_logout"),
    ]
else:
    # URL name is wrong obviously, can't be bothered to fix that
    urlpatterns += [
        path("logout", LogoutView.as_view(), name="oidc_logout"),
    ]