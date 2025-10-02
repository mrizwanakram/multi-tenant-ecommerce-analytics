from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DashboardWidgetViewSet, RealTimeMetricViewSet, AnalyticsReportViewSet,
    DataExportViewSet, AlertRuleViewSet, AlertLogViewSet,
    sales_chart_data, product_performance_data, customer_segmentation_data
)

router = DefaultRouter()
router.register(r'dashboard-widgets', DashboardWidgetViewSet)
router.register(r'realtime-metrics', RealTimeMetricViewSet)
router.register(r'analytics-reports', AnalyticsReportViewSet)
router.register(r'data-exports', DataExportViewSet)
router.register(r'alert-rules', AlertRuleViewSet)
router.register(r'alert-logs', AlertLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Chart data endpoints
    path('charts/sales/<uuid:tenant_id>/', sales_chart_data, name='sales-chart-data'),
    path('charts/products/<uuid:tenant_id>/', product_performance_data, name='product-performance-data'),
    path('charts/customers/<uuid:tenant_id>/', customer_segmentation_data, name='customer-segmentation-data'),
]



