from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, Avg
from .models import Category, Product, ProductImage, ProductVariant
from .serializers import (
    CategorySerializer, ProductSerializer, ProductListSerializer,
    ProductCreateSerializer, ProductImageSerializer, ProductVariantSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Category management"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter categories by tenant"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return Category.objects.filter(tenant=self.request.tenant)
        return Category.objects.none()


class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet for Product management"""
    queryset = Product.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active', 'is_digital']
    search_fields = ['name', 'description', 'sku', 'tags']
    ordering_fields = ['name', 'price', 'created_at', 'stock_quantity']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter products by tenant"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return Product.objects.filter(tenant=self.request.tenant).select_related('category')
        return Product.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return ProductListSerializer
        elif self.action == 'create':
            return ProductCreateSerializer
        return ProductSerializer
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get product analytics"""
        product = self.get_object()
        
        # Get analytics data
        analytics_data = {
            'product_id': product.id,
            'product_name': product.name,
            'total_views': getattr(product.analytics, 'total_views', 0),
            'unique_views': getattr(product.analytics, 'unique_views', 0),
            'add_to_cart_count': getattr(product.analytics, 'add_to_cart_count', 0),
            'purchase_count': getattr(product.analytics, 'purchase_count', 0),
            'conversion_rate': getattr(product.analytics, 'conversion_rate', 0),
            'total_revenue': getattr(product.analytics, 'total_revenue', 0),
            'total_units_sold': getattr(product.analytics, 'total_units_sold', 0),
            'average_rating': getattr(product.analytics, 'average_rating', 0),
            'total_reviews': getattr(product.analytics, 'total_reviews', 0),
        }
        
        return Response(analytics_data)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock"""
        queryset = self.get_queryset().filter(
            stock_quantity__lte=models.F('min_stock_level')
        )
        serializer = ProductListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_selling(self, request):
        """Get top selling products"""
        queryset = self.get_queryset().order_by('-analytics__total_units_sold')[:10]
        serializer = ProductListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def categories_summary(self, request):
        """Get product count by category"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            categories = Category.objects.filter(tenant=self.request.tenant).annotate(
                product_count=Count('products')
            ).values('name', 'product_count')
            return Response(categories)
        return Response([])


class ProductImageViewSet(viewsets.ModelViewSet):
    """ViewSet for ProductImage management"""
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter images by tenant through product"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return ProductImage.objects.filter(product__tenant=self.request.tenant)
        return ProductImage.objects.none()


class ProductVariantViewSet(viewsets.ModelViewSet):
    """ViewSet for ProductVariant management"""
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter variants by tenant through product"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return ProductVariant.objects.filter(product__tenant=self.request.tenant)
        return ProductVariant.objects.none()