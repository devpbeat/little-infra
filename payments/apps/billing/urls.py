from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PagoparWebhookView, PaymentInitiationView, PaymentResultView, PaymentViewSet

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("payments", PaymentInitiationView.as_view(), name="payment-initiate"),
    path(
        "payments/result/<str:gateway_order_id>",
        PaymentResultView.as_view(),
        name="payment-result",
    ),
    path("webhooks/pagopar", PagoparWebhookView.as_view(), name="webhook-pagopar"),
] + router.urls
