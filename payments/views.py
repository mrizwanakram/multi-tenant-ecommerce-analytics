from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import PaymentMethod, Payment, Refund, PaymentWebhook
from .serializers import (
    PaymentMethodSerializer, PaymentSerializer, RefundSerializer, PaymentWebhookSerializer
)
from .services import PaymentServiceFactory
import json


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """ViewSet for managing payment methods"""
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(tenant=self.request.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing payments"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(tenant=self.request.tenant)
    
    @action(detail=False, methods=['post'])
    def create_payment_intent(self, request):
        """Create a payment intent for an order"""
        order_id = request.data.get('order_id')
        payment_type = request.data.get('payment_type', 'stripe')
        
        try:
            from orders.models import Order
            order = Order.objects.get(id=order_id, tenant=request.tenant)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            service = PaymentServiceFactory.get_service(request.tenant, payment_type)
            result = service.create_payment_intent(
                order=order,
                amount=order.total_amount,
                currency=request.data.get('currency', 'USD')
            )
            
            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Payment creation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """Confirm a payment"""
        payment = self.get_object()
        
        try:
            service = PaymentServiceFactory.get_service(
                request.tenant, 
                payment.payment_method.payment_type
            )
            result = service.confirm_payment(payment.external_payment_id)
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response(
                {'error': f'Payment confirmation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """Create a refund for a payment"""
        payment = self.get_object()
        amount = request.data.get('amount')
        reason = request.data.get('reason', 'Customer requested refund')
        
        if not amount:
            return Response(
                {'error': 'Refund amount is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = PaymentServiceFactory.get_service(
                request.tenant, 
                payment.payment_method.payment_type
            )
            result = service.create_refund(
                payment=payment,
                amount=float(amount),
                reason=reason
            )
            
            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response(
                {'error': f'Refund creation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefundViewSet(viewsets.ModelViewSet):
    """ViewSet for managing refunds"""
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Refund.objects.filter(tenant=self.request.tenant)


class PaymentWebhookViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing payment webhooks"""
    queryset = PaymentWebhook.objects.all()
    serializer_class = PaymentWebhookSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PaymentWebhook.objects.filter(tenant=self.request.tenant)


# Webhook endpoints for external payment providers
def stripe_webhook(request, tenant_id):
    """Stripe webhook endpoint"""
    try:
        from tenants.models import Tenant
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return HttpResponse('Tenant not found', status=404)
    
    payload = request.body
    signature = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    
    try:
        service = PaymentServiceFactory.get_service(tenant, 'stripe')
        result = service.handle_webhook(payload, signature)
        
        if result['success']:
            return HttpResponse('Webhook processed successfully', status=200)
        else:
            return HttpResponse(f'Webhook processing failed: {result["error"]}', status=400)
            
    except Exception as e:
        return HttpResponse(f'Webhook error: {str(e)}', status=500)


def paypal_webhook(request, tenant_id):
    """PayPal webhook endpoint"""
    try:
        from tenants.models import Tenant
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return HttpResponse('Tenant not found', status=404)
    
    # Implement PayPal webhook handling
    return HttpResponse('PayPal webhook endpoint', status=200)