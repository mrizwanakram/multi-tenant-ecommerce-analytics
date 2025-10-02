from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    DashboardWidget, RealTimeMetric, AnalyticsReport, 
    DataExport, AlertRule, AlertLog
)
from .serializers import (
    DashboardWidgetSerializer, RealTimeMetricSerializer, 
    AnalyticsReportSerializer, DataExportSerializer, 
    AlertRuleSerializer, AlertLogSerializer
)
from .services import AdvancedAnalyticsService, DataExportService
import json


class DashboardWidgetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing dashboard widgets"""
    queryset = DashboardWidget.objects.all()
    serializer_class = DashboardWidgetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DashboardWidget.objects.filter(tenant=self.request.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)
    
    @action(detail=True, methods=['post'])
    def get_data(self, request, pk=None):
        """Get data for a specific widget"""
        widget = self.get_object()
        service = AdvancedAnalyticsService(request.tenant)
        
        try:
            if widget.data_source == 'realtime_metrics':
                data = service.get_realtime_metrics()
            elif widget.data_source == 'sales_chart':
                start_date = request.data.get('start_date', timezone.now() - timedelta(days=30))
                end_date = request.data.get('end_date', timezone.now())
                group_by = request.data.get('group_by', 'day')
                data = service.generate_sales_chart_data(start_date, end_date, group_by)
            else:
                data = {}
            
            return Response({
                'widget_id': str(widget.id),
                'data': data,
                'config': widget.config
            })
        except Exception as e:
            return Response(
                {'error': f'Error generating widget data: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RealTimeMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for real-time metrics"""
    queryset = RealTimeMetric.objects.all()
    serializer_class = RealTimeMetricSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RealTimeMetric.objects.filter(tenant=self.request.tenant)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current real-time metrics"""
        service = AdvancedAnalyticsService(request.tenant)
        metrics = service.get_realtime_metrics()
        
        return Response(metrics)


class AnalyticsReportViewSet(viewsets.ModelViewSet):
    """ViewSet for analytics reports"""
    queryset = AnalyticsReport.objects.all()
    serializer_class = AnalyticsReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AnalyticsReport.objects.filter(tenant=self.request.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class DataExportViewSet(viewsets.ModelViewSet):
    """ViewSet for data exports"""
    queryset = DataExport.objects.all()
    serializer_class = DataExportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DataExport.objects.filter(tenant=self.request.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class AlertRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for alert rules"""
    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AlertRule.objects.filter(tenant=self.request.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class AlertLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for alert logs"""
    queryset = AlertLog.objects.all()
    serializer_class = AlertLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AlertLog.objects.filter(tenant=self.request.tenant)


# API endpoints for chart data
def sales_chart_data(request, tenant_id):
    """Get sales chart data"""
    try:
        from tenants.models import Tenant
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return JsonResponse({'error': 'Tenant not found'}, status=404)
    
    start_date = request.GET.get('start_date', timezone.now() - timedelta(days=30))
    end_date = request.GET.get('end_date', timezone.now())
    group_by = request.GET.get('group_by', 'day')
    
    service = AdvancedAnalyticsService(tenant)
    data = service.generate_sales_chart_data(start_date, end_date, group_by)
    
    return JsonResponse(data)


def product_performance_data(request, tenant_id):
    """Get product performance data"""
    try:
        from tenants.models import Tenant
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return JsonResponse({'error': 'Tenant not found'}, status=404)
    
    start_date = request.GET.get('start_date', timezone.now() - timedelta(days=30))
    end_date = request.GET.get('end_date', timezone.now())
    limit = int(request.GET.get('limit', 10))
    
    service = AdvancedAnalyticsService(tenant)
    data = service.generate_product_performance_data(start_date, end_date, limit)
    
    return JsonResponse({'data': data})


def customer_segmentation_data(request, tenant_id):
    """Get customer segmentation data"""
    try:
        from tenants.models import Tenant
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return JsonResponse({'error': 'Tenant not found'}, status=404)
    
    start_date = request.GET.get('start_date', timezone.now() - timedelta(days=30))
    end_date = request.GET.get('end_date', timezone.now())
    
    service = AdvancedAnalyticsService(tenant)
    data = service.generate_customer_segmentation_data(start_date, end_date)
    
    return JsonResponse(data)