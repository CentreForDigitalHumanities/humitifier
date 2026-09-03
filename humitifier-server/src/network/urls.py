from django.urls import path
from . import views

app_name = "network"

urlpatterns = [
    path("overview/", views.IPInfoListView.as_view(), name="overview"),
    path("list/", views.NetworkListView.as_view(), name="list"),
    path("create/", views.NetworkCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.NetworkUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.NetworkDeleteView.as_view(), name="delete"),
]
