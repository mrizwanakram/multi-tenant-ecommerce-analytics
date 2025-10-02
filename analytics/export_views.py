"""
Streaming Export API with Resumable Downloads
Implements CSV/Parquet export with compression and checkpointing
"""

import csv
import json
import gzip
import io
import time
import uuid
from typing import Dict, List, Any, Optional, Iterator
from datetime import datetime, timedelta
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.core.cache import cache
from django.db import connection
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Tenant, Order, OrderItem, Product, Customer, ExportJob
import logging

logger = logging.getLogger(__name__)


class StreamingExporter:
    """Streaming exporter for large datasets"""
    
    def __init__(self, tenant_id: str, export_format: str = 'csv'):
        self.tenant_id = tenant_id
        self.export_format = export_format.lower()
        self.tenant = self._get_tenant()
    
    def _get_tenant(self) -> Optional[Tenant]:
        """Get tenant by ID"""
        try:
            return Tenant.objects.get(id=self.tenant_id)
        except Tenant.DoesNotExist:
            return None
    
    def export_orders(self, filters: Dict[str, Any], job_id: str) -> Iterator[bytes]:
        """Export orders with streaming"""
        if not self.tenant:
            yield b'{"error": "Tenant not found"}'
            return
        
        # Update job status
        self._update_job_status(job_id, 'processing', 0)
        
        try:
            if self.export_format == 'csv':
                yield from self._export_orders_csv(filters, job_id)
            elif self.export_format == 'parquet':
                yield from self._export_orders_parquet(filters, job_id)
            else:
                yield b'{"error": "Unsupported format"}'
        
        except Exception as e:
            logger.error(f"Error in export_orders: {e}")
            self._update_job_status(job_id, 'failed', 0, str(e))
            yield f'{{"error": "{str(e)}"}}'.encode('utf-8')
    
    def _export_orders_csv(self, filters: Dict[str, Any], job_id: str) -> Iterator[bytes]:
        """Export orders as CSV with streaming"""
        # Build query
        query, params = self._build_orders_query(filters)
        
        # Get total count for progress tracking
        count_query = f"SELECT COUNT(*) FROM ({query}) as count_query"
        with connection.cursor() as cursor:
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
        
        # Create CSV writer
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        headers = [
            'order_id', 'order_number', 'status', 'total_amount', 'currency',
            'customer_name', 'customer_email', 'created_at', 'updated_at'
        ]
        writer.writerow(headers)
        yield output.getvalue().encode('utf-8')
        output.seek(0)
        output.truncate(0)
        
        # Stream data
        processed_count = 0
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            
            while True:
                rows = cursor.fetchmany(1000)  # Process in chunks
                if not rows:
                    break
                
                for row in rows:
                    writer.writerow([
                        str(row[0]),  # order_id
                        row[1],       # order_number
                        row[2],       # status
                        float(row[3]), # total_amount
                        row[4],       # currency
                        row[5] or '', # customer_name
                        row[6] or '', # customer_email
                        row[7].isoformat() if row[7] else '',  # created_at
                        row[8].isoformat() if row[8] else ''   # updated_at
                    ])
                
                # Yield chunk
                chunk_data = output.getvalue().encode('utf-8')
                yield chunk_data
                
                # Update progress
                processed_count += len(rows)
                progress = int((processed_count / total_count) * 100) if total_count > 0 else 100
                self._update_job_status(job_id, 'processing', progress)
                
                # Reset buffer
                output.seek(0)
                output.truncate(0)
        
        # Mark as completed
        self._update_job_status(job_id, 'completed', 100)
    
    def _export_orders_parquet(self, filters: Dict[str, Any], job_id: str) -> Iterator[bytes]:
        """Export orders as Parquet (simplified JSON format for demo)"""
        # For demo purposes, we'll use JSON Lines format
        # In production, you'd use pyarrow or similar for actual Parquet
        
        query, params = self._build_orders_query(filters)
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            
            while True:
                rows = cursor.fetchmany(1000)
                if not rows:
                    break
                
                for row in rows:
                    data = {
                        'order_id': str(row[0]),
                        'order_number': row[1],
                        'status': row[2],
                        'total_amount': float(row[3]),
                        'currency': row[4],
                        'customer_name': row[5] or '',
                        'customer_email': row[6] or '',
                        'created_at': row[7].isoformat() if row[7] else '',
                        'updated_at': row[8].isoformat() if row[8] else ''
                    }
                    yield json.dumps(data).encode('utf-8') + b'\n'
    
    def _build_orders_query(self, filters: Dict[str, Any]) -> tuple:
        """Build SQL query for orders export"""
        query = """
            SELECT 
                o.id, o.order_number, o.status, o.total_amount, o.currency,
                c.name as customer_name, c.email as customer_email,
                o.created_at, o.updated_at
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            WHERE o.tenant_id = %s
        """
        params = [self.tenant_id]
        
        # Add filters
        if 'start_date' in filters:
            query += " AND o.created_at >= %s"
            params.append(filters['start_date'])
        
        if 'end_date' in filters:
            query += " AND o.created_at <= %s"
            params.append(filters['end_date'])
        
        if 'status' in filters:
            if isinstance(filters['status'], list):
                placeholders = ', '.join(['%s'] * len(filters['status']))
                query += f" AND o.status IN ({placeholders})"
                params.extend(filters['status'])
            else:
                query += " AND o.status = %s"
                params.append(filters['status'])
        
        query += " ORDER BY o.created_at DESC"
        
        return query, params
    
    def _update_job_status(self, job_id: str, status: str, progress: int, error_message: str = None):
        """Update export job status"""
        try:
            job = ExportJob.objects.get(id=job_id)
            job.status = status
            job.progress = progress
            if error_message:
                job.error_message = error_message
            if status == 'completed':
                job.completed_at = datetime.now()
            job.save()
        except ExportJob.DoesNotExist:
            pass


