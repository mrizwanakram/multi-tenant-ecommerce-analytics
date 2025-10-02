from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusHistory, Refund
from products.models import Product
from customers.models import Customer


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model"""
    product_name = serializers.CharField(read_only=True)
    product_sku = serializers.CharField(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_variant', 'quantity', 'unit_price',
            'total_price', 'product_name', 'product_sku'
        ]
        read_only_fields = ['id', 'product_name', 'product_sku']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for OrderStatusHistory model"""
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'status', 'notes', 'changed_by_username', 'changed_at'
        ]
        read_only_fields = ['id', 'changed_at']


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for Refund model"""
    processed_by_username = serializers.CharField(source='processed_by.username', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'amount', 'reason', 'status', 'processed_by_username',
            'processed_at', 'created_at'
        ]
        read_only_fields = ['id', 'processed_at', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model"""
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    refunds = RefundSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name', 'customer_email',
            'tenant', 'tenant_name', 'status', 'total_amount', 'subtotal',
            'tax_amount', 'shipping_amount', 'discount_amount', 'payment_status',
            'payment_method', 'payment_reference', 'shipping_address',
            'billing_address', 'notes', 'internal_notes', 'created_at',
            'updated_at', 'shipped_at', 'delivered_at', 'items', 'status_history',
            'refunds'
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at', 'shipped_at', 'delivered_at'
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders"""
    items = OrderItemSerializer(many=True)
    
    class Meta:
        model = Order
        fields = [
            'customer', 'status', 'payment_method', 'shipping_address',
            'billing_address', 'notes', 'items'
        ]
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Add tenant from request context
        validated_data['tenant'] = self.context['request'].tenant
        
        # Calculate totals
        subtotal = sum(item['quantity'] * item['unit_price'] for item in items_data)
        tax_amount = subtotal * 0.08  # 8% tax
        shipping_amount = 9.99 if subtotal < 50 else 0
        total_amount = subtotal + tax_amount + shipping_amount
        
        validated_data.update({
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'shipping_amount': shipping_amount,
            'total_amount': total_amount,
            'payment_status': 'pending'
        })
        
        order = Order.objects.create(**validated_data)
        
        # Create order items
        for item_data in items_data:
            product = item_data['product']
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_sku=product.sku,
                **item_data
            )
        
        return order


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for order lists"""
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'customer_email',
            'status', 'total_amount', 'payment_status', 'created_at', 'item_count'
        ]
    
    def get_item_count(self, obj):
        return obj.items.count()


class OrderUpdateStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating order status"""
    notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Order
        fields = ['status', 'notes']
    
    def update(self, instance, validated_data):
        # Create status history entry
        OrderStatusHistory.objects.create(
            order=instance,
            status=validated_data['status'],
            notes=validated_data.get('notes', ''),
            changed_by=self.context['request'].user
        )
        
        # Update order status
        instance.status = validated_data['status']
        instance.save()
        
        return instance



