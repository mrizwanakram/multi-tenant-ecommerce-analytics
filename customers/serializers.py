from rest_framework import serializers
from .models import Customer, CustomerSegment, CustomerNote
from tenants.models import Tenant


class CustomerNoteSerializer(serializers.ModelSerializer):
    """Serializer for CustomerNote model"""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = CustomerNote
        fields = [
            'id', 'note', 'created_by_username', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CustomerSegmentSerializer(serializers.ModelSerializer):
    """Serializer for CustomerSegment model"""
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = CustomerSegment
        fields = [
            'id', 'name', 'description', 'tenant', 'tenant_name',
            'criteria', 'customer_count', 'total_spent', 'average_order_value',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""
    notes = CustomerNoteSerializer(many=True, read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    full_name = serializers.CharField(read_only=True)
    full_address = serializers.CharField(read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone',
            'tenant', 'tenant_name', 'address_line_1', 'address_line_2',
            'city', 'state', 'postal_code', 'country', 'full_address',
            'is_active', 'is_vip', 'date_of_birth', 'gender',
            'newsletter_subscribed', 'sms_subscribed', 'created_at',
            'updated_at', 'last_login', 'notes'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login']


class CustomerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating customers"""
    
    class Meta:
        model = Customer
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'address_line_1',
            'address_line_2', 'city', 'state', 'postal_code', 'country',
            'is_active', 'is_vip', 'date_of_birth', 'gender',
            'newsletter_subscribed', 'sms_subscribed'
        ]
    
    def create(self, validated_data):
        # Add tenant from request context
        validated_data['tenant'] = self.context['request'].tenant
        return super().create(validated_data)


class CustomerListSerializer(serializers.ModelSerializer):
    """Simplified serializer for customer lists"""
    full_name = serializers.CharField(read_only=True)
    total_orders = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'email', 'full_name', 'phone', 'is_active', 'is_vip',
            'created_at', 'last_login', 'total_orders', 'total_spent'
        ]
    
    def get_total_orders(self, obj):
        return obj.orders.count()
    
    def get_total_spent(self, obj):
        return sum(order.total_amount for order in obj.orders.all())


class CustomerAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for customer analytics"""
    analytics = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'email', 'first_name', 'last_name', 'analytics'
        ]
    
    def get_analytics(self, obj):
        try:
            analytics = obj.analytics
            return {
                'total_orders': analytics.total_orders,
                'total_spent': float(analytics.total_spent),
                'average_order_value': float(analytics.average_order_value),
                'first_order_date': analytics.first_order_date,
                'last_order_date': analytics.last_order_date,
                'days_since_last_order': analytics.days_since_last_order,
                'unique_products_purchased': analytics.unique_products_purchased,
                'favorite_category': analytics.favorite_category,
                'total_page_views': analytics.total_page_views,
                'total_sessions': analytics.total_sessions,
                'rfm_segment': analytics.rfm_segment
            }
        except:
            return None