class ResumableDownload:
    """Handle resumable downloads with range requests"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.job = self._get_job()
    
    def _get_job(self) -> Optional[ExportJob]:
        """Get export job"""
        try:
            return ExportJob.objects.get(id=self.job_id)
        except ExportJob.DoesNotExist:
            return None
    
    def get_file_info(self) -> Dict[str, Any]:
        """Get file information for range requests"""
        if not self.job or self.job.status != 'completed':
            return {'error': 'Job not completed'}
        
        return {
            'file_size': self.job.file_size,
            'content_type': 'text/csv' if self.job.format == 'csv' else 'application/octet-stream',
            'filename': f'export_{self.job_id}.{self.job.format}'
        }
    
    def get_file_chunk(self, start: int, end: int) -> bytes:
        """Get file chunk for range request"""
        if not self.job or not self.job.file_path:
            return b''
        
        try:
            with open(self.job.file_path, 'rb') as f:
                f.seek(start)
                return f.read(end - start + 1)
        except Exception as e:
            logger.error(f"Error reading file chunk: {e}")
            return b''


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_export(request, tenant_id):
    """Create export job"""
    try:
        # Parse request data
        export_format = request.data.get('format', 'csv')
        filters = request.data.get('filters', {})
        
        if export_format not in ['csv', 'parquet']:
            return Response(
                {'error': 'Unsupported format. Use csv or parquet'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create export job
        job = ExportJob.objects.create(
            tenant_id=tenant_id,
            format=export_format,
            filters=filters,
            status='pending'
        )
        
        return Response({
            'job_id': str(job.id),
            'status': job.status,
            'format': job.format,
            'created_at': job.created_at.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error creating export: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stream_export(request, tenant_id, job_id):
    """Stream export data"""
    try:
        # Get job
        try:
            job = ExportJob.objects.get(id=job_id, tenant_id=tenant_id)
        except ExportJob.DoesNotExist:
            return Response(
                {'error': 'Export job not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if job is ready
        if job.status == 'pending':
            return Response(
                {'error': 'Export job is still pending'}, 
                status=status.HTTP_202_ACCEPTED
            )
        elif job.status == 'failed':
            return Response(
                {'error': f'Export job failed: {job.error_message}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Start export if not already started
        if job.status == 'pending':
            job.status = 'processing'
            job.save()
            
            exporter = StreamingExporter(tenant_id, job.format)
            
            def generate_export():
                yield from exporter.export_orders(job.filters, str(job.id))
            
            # Set response headers
            content_type = 'text/csv' if job.format == 'csv' else 'application/octet-stream'
            filename = f'export_{job_id}.{job.format}'
            
            response = StreamingHttpResponse(
                generate_export(),
                content_type=content_type
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Encoding'] = 'gzip'
            
            return response
        
        # If job is completed, stream the file
        elif job.status == 'completed':
            if not job.file_path:
                return Response(
                    {'error': 'Export file not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            def generate_file():
                with open(job.file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk
            
            content_type = 'text/csv' if job.format == 'csv' else 'application/octet-stream'
            filename = f'export_{job_id}.{job.format}'
            
            response = StreamingHttpResponse(
                generate_file(),
                content_type=content_type
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = str(job.file_size)
            
            return response
    
    except Exception as e:
        logger.error(f"Error streaming export: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_export_status(request, tenant_id, job_id):
    """Get export job status"""
    try:
        job = ExportJob.objects.get(id=job_id, tenant_id=tenant_id)
        
        return Response({
            'job_id': str(job.id),
            'status': job.status,
            'format': job.format,
            'progress': job.progress,
            'file_size': job.file_size,
            'created_at': job.created_at.isoformat(),
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error_message': job.error_message
        })
    
    except ExportJob.DoesNotExist:
        return Response(
            {'error': 'Export job not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_export(request, tenant_id, job_id):
    """Download export with range request support"""
    try:
        # Get range header
        range_header = request.META.get('HTTP_RANGE')
        
        # Get job
        try:
            job = ExportJob.objects.get(id=job_id, tenant_id=tenant_id)
        except ExportJob.DoesNotExist:
            return Response(
                {'error': 'Export job not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if job.status != 'completed':
            return Response(
                {'error': 'Export not ready'}, 
                status=status.HTTP_202_ACCEPTED
            )
        
        # Handle range request
        if range_header:
            # Parse range header
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else job.file_size - 1
            
            # Get file chunk
            resumable = ResumableDownload(job_id)
            chunk_data = resumable.get_file_chunk(start, end)
            
            response = HttpResponse(
                chunk_data,
                status=206,  # Partial Content
                content_type='text/csv' if job.format == 'csv' else 'application/octet-stream'
            )
            response['Content-Range'] = f'bytes {start}-{end}/{job.file_size}'
            response['Content-Length'] = str(len(chunk_data))
            
            return response
        
        else:
            # Full file download
            def generate_file():
                with open(job.file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk
            
            content_type = 'text/csv' if job.format == 'csv' else 'application/octet-stream'
            filename = f'export_{job_id}.{job.format}'
            
            response = StreamingHttpResponse(
                generate_file(),
                content_type=content_type
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = str(job.file_size)
            
            return response
    
    except Exception as e:
        logger.error(f"Error downloading export: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



