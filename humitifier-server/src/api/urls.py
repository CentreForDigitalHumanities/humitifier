from django.urls import path

from .views import UploadScans

app_name = 'api'

urlpatterns = [
    path("upload_scans/", UploadScans.as_view(), name="upload_scans"),
]
