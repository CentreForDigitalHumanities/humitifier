from rest_framework.routers import DefaultRouter

from api.views import HostsViewSet

router = DefaultRouter()
router.register(r'hosts', HostsViewSet, basename='hosts')
urlpatterns = router.urls