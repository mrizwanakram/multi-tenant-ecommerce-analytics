from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentMethodViewSet, PaymentViewSet, RefundViewSet, 
    PaymentWebhookViewSet, stripe_webhook, paypal_webhook
)

router = DefaultRouter()
router.register(r'payment-methods', PaymentMethodViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'refunds', RefundViewSet)
router.register(r'webhooks', PaymentWebhookViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Webhook endpoints for external payment providers
    path('webhooks/stripe/<uuid:tenant_id>/', stripe_webhook, name='stripe-webhook'),
    path('webhooks/paypal/<uuid:tenant_id>/', paypal_webhook, name='paypal-webhook'),
]



