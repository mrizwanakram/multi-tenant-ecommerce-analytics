from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, RefundViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet)
router.register(r'refunds', RefundViewSet)

urlpatterns = [
    path('', include(router.urls)),
]



