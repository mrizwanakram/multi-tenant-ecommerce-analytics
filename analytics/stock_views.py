"""
Conflict Resolution & Transactional Batch Updates
Implements row-level locking and conflict resolution for stock updates
"""

import json
import time
import uuid
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime
from django.http import JsonResponse
from django.db import transaction, connection
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Tenant, Product, StockEvent
import logging

logger = logging.getLogger(__name__)


class ConflictResolver:
    """Handle conflict resolution for concurrent stock updates"""
    
    CONFLICT_RESOLUTION_STRATEGIES = {
        'last_write_wins': 'last_write_wins',
        'merge': 'merge',
        'reject': 'reject'
    }
    
    def __init__(self, strategy: str = 'last_write_wins'):
        self.strategy = strategy
        if strategy not in self.CONFLICT_RESOLUTION_STRATEGIES:
            raise ValueError(f"Invalid conflict resolution strategy: {strategy}")
    
    def resolve_conflict(self, product_id: str, current_stock: int, 
                        new_stock: int, quantity_change: int) -> Dict[str, Any]:
        """Resolve conflict between current and new stock values"""
        if self.strategy == 'last_write_wins':
            return {
                'resolved_stock': new_stock,
                'strategy_used': 'last_write_wins',
                'conflict_resolved': True
            }
        
        elif self.strategy == 'merge':
            # Apply additive delta
            resolved_stock = current_stock + quantity_change
            return {
                'resolved_stock': resolved_stock,
                'strategy_used': 'merge',
                'conflict_resolved': True,
                'delta_applied': quantity_change
            }
        
        elif self.strategy == 'reject':
            return {
                'resolved_stock': current_stock,
                'strategy_used': 'reject',
                'conflict_resolved': False,
                'reason': 'Conflict detected, update rejected'
            }
        
        return {
            'resolved_stock': current_stock,
            'strategy_used': 'unknown',
            'conflict_resolved': False,
            'reason': 'Unknown strategy'
        }


