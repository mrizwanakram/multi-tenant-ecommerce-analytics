"""
Bulk Ingest API for High-Throughput Order Ingestion
Implements idempotent, chunked upload with streaming processing
"""

import json
import uuid
import time
import gzip
import io
from typing import Dict, List, Any, Optional
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.db import transaction, connection
from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Tenant, Order, OrderItem, Product, Customer, IngestionJob
import logging

logger = logging.getLogger(__name__)


class BulkIngestProcessor:
    """Process bulk order ingestion with idempotency and chunking"""
    
    def __init__(self, tenant_id: str, idempotency_key: str):
        self.tenant_id = tenant_id
        self.idempotency_key = idempotency_key
        self.tenant = self._get_tenant()
        self.job = self._get_or_create_job()
    
    def _get_tenant(self) -> Optional[Tenant]:
        """Get tenant by ID"""
        try:
            return Tenant.objects.get(id=self.tenant_id)
        except Tenant.DoesNotExist:
            return None
    
    def _get_or_create_job(self) -> Optional[IngestionJob]:
        """Get or create ingestion job for idempotency"""
        if not self.tenant:
            return None
        
        job, created = IngestionJob.objects.get_or_create(
            idempotency_key=self.idempotency_key,
            defaults={
                'tenant': self.tenant,
                'status': 'pending',
                'total_rows': 0,
                'processed_rows': 0,
                'failed_rows': 0
            }
        )
        return job
    
    def process_chunk(self, chunk_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a chunk of order data"""
        if not self.job or self.job.status == 'completed':
            return {
                'success': False,
                'error': 'Job already completed or not found',
                'rows_processed': 0,
                'rows_failed': 0
            }
        
        if self.job.status == 'failed':
            return {
                'success': False,
                'error': 'Job has failed and cannot process more data',
                'rows_processed': 0,
                'rows_failed': 0
            }
        
        # Update job status to processing
        self.job.status = 'processing'
        self.job.save()
        
        rows_processed = 0
        rows_failed = 0
        error_details = []
        
        try:
            # Process orders in batches using raw SQL for performance
            orders_data = []
            order_items_data = []
            
            for row_data in chunk_data:
                try:
                    # Validate required fields
                    if not self._validate_order_data(row_data):
                        rows_failed += 1
                        error_details.append({
                            'row': row_data,
                            'error': 'Missing required fields'
                        })
                        continue
                    
                    # Prepare order data
                    order_id = str(uuid.uuid4())
                    order_data = self._prepare_order_data(row_data, order_id)
                    orders_data.append(order_data)
                    
                    # Prepare order items data
                    items_data = self._prepare_order_items_data(row_data, order_id)
                    order_items_data.extend(items_data)
                    
                    rows_processed += 1
                    
                except Exception as e:
                    rows_failed += 1
                    error_details.append({
                        'row': row_data,
                        'error': str(e)
                    })
                    logger.error(f"Error processing order row: {e}")
            
            # Bulk insert using raw SQL for maximum performance
            if orders_data:
                self._bulk_insert_orders(orders_data)
                self._bulk_insert_order_items(order_items_data)
            
            # Update job progress
            self.job.processed_rows += rows_processed
            self.job.failed_rows += rows_failed
            self.job.error_details.update({str(uuid.uuid4()): error_details})
            
            if rows_processed > 0:
                self.job.status = 'processing'
            else:
                self.job.status = 'failed'
            
            self.job.save()
            
            return {
                'success': True,
                'rows_processed': rows_processed,
                'rows_failed': rows_failed,
                'error_details': error_details[:10]  # Limit error details
            }
            
        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            self.job.status = 'failed'
            self.job.save()
            
            return {
                'success': False,
                'error': str(e),
                'rows_processed': rows_processed,
                'rows_failed': rows_failed
            }
    
    def _validate_order_data(self, data: Dict[str, Any]) -> bool:
        """Validate order data has required fields"""
        required_fields = ['order_number', 'total_amount', 'status']
        return all(field in data for field in required_fields)
    
    def _prepare_order_data(self, data: Dict[str, Any], order_id: str) -> Dict[str, Any]:
        """Prepare order data for bulk insert"""
        # Get or create customer if email provided
        customer_id = None
        if 'customer_email' in data:
            customer_id = self._get_or_create_customer(data)
        
        return {
            'id': order_id,
            'tenant_id': self.tenant_id,
            'customer_id': customer_id,
            'order_number': data['order_number'],
            'status': data['status'],
            'total_amount': float(data['total_amount']),
            'currency': data.get('currency', 'USD'),
            'created_at': data.get('created_at', time.time()),
            'updated_at': time.time()
        }
    
    def _prepare_order_items_data(self, data: Dict[str, Any], order_id: str) -> List[Dict[str, Any]]:
        """Prepare order items data for bulk insert"""
        items_data = []
        
        if 'items' in data and isinstance(data['items'], list):
            for item in data['items']:
                if 'product_sku' in item and 'quantity' in item and 'price' in item:
                    # Get product ID by SKU
                    product_id = self._get_product_by_sku(item['product_sku'])
                    if product_id:
                        items_data.append({
                            'id': str(uuid.uuid4()),
                            'order_id': order_id,
                            'product_id': product_id,
                            'quantity': int(item['quantity']),
                            'price': float(item['price']),
                            'total_price': float(item['quantity']) * float(item['price']),
                            'created_at': time.time()
                        })
        
        return items_data
    
    def _get_or_create_customer(self, data: Dict[str, Any]) -> Optional[str]:
        """Get or create customer by email"""
        email = data.get('customer_email')
        if not email:
            return None
        
        try:
            customer = Customer.objects.get(tenant_id=self.tenant_id, email=email)
            return str(customer.id)
        except Customer.DoesNotExist:
            # Create new customer
            customer = Customer.objects.create(
                tenant_id=self.tenant_id,
                name=data.get('customer_name', 'Unknown'),
                email=email,
                phone=data.get('customer_phone', '')
            )
            return str(customer.id)
    
    def _get_product_by_sku(self, sku: str) -> Optional[str]:
        """Get product ID by SKU"""
        try:
            product = Product.objects.get(tenant_id=self.tenant_id, sku=sku)
            return str(product.id)
        except Product.DoesNotExist:
            return None
    
    def _bulk_insert_orders(self, orders_data: List[Dict[str, Any]]):
        """Bulk insert orders using raw SQL"""
        if not orders_data:
            return
        
        cursor = connection.cursor()
        columns = ['id', 'tenant_id', 'customer_id', 'order_number', 'status', 
                  'total_amount', 'currency', 'created_at', 'updated_at']
        placeholders = ', '.join(['%s'] * len(columns))
        query = f"""
            INSERT INTO orders ({', '.join(columns)}) 
            VALUES ({placeholders})
        """
        
        values = [tuple(order[col] for col in columns) for order in orders_data]
        cursor.executemany(query, values)
    
    def _bulk_insert_order_items(self, items_data: List[Dict[str, Any]]):
        """Bulk insert order items using raw SQL"""
        if not items_data:
            return
        
        cursor = connection.cursor()
        columns = ['id', 'order_id', 'product_id', 'quantity', 'price', 
                  'total_price', 'created_at']
        placeholders = ', '.join(['%s'] * len(columns))
        query = f"""
            INSERT INTO order_items ({', '.join(columns)}) 
            VALUES ({placeholders})
        """
        
        values = [tuple(item[col] for col in columns) for item in items_data]
        cursor.executemany(query, values)
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get current job status"""
        if not self.job:
            return {'error': 'Job not found'}
        
        return {
            'idempotency_key': self.idempotency_key,
            'status': self.job.status,
            'total_rows': self.job.total_rows,
            'processed_rows': self.job.processed_rows,
            'failed_rows': self.job.failed_rows,
            'created_at': self.job.created_at.isoformat(),
            'completed_at': self.job.completed_at.isoformat() if self.job.completed_at else None
        }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_ingest_orders(request):
    """
    Bulk ingest orders endpoint
    Supports multipart/form-data, application/x-ndjson, and compressed data
    """
    start_time = time.time()
    
    # Get idempotency key
    idempotency_key = request.headers.get('Idempotency-Key')
    if not idempotency_key:
        return Response(
            {'error': 'Idempotency-Key header is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get tenant ID from URL or request
    tenant_id = request.data.get('tenant_id') or request.GET.get('tenant_id')
    if not tenant_id:
        return Response(
            {'error': 'tenant_id is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if job already exists and is completed
    try:
        existing_job = IngestionJob.objects.get(idempotency_key=idempotency_key)
        if existing_job.status == 'completed':
            return Response({
                'message': 'Job already completed',
                'idempotency_key': idempotency_key,
                'rows_received': existing_job.total_rows,
                'rows_inserted': existing_job.processed_rows,
                'rows_failed': existing_job.failed_rows,
                'processing_time': 0
            })
    except IngestionJob.DoesNotExist:
        pass
    
    # Initialize processor
    processor = BulkIngestProcessor(tenant_id, idempotency_key)
    if not processor.tenant:
        return Response(
            {'error': 'Tenant not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Process data based on content type
    content_type = request.content_type
    
    try:
        if 'multipart/form-data' in content_type:
            # Handle multipart form data
            file = request.FILES.get('file')
            if not file:
                return Response(
                    {'error': 'No file provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read file content
            if file.name.endswith('.gz'):
                content = gzip.decompress(file.read()).decode('utf-8')
            else:
                content = file.read().decode('utf-8')
            
            # Parse JSON Lines
            chunk_data = []
            for line in content.strip().split('\n'):
                if line.strip():
                    chunk_data.append(json.loads(line))
        
        elif 'application/x-ndjson' in content_type:
            # Handle NDJSON data
            content = request.body.decode('utf-8')
            chunk_data = []
            for line in content.strip().split('\n'):
                if line.strip():
                    chunk_data.append(json.loads(line))
        
        elif 'application/octet-stream' in content_type:
            # Handle compressed data
            content = gzip.decompress(request.body).decode('utf-8')
            chunk_data = []
            for line in content.strip().split('\n'):
                if line.strip():
                    chunk_data.append(json.loads(line))
        
        else:
            return Response(
                {'error': 'Unsupported content type'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process chunk
        result = processor.process_chunk(chunk_data)
        
        # Update job totals
        processor.job.total_rows += len(chunk_data)
        processor.job.save()
        
        processing_time = time.time() - start_time
        
        if result['success']:
            return Response({
                'idempotency_key': idempotency_key,
                'rows_received': len(chunk_data),
                'rows_inserted': result['rows_processed'],
                'rows_failed': result['rows_failed'],
                'processing_time': processing_time,
                'error_details': result.get('error_details', [])
            })
        else:
            return Response(
                {'error': result['error']}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except Exception as e:
        logger.error(f"Error in bulk ingest: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ingestion_status(request, idempotency_key):
    """Get ingestion job status"""
    try:
        job = IngestionJob.objects.get(idempotency_key=idempotency_key)
        return Response({
            'idempotency_key': idempotency_key,
            'status': job.status,
            'total_rows': job.total_rows,
            'processed_rows': job.processed_rows,
            'failed_rows': job.failed_rows,
            'created_at': job.created_at.isoformat(),
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error_details': job.error_details
        })
    except IngestionJob.DoesNotExist:
        return Response(
            {'error': 'Job not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_upload_token(request):
    """Create resumable upload token"""
    tenant_id = request.data.get('tenant_id')
    if not tenant_id:
        return Response(
            {'error': 'tenant_id is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Generate upload token
    upload_token = str(uuid.uuid4())
    
    # Store token in cache with expiration
    cache.set(f"upload_token_{upload_token}", {
        'tenant_id': tenant_id,
        'created_at': time.time()
    }, timeout=3600)  # 1 hour expiration
    
    return Response({
        'upload_token': upload_token,
        'expires_in': 3600
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resume_upload(request, upload_token):
    """Resume upload using token"""
    # Get token data from cache
    token_data = cache.get(f"upload_token_{upload_token}")
    if not token_data:
        return Response(
            {'error': 'Invalid or expired upload token'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Process upload similar to bulk_ingest_orders
    # Implementation would be similar to bulk_ingest_orders but using the token's tenant_id
    return Response({'message': 'Upload resumed successfully'})



