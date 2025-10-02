"""
Real-time Price Sensing API with Anomaly Detection
Implements rate limiting, idempotency, and streaming anomaly detection
"""

import json
import time
import uuid
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from django.http import JsonResponse, StreamingHttpResponse
from django.core.cache import cache
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Tenant, Product, PriceEvent, PriceHistory
import logging

logger = logging.getLogger(__name__)


class PriceAnomalyDetector:
    """Detect price anomalies using statistical methods"""
    
    def __init__(self, anomaly_threshold: float = 0.2):  # 20% change threshold
        self.anomaly_threshold = anomaly_threshold
    
    def detect_anomaly(self, old_price: Decimal, new_price: Decimal) -> Dict[str, Any]:
        """Detect if price change is anomalous"""
        if old_price == 0:
            return {'is_anomaly': False, 'change_percentage': 0.0, 'reason': 'No previous price'}
        
        change_percentage = float((new_price - old_price) / old_price)
        is_anomaly = abs(change_percentage) >= self.anomaly_threshold
        
        reason = None
        if is_anomaly:
            if change_percentage > 0:
                reason = f"Price increased by {change_percentage:.2%} (threshold: {self.anomaly_threshold:.2%})"
            else:
                reason = f"Price decreased by {abs(change_percentage):.2%} (threshold: {self.anomaly_threshold:.2%})"
        
        return {
            'is_anomaly': is_anomaly,
            'change_percentage': change_percentage,
            'reason': reason
        }


class RateLimiter:
    """Rate limiter for price events per product and tenant"""
    
    def __init__(self):
        self.cache_timeout = 3600  # 1 hour
    
    def is_rate_limited(self, tenant_id: str, product_id: str, limit: int = 100) -> bool:
        """Check if rate limit is exceeded"""
        key = f"rate_limit:{tenant_id}:{product_id}"
        current_count = cache.get(key, 0)
        return current_count >= limit
    
    def increment_rate_limit(self, tenant_id: str, product_id: str, limit: int = 100):
        """Increment rate limit counter"""
        key = f"rate_limit:{tenant_id}:{product_id}"
        current_count = cache.get(key, 0)
        cache.set(key, current_count + 1, self.cache_timeout)
    
    def get_rate_limit_info(self, tenant_id: str, product_id: str, limit: int = 100) -> Dict[str, Any]:
        """Get current rate limit information"""
        key = f"rate_limit:{tenant_id}:{product_id}"
        current_count = cache.get(key, 0)
        return {
            'current_count': current_count,
            'limit': limit,
            'remaining': max(0, limit - current_count),
            'reset_time': time.time() + self.cache_timeout
        }