class StockUpdateProcessor:
    """Process stock updates with conflict resolution"""
    
    def __init__(self, tenant_id: str, conflict_strategy: str = 'last_write_wins'):
        self.tenant_id = tenant_id
        self.conflict_resolver = ConflictResolver(conflict_strategy)
        self.tenant = self._get_tenant()
    
    def _get_tenant(self) -> Optional[Tenant]:
        """Get tenant by ID"""
        try:
            return Tenant.objects.get(id=self.tenant_id)
        except Tenant.DoesNotExist:
            return None
    
    def process_bulk_update(self, stock_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process bulk stock update with conflict resolution"""
        if not self.tenant:
            return {
                'success': False,
                'error': 'Tenant not found',
                'results': []
            }
        
        results = []
        successful_updates = 0
        failed_updates = 0
        
        # Group events by product for atomic processing
        events_by_product = {}
        for event in stock_events:
            product_id = event.get('product_id')
            if product_id not in events_by_product:
                events_by_product[product_id] = []
            events_by_product[product_id].append(event)
        
        # Process each product atomically
        for product_id, product_events in events_by_product.items():
            try:
                result = self._process_product_events(product_id, product_events)
                results.append(result)
                
                if result['success']:
                    successful_updates += 1
                else:
                    failed_updates += 1
                    
            except Exception as e:
                logger.error(f"Error processing product {product_id}: {e}")
                results.append({
                    'product_id': product_id,
                    'success': False,
                    'error': str(e),
                    'events_processed': 0
                })
                failed_updates += 1
        
        return {
            'success': failed_updates == 0,
            'total_products': len(events_by_product),
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'results': results
        }
    
    def _process_product_events(self, product_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process events for a single product with row-level locking"""
        try:
            # Get product with row-level lock
            with transaction.atomic():
                # Use SELECT FOR UPDATE to lock the row
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, price FROM products WHERE id = %s AND tenant_id = %s FOR UPDATE",
                        [product_id, self.tenant_id]
                    )
                    product_row = cursor.fetchone()
                    
                    if not product_row:
                        return {
                            'product_id': product_id,
                            'success': False,
                            'error': 'Product not found',
                            'events_processed': 0
                        }
                    
                    # Get current stock from latest stock event
                    cursor.execute("""
                        SELECT quantity_after 
                        FROM stock_events 
                        WHERE product_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """, [product_id])
                    
                    stock_row = cursor.fetchone()
                    current_stock = stock_row[0] if stock_row else 0
                    
                    # Process events
                    events_processed = 0
                    final_stock = current_stock
                    
                    for event in events:
                        event_type = event.get('event_type', 'adjustment')
                        quantity_change = event.get('quantity_change', 0)
                        reference_id = event.get('reference_id', '')
                        
                        # Calculate new stock
                        new_stock = final_stock + quantity_change
                        
                        # Check for conflicts (simplified - in production, you'd check for concurrent updates)
                        if self._has_conflict(product_id, current_stock):
                            # Resolve conflict
                            conflict_result = self.conflict_resolver.resolve_conflict(
                                product_id, current_stock, new_stock, quantity_change
                            )
                            
                            if not conflict_result['conflict_resolved']:
                                continue  # Skip this event
                            
                            new_stock = conflict_result['resolved_stock']
                        
                        # Create stock event
                        stock_event = StockEvent.objects.create(
                            product_id=product_id,
                            event_type=event_type,
                            quantity_change=quantity_change,
                            quantity_after=new_stock,
                            reference_id=reference_id,
                            created_at=datetime.now()
                        )
                        
                        final_stock = new_stock
                        events_processed += 1
                    
                    return {
                        'product_id': product_id,
                        'success': True,
                        'initial_stock': current_stock,
                        'final_stock': final_stock,
                        'events_processed': events_processed,
                        'conflict_resolution_strategy': self.conflict_resolver.strategy
                    }
        
        except Exception as e:
            logger.error(f"Error processing product events for {product_id}: {e}")
            return {
                'product_id': product_id,
                'success': False,
                'error': str(e),
                'events_processed': 0
            }
    
    def _has_conflict(self, product_id: str, expected_stock: int) -> bool:
        """Check if there's a conflict with concurrent updates"""
        # Simplified conflict detection
        # In production, you'd check for recent updates or use version numbers
        cache_key = f"stock_update:{product_id}"
        last_update = cache.get(cache_key)
        
        if last_update and time.time() - last_update < 1.0:  # 1 second window
            return True
        
        # Update cache
        cache.set(cache_key, time.time(), 10)  # 10 second expiration
        return False


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def bulk_stock_update(request, tenant_id):
    """
    Bulk stock update with conflict resolution
    Supports different conflict resolution strategies
    """
    try:
        # Parse request data
        stock_events = request.data.get('events', [])
        conflict_strategy = request.data.get('conflict_strategy', 'last_write_wins')
        
        if not stock_events:
            return Response(
                {'error': 'No stock events provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate events
        for event in stock_events:
            required_fields = ['product_id', 'event_type', 'quantity_change']
            if not all(field in event for field in required_fields):
                return Response(
                    {'error': f'Missing required fields in event: {event}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Process bulk update
        processor = StockUpdateProcessor(tenant_id, conflict_strategy)
        result = processor.process_bulk_update(stock_events)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_207_MULTI_STATUS)  # Partial success
    
    except Exception as e:
        logger.error(f"Error in bulk_stock_update: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stock_events(request, tenant_id, product_id):
    """Get stock events for a product"""
    try:
        # Parse query parameters
        limit = int(request.GET.get('limit', 100))
        event_type = request.GET.get('event_type')
        
        # Build query
        events = StockEvent.objects.filter(
            product_id=product_id,
            product__tenant_id=tenant_id
        )
        
        if event_type:
            events = events.filter(event_type=event_type)
        
        events = events.order_by('-created_at')[:limit]
        
        # Convert to list
        events_data = []
        for event in events:
            events_data.append({
                'id': str(event.id),
                'product_id': str(event.product_id),
                'event_type': event.event_type,
                'quantity_change': event.quantity_change,
                'quantity_after': event.quantity_after,
                'reference_id': event.reference_id,
                'created_at': event.created_at.isoformat()
            })
        
        return Response({
            'product_id': product_id,
            'events': events_data,
            'count': len(events_data)
        })
    
    except Exception as e:
        logger.error(f"Error in get_stock_events: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_stock(request, tenant_id, product_id):
    """Get current stock for a product"""
    try:
        # Get latest stock event
        latest_event = StockEvent.objects.filter(
            product_id=product_id,
            product__tenant_id=tenant_id
        ).order_by('-created_at').first()
        
        if not latest_event:
            return Response({
                'product_id': product_id,
                'current_stock': 0,
                'last_updated': None
            })
        
        return Response({
            'product_id': product_id,
            'current_stock': latest_event.quantity_after,
            'last_updated': latest_event.created_at.isoformat(),
            'last_event_type': latest_event.event_type
        })
    
    except Exception as e:
        logger.error(f"Error in get_product_stock: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_concurrent_updates(request, tenant_id):
    """Test concurrent updates to demonstrate conflict resolution"""
    try:
        # This is a test endpoint to demonstrate conflict resolution
        product_id = request.data.get('product_id')
        num_concurrent_updates = request.data.get('num_updates', 5)
        
        if not product_id:
            return Response(
                {'error': 'product_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create concurrent update events
        events = []
        for i in range(num_concurrent_updates):
            events.append({
                'product_id': product_id,
                'event_type': 'adjustment',
                'quantity_change': 1,
                'reference_id': f'concurrent_test_{i}'
            })
        
        # Process with different strategies
        strategies = ['last_write_wins', 'merge', 'reject']
        results = {}
        
        for strategy in strategies:
            processor = StockUpdateProcessor(tenant_id, strategy)
            result = processor.process_bulk_update(events)
            results[strategy] = result
        
        return Response({
            'product_id': product_id,
            'test_results': results,
            'message': 'Concurrent update test completed'
        })
    
    except Exception as e:
        logger.error(f"Error in test_concurrent_updates: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



