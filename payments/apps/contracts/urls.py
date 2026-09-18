from rest_framework.routers import DefaultRouter

from .views import ContractTemplateViewSet, ContractViewSet

router = DefaultRouter()
router.register("contracts", ContractViewSet, basename="contract")
router.register(
    "contract-templates", ContractTemplateViewSet, basename="contract-template"
)

urlpatterns = router.urls
