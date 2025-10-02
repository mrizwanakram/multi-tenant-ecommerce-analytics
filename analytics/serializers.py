from rest_framework import serializers
from .models import AnalyticsEvent, SalesMetric, ProductAnalytics, CustomerAnalytics, DashboardWidget
from products.models import Product
from customers.models import Customer
from tenants.models import Tenant


class AnalyticsEventSerializer(serializers.ModelSerializer):
    """Serializer for AnalyticsEvent model"""
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = AnalyticsEvent
        fields = [
            'id', 'tenant', 'tenant_name', 'event_type', 'user', 'user_username',
            'customer', 'customer_name', 'session_id', 'ip_address', 'user_agent',
            'event_data', 'page_url', 'referrer', 'product', 'product_name',
            'order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SalesMetricSerializer(serializers.ModelSerializer):
    """Serializer for SalesMetric model"""
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    top_selling_product_name = serializers.CharField(source='top_selling_product.name', read_only=True)
    
    class Meta:
        model = SalesMetric
        fields = [
            'id', 'tenant', 'tenant_name', 'date', 'total_orders', 'total_revenue',
            'total_units_sold', 'average_order_value', 'new_customers',
            'returning_customers', 'total_customers', 'unique_products_sold',
            'top_selling_product', 'top_selling_product_name', 'conversion_rate',
            'cart_abandonment_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for ProductAnalytics model"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = ProductAnalytics
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'total_views',
            'unique_views', 'add_to_cart_count', 'purchase_count',
            'conversion_rate', 'total_revenue', 'total_units_sold',
            'average_rating', 'total_reviews', 'last_viewed', 'last_purchased',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for CustomerAnalytics model"""
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    
    class Meta:
        model = CustomerAnalytics
        fields = [
            'id', 'customer', 'customer_name', 'customer_email', 'total_orders',
            'total_spent', 'average_order_value', 'first_order_date',
            'last_order_date', 'days_since_last_order', 'unique_products_purchased',
            'favorite_category', 'total_page_views', 'total_sessions',
            'average_session_duration', 'recency_score', 'frequency_score',
            'monetary_score', 'rfm_segment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """Serializer for DashboardWidget model"""
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = DashboardWidget
        fields = [
            'id', 'tenant', 'tenant_name', 'name', 'widget_type', 'position_x',
            'position_y', 'width', 'height', 'config', 'filters', 'is_visible',
            'refresh_interval', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalyticsSummarySerializer(serializers.Serializer):
    """Serializer for analytics summary data"""
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    total_products = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    cart_abandonment_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    new_customers = serializers.IntegerField()
    returning_customers = serializers.IntegerField()
    top_selling_products = serializers.ListField()
    recent_orders = serializers.ListField()
    sales_trend = serializers.ListField()
    customer_segments = serializers.ListField()


class RevenueAnalyticsSerializer(serializers.Serializer):
    """Serializer for revenue analytics"""
    period = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders = serializers.IntegerField()
    customers = serializers.IntegerField()
    growth_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


class ProductPerformanceSerializer(serializers.Serializer):
    """Serializer for product performance analytics"""
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    sku = serializers.CharField()
    total_views = serializers.IntegerField()
    total_sales = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    rank = serializers.IntegerField()


class CustomerSegmentAnalyticsSerializer(serializers.Serializer):
    """Serializer for customer segment analytics"""
    segment_name = serializers.CharField()
    customer_count = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)



