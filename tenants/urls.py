from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet, TenantUserViewSet

router = DefaultRouter()
router.register(r'tenants', TenantViewSet)
router.register(r'tenant-users', TenantUserViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

