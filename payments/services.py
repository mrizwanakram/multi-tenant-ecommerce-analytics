import stripe
import json
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import Payment, PaymentMethod, Refund, PaymentWebhook
from orders.models import Order


class StripeService:
    """Stripe payment processing service"""
    
    def __init__(self, tenant):
        self.tenant = tenant
        self.payment_method = PaymentMethod.objects.filter(
            tenant=tenant, 
            payment_type='stripe', 
            is_active=True
        ).first()
        
        if not self.payment_method:
            raise ValueError("No active Stripe payment method found for tenant")
        
        # Set Stripe API key from payment method configuration
        stripe.api_key = self.payment_method.configuration.get('secret_key')
    
    def create_payment_intent(self, order, amount, currency='USD'):
        """Create a Stripe payment intent"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency.lower(),
                metadata={
                    'order_id': str(order.id),
                    'tenant_id': str(self.tenant.id),
                },
                automatic_payment_methods={
                    'enabled': True,
                },
            )
            
            # Create payment record
            payment = Payment.objects.create(
                tenant=self.tenant,
                order=order,
                payment_method=self.payment_method,
                amount=amount,
                currency=currency,
                status='pending',
                external_payment_id=intent.id,
                payment_data={
                    'client_secret': intent.client_secret,
                    'intent_id': intent.id,
                }
            )
            
            return {
                'success': True,
                'payment_id': str(payment.id),
                'client_secret': intent.client_secret,
                'intent_id': intent.id,
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def confirm_payment(self, payment_intent_id):
        """Confirm a payment intent"""
        try:
            payment = Payment.objects.get(
                external_payment_id=payment_intent_id,
                tenant=self.tenant
            )
            
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == 'succeeded':
                payment.status = 'completed'
                payment.processed_at = timezone.now()
                payment.external_transaction_id = intent.latest_charge
                payment.save()
                
                # Update order status
                payment.order.status = 'paid'
                payment.order.save()
                
                return {
                    'success': True,
                    'payment_id': str(payment.id),
                    'status': 'completed',
                }
            else:
                payment.status = 'failed'
                payment.failure_reason = f"Payment failed: {intent.status}"
                payment.save()
                
                return {
                    'success': False,
                    'error': f"Payment failed: {intent.status}",
                }
                
        except Payment.DoesNotExist:
            return {
                'success': False,
                'error': 'Payment not found',
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def create_refund(self, payment, amount, reason):
        """Create a refund"""
        try:
            refund = stripe.Refund.create(
                payment_intent=payment.external_payment_id,
                amount=int(amount * 100),  # Convert to cents
                reason='requested_by_customer',
                metadata={
                    'refund_reason': reason,
                    'tenant_id': str(self.tenant.id),
                }
            )
            
            # Create refund record
            refund_record = Refund.objects.create(
                tenant=self.tenant,
                payment=payment,
                order=payment.order,
                amount=amount,
                reason=reason,
                status='completed' if refund.status == 'succeeded' else 'failed',
                external_refund_id=refund.id,
                refund_data={
                    'refund_id': refund.id,
                    'status': refund.status,
                },
                processed_at=timezone.now() if refund.status == 'succeeded' else None,
            )
            
            return {
                'success': True,
                'refund_id': str(refund_record.id),
                'status': refund_record.status,
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def handle_webhook(self, payload, signature):
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.payment_method.configuration.get('webhook_secret')
            )
            
            # Create webhook record
            webhook = PaymentWebhook.objects.create(
                tenant=self.tenant,
                payment_method=self.payment_method,
                event_type=event['type'],
                external_event_id=event['id'],
                payload=event,
                signature=signature,
            )
            
            # Process the event
            self._process_webhook_event(webhook, event)
            
            return {
                'success': True,
                'webhook_id': str(webhook.id),
            }
            
        except stripe.error.SignatureVerificationError:
            return {
                'success': False,
                'error': 'Invalid signature',
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def _process_webhook_event(self, webhook, event):
        """Process webhook event based on type"""
        try:
            if event['type'] == 'payment_intent.succeeded':
                self._handle_payment_succeeded(webhook, event)
            elif event['type'] == 'payment_intent.payment_failed':
                self._handle_payment_failed(webhook, event)
            elif event['type'] == 'charge.dispute.created':
                self._handle_dispute_created(webhook, event)
            
            webhook.processed = True
            webhook.processed_at = timezone.now()
            webhook.save()
            
        except Exception as e:
            webhook.processing_error = str(e)
            webhook.save()
    
    def _handle_payment_succeeded(self, webhook, event):
        """Handle payment succeeded event"""
        payment_intent_id = event['data']['object']['id']
        try:
            payment = Payment.objects.get(
                external_payment_id=payment_intent_id,
                tenant=self.tenant
            )
            payment.status = 'completed'
            payment.processed_at = timezone.now()
            payment.save()
            
            # Update order status
            payment.order.status = 'paid'
            payment.order.save()
            
        except Payment.DoesNotExist:
            pass
    
    def _handle_payment_failed(self, webhook, event):
        """Handle payment failed event"""
        payment_intent_id = event['data']['object']['id']
        try:
            payment = Payment.objects.get(
                external_payment_id=payment_intent_id,
                tenant=self.tenant
            )
            payment.status = 'failed'
            payment.failure_reason = event['data']['object'].get('last_payment_error', {}).get('message', 'Payment failed')
            payment.save()
            
        except Payment.DoesNotExist:
            pass
    
    def _handle_dispute_created(self, webhook, event):
        """Handle dispute created event"""
        # Implement dispute handling logic
        pass


class PayPalService:
    """PayPal payment processing service"""
    
    def __init__(self, tenant):
        self.tenant = tenant
        self.payment_method = PaymentMethod.objects.filter(
            tenant=tenant, 
            payment_type='paypal', 
            is_active=True
        ).first()
        
        if not self.payment_method:
            raise ValueError("No active PayPal payment method found for tenant")
    
    def create_payment(self, order, amount, currency='USD'):
        """Create a PayPal payment"""
        # Implement PayPal payment creation
        # This would integrate with PayPal's API
        pass
    
    def execute_payment(self, payment_id, payer_id):
        """Execute a PayPal payment"""
        # Implement PayPal payment execution
        pass


class PaymentServiceFactory:
    """Factory for creating payment services"""
    
    @staticmethod
    def get_service(tenant, payment_type):
        if payment_type == 'stripe':
            return StripeService(tenant)
        elif payment_type == 'paypal':
            return PayPalService(tenant)
        else:
            raise ValueError(f"Unsupported payment type: {payment_type}")



