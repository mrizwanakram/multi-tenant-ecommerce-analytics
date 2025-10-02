from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg
from .models import AnalyticsEvent, SalesMetric, ProductAnalytics, CustomerAnalytics, DashboardWidget
from .serializers import (
    AnalyticsEventSerializer, SalesMetricSerializer, ProductAnalyticsSerializer,
    CustomerAnalyticsSerializer, DashboardWidgetSerializer
)


class AnalyticsEventViewSet(viewsets.ModelViewSet):
    """ViewSet for AnalyticsEvent management"""
    queryset = AnalyticsEvent.objects.all()
    serializer_class = AnalyticsEventSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter events by tenant"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return AnalyticsEvent.objects.filter(tenant=self.request.tenant)
        return AnalyticsEvent.objects.none()


class SalesMetricViewSet(viewsets.ModelViewSet):
    """ViewSet for SalesMetric management"""
    queryset = SalesMetric.objects.all()
    serializer_class = SalesMetricSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter metrics by tenant"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return SalesMetric.objects.filter(tenant=self.request.tenant)
        return SalesMetric.objects.none()


class ProductAnalyticsViewSet(viewsets.ModelViewSet):
    """ViewSet for ProductAnalytics management"""
    queryset = ProductAnalytics.objects.all()
    serializer_class = ProductAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter analytics by tenant through product"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return ProductAnalytics.objects.filter(product__tenant=self.request.tenant)
        return ProductAnalytics.objects.none()


class CustomerAnalyticsViewSet(viewsets.ModelViewSet):
    """ViewSet for CustomerAnalytics management"""
    queryset = CustomerAnalytics.objects.all()
    serializer_class = CustomerAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter analytics by tenant through customer"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return CustomerAnalytics.objects.filter(customer__tenant=self.request.tenant)
        return CustomerAnalytics.objects.none()


class DashboardWidgetViewSet(viewsets.ModelViewSet):
    """ViewSet for DashboardWidget management"""
    queryset = DashboardWidget.objects.all()
    serializer_class = DashboardWidgetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter widgets by tenant"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return DashboardWidget.objects.filter(tenant=self.request.tenant)
        return DashboardWidget.objects.none()


class AnalyticsSummaryViewSet(viewsets.ViewSet):
    """ViewSet for analytics summary and reports"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get analytics overview for the tenant"""
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        tenant = request.tenant
        
        # Calculate basic metrics
        total_revenue = tenant.orders.aggregate(total=Sum('total_amount'))['total'] or 0
        total_orders = tenant.orders.count()
        total_customers = tenant.customers.count()
        total_products = tenant.products.count()
        average_order_value = tenant.orders.aggregate(avg=Avg('total_amount'))['avg'] or 0
        
        overview_data = {
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'total_customers': total_customers,
            'total_products': total_products,
            'average_order_value': float(average_order_value)
        }
        
        return Response(overview_data)