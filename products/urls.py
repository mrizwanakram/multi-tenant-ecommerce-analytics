from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, ProductImageViewSet, ProductVariantViewSet
from .upload_views import (
    upload_product_image, delete_product_image, set_primary_image, bulk_upload_images
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'product-images', ProductImageViewSet)
router.register(r'product-variants', ProductVariantViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # File upload endpoints
    path('products/<uuid:product_id>/upload-image/', upload_product_image, name='upload-product-image'),
    path('products/<uuid:product_id>/images/<int:image_id>/delete/', delete_product_image, name='delete-product-image'),
    path('products/<uuid:product_id>/images/<int:image_id>/set-primary/', set_primary_image, name='set-primary-image'),
    path('products/<uuid:product_id>/bulk-upload/', bulk_upload_images, name='bulk-upload-images'),
]
