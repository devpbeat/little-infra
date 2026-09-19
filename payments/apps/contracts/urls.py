from rest_framework.routers import DefaultRouter

from .views import ContractTemplateViewSet, ContractViewSet, PublicContractSigningView

router = DefaultRouter()
router.register("contracts", ContractViewSet, basename="contract")
router.register(
    "contract-templates", ContractTemplateViewSet, basename="contract-template"
)
router.register(
    "public/contract-signing", PublicContractSigningView, basename="contract-signing"
)

urlpatterns = router.urls
