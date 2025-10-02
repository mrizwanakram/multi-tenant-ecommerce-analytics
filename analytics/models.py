from django.db import models
from django.contrib.auth.models import User
from tenants.models import Tenant
from products.models import Product
from customers.models import Customer
from orders.models import Order
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
import json


class PriceHistory(models.Model):
    """Price history for products"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_history'
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.price}"


class StockEvent(models.Model):
    """Stock events for inventory tracking"""
    EVENT_TYPES = [
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('restock', 'Restock'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    quantity_change = models.IntegerField()  # Positive for restock, negative for sale
    quantity_after = models.IntegerField()
    reference_id = models.CharField(max_length=100, blank=True)  # Order ID, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_events'
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.event_type} - {self.quantity_change}"


class PriceEvent(models.Model):
    """Price events for anomaly detection"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_events')
    old_price = models.DecimalField(max_digits=10, decimal_places=2)
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    change_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_anomaly = models.BooleanField(default=False)
    anomaly_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_events'
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['is_anomaly', 'created_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.change_percentage}%"


class IngestionJob(models.Model):
    """Track bulk ingestion jobs for idempotency"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='ingestion_jobs')
    idempotency_key = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    error_details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ingestion_jobs'
        indexes = [
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.idempotency_key}"


class MaterializedView(models.Model):
    """Materialized views for pre-aggregated data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='materialized_views')
    view_name = models.CharField(max_length=100)
    group_by = models.CharField(max_length=50)  # day, hour, product, category
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'materialized_views'
        indexes = [
            models.Index(fields=['tenant', 'view_name', 'group_by']),
            models.Index(fields=['tenant', 'period_start', 'period_end']),
        ]
        unique_together = ['tenant', 'view_name', 'group_by', 'period_start', 'period_end']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.view_name} - {self.group_by}"


class ExportJob(models.Model):
    """Track export jobs for resumable downloads"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='export_jobs')
    format = models.CharField(max_length=10)  # csv, parquet
    filters = models.JSONField(default=dict)
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0)  # 0-100
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'export_jobs'
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.format} - {self.status}"