class PriceEventProcessor:
    """Process price events with idempotency and anomaly detection"""
    
    def __init__(self, tenant_id: str, product_id: str):
        self.tenant_id = tenant_id
        self.product_id = product_id
        self.rate_limiter = RateLimiter()
        self.anomaly_detector = PriceAnomalyDetector()
    
    def process_price_event(self, event_data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        """Process a price event with idempotency and anomaly detection"""
        try:
            # Check rate limiting
            if self.rate_limiter.is_rate_limited(self.tenant_id, self.product_id):
                return {
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'rate_limit_info': self.rate_limiter.get_rate_limit_info(self.tenant_id, self.product_id)
                }
            
            # Check idempotency
            if self._is_duplicate_event(idempotency_key):
                return {
                    'success': True,
                    'message': 'Event already processed (idempotent)',
                    'idempotency_key': idempotency_key
                }
            
            # Get current product price
            try:
                product = Product.objects.get(id=self.product_id, tenant_id=self.tenant_id)
                old_price = product.price
            except Product.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Product not found'
                }
            
            new_price = Decimal(str(event_data['price']))
            
            # Detect anomaly
            anomaly_result = self.anomaly_detector.detect_anomaly(old_price, new_price)
            
            # Create price event record
            price_event = PriceEvent.objects.create(
                product=product,
                old_price=old_price,
                new_price=new_price,
                change_percentage=anomaly_result['change_percentage'],
                is_anomaly=anomaly_result['is_anomaly'],
                anomaly_reason=anomaly_result['reason'] or '',
                created_at=datetime.now()
            )
            
            # Update product price
            product.price = new_price
            product.updated_at = datetime.now()
            product.save()
            
            # Create price history entry
            PriceHistory.objects.create(
                product=product,
                price=new_price,
                created_at=datetime.now()
            )
            
            # Store idempotency key
            self._store_idempotency_key(idempotency_key, price_event.id)
            
            # Increment rate limit
            self.rate_limiter.increment_rate_limit(self.tenant_id, self.product_id)
            
            return {
                'success': True,
                'price_event_id': str(price_event.id),
                'old_price': float(old_price),
                'new_price': float(new_price),
                'change_percentage': anomaly_result['change_percentage'],
                'is_anomaly': anomaly_result['is_anomaly'],
                'anomaly_reason': anomaly_result['reason'],
                'idempotency_key': idempotency_key
            }
            
        except Exception as e:
            logger.error(f"Error processing price event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _is_duplicate_event(self, idempotency_key: str) -> bool:
        """Check if event with idempotency key already exists"""
        cache_key = f"price_event_idempotency:{idempotency_key}"
        return cache.get(cache_key) is not None
    
    def _store_idempotency_key(self, idempotency_key: str, price_event_id: str):
        """Store idempotency key to prevent duplicates"""
        cache_key = f"price_event_idempotency:{idempotency_key}"
        cache.set(cache_key, price_event_id, 3600)  # 1 hour expiration


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def price_event_webhook(request, tenant_id, product_id):
    """
    Price event webhook endpoint
    Accepts price update events with rate limiting and anomaly detection
    """
    try:
        # Get idempotency key
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response(
                {'error': 'Idempotency-Key header is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse request data
        try:
            event_data = request.data
        except Exception:
            return Response(
                {'error': 'Invalid JSON data'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate required fields
        if 'price' not in event_data:
            return Response(
                {'error': 'price field is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process price event
        processor = PriceEventProcessor(tenant_id, product_id)
        result = processor.process_price_event(event_data, idempotency_key)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            if 'Rate limit exceeded' in result.get('error', ''):
                return Response(result, status=status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Error in price_event_webhook: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_price_anomalies(request, tenant_id, product_id):
    """
    Get price anomalies for a product
    Streaming endpoint for recent anomalies
    """
    try:
        # Parse query parameters
        limit = int(request.GET.get('limit', 100))
        hours = int(request.GET.get('hours', 24))
        stream = request.GET.get('stream', 'false').lower() == 'true'
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Get anomalies
        anomalies = PriceEvent.objects.filter(
            product_id=product_id,
            product__tenant_id=tenant_id,
            is_anomaly=True,
            created_at__gte=start_time,
            created_at__lte=end_time
        ).order_by('-created_at')[:limit]
        
        # Convert to list of dictionaries
        anomaly_data = []
        for anomaly in anomalies:
            anomaly_data.append({
                'id': str(anomaly.id),
                'product_id': str(anomaly.product_id),
                'old_price': float(anomaly.old_price),
                'new_price': float(anomaly.new_price),
                'change_percentage': float(anomaly.change_percentage),
                'anomaly_reason': anomaly.anomaly_reason,
                'created_at': anomaly.created_at.isoformat()
            })
        
        if stream:
            # Return streaming response
            def generate_anomalies():
                yield json.dumps({
                    'product_id': product_id,
                    'tenant_id': tenant_id,
                    'time_range': {
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat()
                    },
                    'anomalies': anomaly_data
                }) + '\n'
            
            response = StreamingHttpResponse(
                generate_anomalies(),
                content_type='application/x-ndjson'
            )
            response['Content-Disposition'] = f'attachment; filename="price_anomalies_{product_id}.jsonl"'
            return response
        else:
            # Return regular JSON response
            return Response({
                'product_id': product_id,
                'tenant_id': tenant_id,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'anomalies': anomaly_data,
                'count': len(anomaly_data)
            })
    
    except Exception as e:
        logger.error(f"Error in get_price_anomalies: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_rate_limit_info(request, tenant_id, product_id):
    """Get rate limit information for a product"""
    try:
        rate_limiter = RateLimiter()
        limit = int(request.GET.get('limit', 100))
        
        info = rate_limiter.get_rate_limit_info(tenant_id, product_id, limit)
        
        return Response({
            'tenant_id': tenant_id,
            'product_id': product_id,
            'rate_limit': info
        })
    
    except Exception as e:
        logger.error(f"Error in get_rate_limit_info: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_rate_limit(request, tenant_id, product_id):
    """Reset rate limit for a product (admin function)"""
    try:
        key = f"rate_limit:{tenant_id}:{product_id}"
        cache.delete(key)
        
        return Response({
            'message': 'Rate limit reset successfully',
            'tenant_id': tenant_id,
            'product_id': product_id
        })
    
    except Exception as e:
        logger.error(f"Error in reset_rate_limit: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



