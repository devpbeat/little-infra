from rest_framework.routers import DefaultRouter

from .views import ConsumingAppViewSet

router = DefaultRouter()
router.register("apps", ConsumingAppViewSet, basename="consuming-app")

urlpatterns = router.urls
