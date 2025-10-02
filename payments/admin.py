from django.contrib import admin
from .models import PaymentMethod, Payment, Refund, PaymentWebhook


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'payment_type', 'is_active', 'created_at']
    list_filter = ['payment_type', 'is_active', 'created_at']
    search_fields = ['name', 'tenant__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'order', 'payment_method', 'amount', 'currency', 
        'status', 'created_at', 'processed_at'
    ]
    list_filter = ['status', 'currency', 'payment_method__payment_type', 'created_at']
    search_fields = ['id', 'order__order_number', 'external_payment_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_at']
    raw_id_fields = ['order', 'payment_method']


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'payment', 'order', 'amount', 'status', 
        'created_at', 'processed_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'payment__id', 'order__order_number', 'external_refund_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_at']
    raw_id_fields = ['payment', 'order']


@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'tenant', 'payment_method', 'event_type', 
        'processed', 'received_at'
    ]
    list_filter = ['event_type', 'processed', 'received_at']
    search_fields = ['id', 'tenant__name', 'external_event_id']
    readonly_fields = ['id', 'received_at', 'processed_at']
    raw_id_fields = ['tenant', 'payment_method']