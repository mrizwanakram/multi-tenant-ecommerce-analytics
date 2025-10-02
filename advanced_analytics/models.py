from django.db import models
from django.contrib.auth.models import User
from tenants.models import Tenant
from products.models import Product, Category
from orders.models import Order
from customers.models import Customer
from analytics.models import SalesMetric
import uuid
from decimal import Decimal


class DashboardWidget(models.Model):
    """Dashboard widgets configuration"""
    WIDGET_TYPES = [
        ('chart', 'Chart'),
        ('metric', 'Metric'),
        ('table', 'Table'),
        ('gauge', 'Gauge'),
        ('map', 'Map'),
        ('trend', 'Trend'),
    ]
    
    CHART_TYPES = [
        ('line', 'Line Chart'),
        ('bar', 'Bar Chart'),
        ('pie', 'Pie Chart'),
        ('area', 'Area Chart'),
        ('scatter', 'Scatter Plot'),
        ('heatmap', 'Heatmap'),
        ('funnel', 'Funnel Chart'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='advanced_dashboard_widgets')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    chart_type = models.CharField(max_length=20, choices=CHART_TYPES, blank=True)
    
    # Widget configuration
    config = models.JSONField(default=dict)  # Chart configuration, filters, etc.
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=4)
    height = models.IntegerField(default=3)
    
    # Data source configuration
    data_source = models.CharField(max_length=100)  # Which API endpoint to use
    refresh_interval = models.IntegerField(default=300)  # Refresh interval in seconds
    
    # Status
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['position_y', 'position_x']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class RealTimeMetric(models.Model):
    """Real-time metrics for live dashboard updates"""
    METRIC_TYPES = [
        ('revenue', 'Revenue'),
        ('orders', 'Orders'),
        ('customers', 'Customers'),
        ('conversion', 'Conversion Rate'),
        ('cart_abandonment', 'Cart Abandonment'),
        ('page_views', 'Page Views'),
        ('sessions', 'Sessions'),
        ('bounce_rate', 'Bounce Rate'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='advanced_realtime_metrics')
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    
    # Metric values
    current_value = models.DecimalField(max_digits=15, decimal_places=2)
    previous_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    change_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Time period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Additional data
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['tenant', 'metric_type', 'period_start']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.metric_type} - {self.current_value}"


class AnalyticsReport(models.Model):
    """Generated analytics reports"""
    REPORT_TYPES = [
        ('sales', 'Sales Report'),
        ('customer', 'Customer Report'),
        ('product', 'Product Report'),
        ('revenue', 'Revenue Report'),
        ('custom', 'Custom Report'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='advanced_analytics_reports')
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    
    # Report configuration
    filters = models.JSONField(default=dict)  # Applied filters
    date_range_start = models.DateTimeField()
    date_range_end = models.DateTimeField()
    
    # Report data
    data = models.JSONField(default=dict)  # Generated report data
    summary = models.JSONField(default=dict)  # Report summary
    
    # File attachments
    pdf_file = models.FileField(upload_to='reports/pdf/', blank=True, null=True)
    excel_file = models.FileField(upload_to='reports/excel/', blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, default='generating', choices=[
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class DataExport(models.Model):
    """Data export jobs"""
    EXPORT_TYPES = [
        ('orders', 'Orders'),
        ('customers', 'Customers'),
        ('products', 'Products'),
        ('analytics', 'Analytics'),
        ('custom', 'Custom Query'),
    ]
    
    EXPORT_FORMATS = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
        ('pdf', 'PDF'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='advanced_data_exports')
    name = models.CharField(max_length=200)
    export_type = models.CharField(max_length=20, choices=EXPORT_TYPES)
    export_format = models.CharField(max_length=10, choices=EXPORT_FORMATS)
    
    # Export configuration
    filters = models.JSONField(default=dict)
    fields = models.JSONField(default=list)  # Fields to include
    date_range_start = models.DateTimeField(null=True, blank=True)
    date_range_end = models.DateTimeField(null=True, blank=True)
    
    # Export file
    file = models.FileField(upload_to='exports/', blank=True, null=True)
    file_size = models.BigIntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class AlertRule(models.Model):
    """Alert rules for monitoring metrics"""
    ALERT_TYPES = [
        ('threshold', 'Threshold Alert'),
        ('anomaly', 'Anomaly Detection'),
        ('trend', 'Trend Alert'),
        ('custom', 'Custom Alert'),
    ]
    
    COMPARISON_OPERATORS = [
        ('gt', 'Greater Than'),
        ('gte', 'Greater Than or Equal'),
        ('lt', 'Less Than'),
        ('lte', 'Less Than or Equal'),
        ('eq', 'Equal'),
        ('ne', 'Not Equal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='advanced_alert_rules')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    
    # Alert configuration
    metric_type = models.CharField(max_length=50)  # Which metric to monitor
    comparison_operator = models.CharField(max_length=5, choices=COMPARISON_OPERATORS)
    threshold_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Alert settings
    is_active = models.BooleanField(default=True)
    cooldown_minutes = models.IntegerField(default=60)  # Cooldown between alerts
    
    # Notification settings
    email_recipients = models.JSONField(default=list)  # List of email addresses
    webhook_url = models.URLField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class AlertLog(models.Model):
    """Alert trigger logs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='advanced_alert_logs')
    alert_rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='logs')
    
    # Alert details
    metric_value = models.DecimalField(max_digits=15, decimal_places=2)
    threshold_value = models.DecimalField(max_digits=15, decimal_places=2)
    message = models.TextField()
    
    # Status
    status = models.CharField(max_length=20, default='sent', choices=[
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('ignored', 'Ignored'),
    ])
    
    # Timestamps
    triggered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-triggered_at']
    
    def __str__(self):
        return f"{self.alert_rule.name} - {self.triggered_at}"