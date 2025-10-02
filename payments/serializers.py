from rest_framework import serializers
from .models import PaymentMethod, Payment, Refund, PaymentWebhook


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for PaymentMethod model"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'payment_type', 'is_active', 'configuration',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_configuration(self, value):
        """Validate payment method configuration"""
        payment_type = self.initial_data.get('payment_type')
        
        if payment_type == 'stripe':
            required_fields = ['secret_key', 'publishable_key']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(f"Stripe requires {field}")
        
        elif payment_type == 'paypal':
            required_fields = ['client_id', 'client_secret']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(f"PayPal requires {field}")
        
        return value


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_name = serializers.CharField(source='order.customer.full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'payment_method', 'payment_method_name',
            'amount', 'currency', 'status', 'external_payment_id',
            'external_transaction_id', 'payment_data', 'failure_reason',
            'created_at', 'updated_at', 'processed_at', 'order_number',
            'customer_name'
        ]
        read_only_fields = [
            'id', 'external_payment_id', 'external_transaction_id',
            'created_at', 'updated_at', 'processed_at'
        ]
    
    def validate_amount(self, value):
        """Validate payment amount"""
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero")
        return value


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for Refund model"""
    payment_amount = serializers.DecimalField(source='payment.amount', max_digits=10, decimal_places=2, read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'order', 'amount', 'reason', 'status',
            'external_refund_id', 'refund_data', 'failure_reason',
            'created_at', 'updated_at', 'processed_at', 'payment_amount',
            'order_number'
        ]
        read_only_fields = [
            'id', 'external_refund_id', 'created_at', 'updated_at', 'processed_at'
        ]
    
    def validate_amount(self, value):
        """Validate refund amount"""
        if value <= 0:
            raise serializers.ValidationError("Refund amount must be greater than zero")
        return value
    
    def validate(self, data):
        """Validate refund against payment amount"""
        payment = data.get('payment')
        amount = data.get('amount')
        
        if payment and amount:
            # Calculate total refunded amount for this payment
            total_refunded = Refund.objects.filter(
                payment=payment, 
                status__in=['completed', 'processing']
            ).exclude(id=self.instance.id if self.instance else None).aggregate(
                total=models.Sum('amount')
            )['total'] or 0
            
            if total_refunded + amount > payment.amount:
                raise serializers.ValidationError(
                    f"Refund amount ({total_refunded + amount}) cannot exceed payment amount ({payment.amount})"
                )
        
        return data


class PaymentWebhookSerializer(serializers.ModelSerializer):
    """Serializer for PaymentWebhook model"""
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    
    class Meta:
        model = PaymentWebhook
        fields = [
            'id', 'payment_method', 'payment_method_name', 'event_type',
            'external_event_id', 'payload', 'processed', 'processing_error',
            'received_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'external_event_id', 'payload', 'processed',
            'processing_error', 'received_at', 'processed_at'
        ]


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating payment intents"""
    order_id = serializers.UUIDField()
    payment_type = serializers.ChoiceField(choices=['stripe', 'paypal'], default='stripe')
    currency = serializers.CharField(max_length=3, default='USD')
    
    def validate_order_id(self, value):
        """Validate that order exists and belongs to tenant"""
        # This will be validated in the view
        return value


class ConfirmPaymentSerializer(serializers.Serializer):
    """Serializer for confirming payments"""
    payment_intent_id = serializers.CharField(max_length=255)
    
    def validate_payment_intent_id(self, value):
        """Validate payment intent ID format"""
        if not value or len(value) < 10:
            raise serializers.ValidationError("Invalid payment intent ID")
        return value


class CreateRefundSerializer(serializers.Serializer):
    """Serializer for creating refunds"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.CharField(max_length=500, required=False)
    
    def validate_amount(self, value):
        """Validate refund amount"""
        if value <= 0:
            raise serializers.ValidationError("Refund amount must be greater than zero")
        return value



