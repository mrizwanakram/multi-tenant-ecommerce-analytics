from django.urls import path, include
from . import ingest_views, search_views, aggregation_views, price_views, export_views, stock_views, observability_views

urlpatterns = [
    # Bulk ingest endpoints
    path('v1/ingest/orders/', ingest_views.bulk_ingest_orders, name='bulk_ingest_orders'),
    path('v1/ingest/status/<str:idempotency_key>/', ingest_views.get_ingestion_status, name='ingestion_status'),
    path('v1/ingest/upload-token/', ingest_views.create_upload_token, name='create_upload_token'),
    path('v1/ingest/resume/<str:upload_token>/', ingest_views.resume_upload, name='resume_upload'),
    
    # High-throughput search endpoints
    path('v1/tenants/<uuid:tenant_id>/orders/search/', search_views.search_orders, name='search_orders'),
    path('v1/tenants/<uuid:tenant_id>/orders/search/ndjson/', search_views.search_orders_ndjson, name='search_orders_ndjson'),
    path('v1/tenants/<uuid:tenant_id>/search/explanation/', search_views.get_search_explanation, name='search_explanation'),
    
    # Aggregation endpoints
    path('v1/tenants/<uuid:tenant_id>/metrics/sales/', aggregation_views.get_sales_metrics, name='sales_metrics'),
    path('v1/tenants/<uuid:tenant_id>/materialized-views/invalidate/', aggregation_views.invalidate_materialized_views, name='invalidate_views'),
    path('v1/tenants/<uuid:tenant_id>/aggregation/explanation/', aggregation_views.get_aggregation_explanation, name='aggregation_explanation'),
    
    # Price sensing endpoints
    path('v1/tenants/<uuid:tenant_id>/products/<uuid:product_id>/price-event/', price_views.price_event_webhook, name='price_event_webhook'),
    path('v1/tenants/<uuid:tenant_id>/products/<uuid:product_id>/price-anomalies/', price_views.get_price_anomalies, name='price_anomalies'),
    path('v1/tenants/<uuid:tenant_id>/products/<uuid:product_id>/rate-limit/', price_views.get_rate_limit_info, name='rate_limit_info'),
    path('v1/tenants/<uuid:tenant_id>/products/<uuid:product_id>/reset-rate-limit/', price_views.reset_rate_limit, name='reset_rate_limit'),
    
    # Export endpoints
    path('v1/tenants/<uuid:tenant_id>/reports/export/', export_views.create_export, name='create_export'),
    path('v1/tenants/<uuid:tenant_id>/reports/export/<str:job_id>/stream/', export_views.stream_export, name='stream_export'),
    path('v1/tenants/<uuid:tenant_id>/reports/export/<str:job_id>/status/', export_views.get_export_status, name='export_status'),
    path('v1/tenants/<uuid:tenant_id>/reports/export/<str:job_id>/download/', export_views.download_export, name='download_export'),
    
    # Stock management endpoints
    path('v1/tenants/<uuid:tenant_id>/stock/bulk_update/', stock_views.bulk_stock_update, name='bulk_stock_update'),
    path('v1/tenants/<uuid:tenant_id>/products/<uuid:product_id>/stock/events/', stock_views.get_stock_events, name='stock_events'),
    path('v1/tenants/<uuid:tenant_id>/products/<uuid:product_id>/stock/', stock_views.get_product_stock, name='product_stock'),
    path('v1/tenants/<uuid:tenant_id>/stock/test-concurrent/', stock_views.test_concurrent_updates, name='test_concurrent_updates'),
    
    # Observability endpoints
    path('metrics/', observability_views.get_metrics, name='metrics'),
    path('health/', observability_views.get_health_status, name='health_status'),
    path('performance/', observability_views.get_performance_metrics, name='performance_metrics'),
    path('backpressure/', observability_views.get_backpressure_status, name='backpressure_status'),
    path('queue-length/', observability_views.update_queue_length, name='update_queue_length'),
]