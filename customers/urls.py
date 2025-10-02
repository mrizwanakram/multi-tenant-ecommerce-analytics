from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, CustomerSegmentViewSet, CustomerNoteViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'customer-segments', CustomerSegmentViewSet)
router.register(r'customer-notes', CustomerNoteViewSet)

urlpatterns = [
    path('', include(router.urls)),
]



