"""
Observability and Backpressure Handling
Implements metrics, monitoring, and graceful degradation
"""

import json
import time
import psutil
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from django.db import connection
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect system and application metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.lock = threading.Lock()
    
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        with self.lock:
            key = self._get_metric_key(name, labels)
            if key not in self.metrics:
                self.metrics[key] = {'type': 'counter', 'value': 0}
            self.metrics[key]['value'] += value
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric"""
        with self.lock:
            key = self._get_metric_key(name, labels)
            self.metrics[key] = {'type': 'gauge', 'value': value}
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value"""
        with self.lock:
            key = self._get_metric_key(name, labels)
            if key not in self.metrics:
                self.metrics[key] = {'type': 'histogram', 'values': []}
            self.metrics[key]['values'].append({
                'value': value,
                'timestamp': time.time()
            })
            # Keep only last 1000 values
            if len(self.metrics[key]['values']) > 1000:
                self.metrics[key]['values'] = self.metrics[key]['values'][-1000:]
    
    def _get_metric_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Generate metric key with labels"""
        if not labels:
            return name
        label_str = ','.join([f'{k}={v}' for k, v in sorted(labels.items())])
        return f'{name}{{{label_str}}}'
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        with self.lock:
            return self.metrics.copy()
    
    def get_histogram_stats(self, name: str, labels: Dict[str, str] = None) -> Dict[str, float]:
        """Get histogram statistics"""
        key = self._get_metric_key(name, labels)
        if key not in self.metrics or self.metrics[key]['type'] != 'histogram':
            return {}
        
        values = self.metrics[key]['values']
        if not values:
            return {}
        
        sorted_values = sorted([v['value'] for v in values])
        n = len(sorted_values)
        
        return {
            'count': n,
            'min': min(sorted_values),
            'max': max(sorted_values),
            'sum': sum(sorted_values),
            'avg': sum(sorted_values) / n,
            'p50': sorted_values[int(n * 0.5)],
            'p95': sorted_values[int(n * 0.95)],
            'p99': sorted_values[int(n * 0.99)]
        }


class BackpressureController:
    """Handle backpressure and graceful degradation"""
    
    def __init__(self):
        self.queue_length_threshold = 1000
        self.memory_threshold = 0.8  # 80% memory usage
        self.cpu_threshold = 0.9     # 90% CPU usage
        self.retry_after_base = 1    # Base retry after in seconds
    
    def check_backpressure(self) -> Dict[str, Any]:
        """Check if system is under backpressure"""
        # Get system metrics
        memory_usage = psutil.virtual_memory().percent / 100
        cpu_usage = psutil.cpu_percent() / 100
        
        # Get queue length (simplified - in production, you'd check actual queue)
        queue_length = self._get_queue_length()
        
        # Check thresholds
        memory_pressure = memory_usage > self.memory_threshold
        cpu_pressure = cpu_usage > self.cpu_threshold
        queue_pressure = queue_length > self.queue_length_threshold
        
        under_pressure = memory_pressure or cpu_pressure or queue_pressure
        
        # Calculate retry after
        retry_after = self.retry_after_base
        if memory_pressure:
            retry_after *= 2
        if cpu_pressure:
            retry_after *= 2
        if queue_pressure:
            retry_after *= (queue_length / self.queue_length_threshold)
        
        return {
            'under_pressure': under_pressure,
            'memory_usage': memory_usage,
            'cpu_usage': cpu_usage,
            'queue_length': queue_length,
            'memory_pressure': memory_pressure,
            'cpu_pressure': cpu_pressure,
            'queue_pressure': queue_pressure,
            'retry_after': int(retry_after)
        }
    
    def _get_queue_length(self) -> int:
        """Get current queue length (simplified)"""
        # In production, you'd check actual queue length
        # For now, return a simulated value
        return cache.get('queue_length', 0)
    
    def set_queue_length(self, length: int):
        """Set queue length"""
        cache.set('queue_length', length, 60)  # 1 minute expiration


# Global instances
metrics_collector = MetricsCollector()
backpressure_controller = BackpressureController()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_metrics(request):
    """Get Prometheus-style metrics"""
    try:
        # Get system metrics
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk_usage = psutil.disk_usage('/')
        
        # Get application metrics
        app_metrics = metrics_collector.get_metrics()
        
        # Format metrics in Prometheus format
        metrics_lines = []
        
        # System metrics
        metrics_lines.append(f'# HELP system_memory_usage_percent System memory usage percentage')
        metrics_lines.append(f'# TYPE system_memory_usage_percent gauge')
        metrics_lines.append(f'system_memory_usage_percent {memory_info.percent}')
        
        metrics_lines.append(f'# HELP system_cpu_usage_percent System CPU usage percentage')
        metrics_lines.append(f'# TYPE system_cpu_usage_percent gauge')
        metrics_lines.append(f'system_cpu_usage_percent {cpu_percent}')
        
        metrics_lines.append(f'# HELP system_disk_usage_percent System disk usage percentage')
        metrics_lines.append(f'# TYPE system_disk_usage_percent gauge')
        metrics_lines.append(f'system_disk_usage_percent {disk_usage.percent}')
        
        # Application metrics
        for key, metric in app_metrics.items():
            if metric['type'] == 'counter':
                metrics_lines.append(f'# HELP {key} Application counter metric')
                metrics_lines.append(f'# TYPE {key} counter')
                metrics_lines.append(f'{key} {metric["value"]}')
            
            elif metric['type'] == 'gauge':
                metrics_lines.append(f'# HELP {key} Application gauge metric')
                metrics_lines.append(f'# TYPE {key} gauge')
                metrics_lines.append(f'{key} {metric["value"]}')
            
            elif metric['type'] == 'histogram':
                stats = metrics_collector.get_histogram_stats(key)
                if stats:
                    metrics_lines.append(f'# HELP {key} Application histogram metric')
                    metrics_lines.append(f'# TYPE {key} histogram')
                    metrics_lines.append(f'{key}_count {stats["count"]}')
                    metrics_lines.append(f'{key}_sum {stats["sum"]}')
                    metrics_lines.append(f'{key}_avg {stats["avg"]}')
                    metrics_lines.append(f'{key}_p50 {stats["p50"]}')
                    metrics_lines.append(f'{key}_p95 {stats["p95"]}')
                    metrics_lines.append(f'{key}_p99 {stats["p99"]}')
        
        # Backpressure metrics
        backpressure_info = backpressure_controller.check_backpressure()
        metrics_lines.append(f'# HELP backpressure_under_pressure System under backpressure')
        metrics_lines.append(f'# TYPE backpressure_under_pressure gauge')
        metrics_lines.append(f'backpressure_under_pressure {1 if backpressure_info["under_pressure"] else 0}')
        
        metrics_lines.append(f'# HELP backpressure_queue_length Current queue length')
        metrics_lines.append(f'# TYPE backpressure_queue_length gauge')
        metrics_lines.append(f'backpressure_queue_length {backpressure_info["queue_length"]}')
        
        metrics_text = '\n'.join(metrics_lines)
        
        return HttpResponse(metrics_text, content_type='text/plain')
    
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_health_status(request):
    """Get health status with backpressure information"""
    try:
        # Check backpressure
        backpressure_info = backpressure_controller.check_backpressure()
        
        # Get database health
        db_healthy = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            db_healthy = False
        
        # Get cache health
        cache_healthy = True
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') != 'ok':
                cache_healthy = False
        except Exception:
            cache_healthy = False
        
        # Overall health
        overall_healthy = db_healthy and cache_healthy and not backpressure_info['under_pressure']
        
        status_code = 200 if overall_healthy else 503
        
        response_data = {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'components': {
                'database': 'healthy' if db_healthy else 'unhealthy',
                'cache': 'healthy' if cache_healthy else 'unhealthy',
                'backpressure': 'healthy' if not backpressure_info['under_pressure'] else 'unhealthy'
            },
            'backpressure': backpressure_info,
            'system': {
                'memory_usage_percent': psutil.virtual_memory().percent,
                'cpu_usage_percent': psutil.cpu_percent(),
                'disk_usage_percent': psutil.disk_usage('/').percent
            }
        }
        
        return Response(response_data, status=status_code)
    
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_performance_metrics(request):
    """Get detailed performance metrics"""
    try:
        # Get histogram statistics
        db_query_stats = metrics_collector.get_histogram_stats('db_query_duration')
        api_response_stats = metrics_collector.get_histogram_stats('api_response_duration')
        ingestion_stats = metrics_collector.get_histogram_stats('ingestion_duration')
        
        # Get current metrics
        current_metrics = metrics_collector.get_metrics()
        
        # Get backpressure info
        backpressure_info = backpressure_controller.check_backpressure()
        
        return Response({
            'timestamp': datetime.now().isoformat(),
            'database_queries': db_query_stats,
            'api_responses': api_response_stats,
            'ingestion': ingestion_stats,
            'current_metrics': current_metrics,
            'backpressure': backpressure_info,
            'system': {
                'memory_usage_percent': psutil.virtual_memory().percent,
                'cpu_usage_percent': psutil.cpu_percent(),
                'disk_usage_percent': psutil.disk_usage('/').percent
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_queue_length(request):
    """Update queue length (for testing backpressure)"""
    try:
        length = request.data.get('length', 0)
        backpressure_controller.set_queue_length(length)
        
        return Response({
            'message': 'Queue length updated',
            'new_length': length
        })
    
    except Exception as e:
        logger.error(f"Error updating queue length: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_backpressure_status(request):
    """Get current backpressure status"""
    try:
        backpressure_info = backpressure_controller.check_backpressure()
        
        return Response(backpressure_info)
    
    except Exception as e:
        logger.error(f"Error getting backpressure status: {e}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Middleware for automatic metrics collection
class MetricsMiddleware:
    """Middleware to collect request metrics"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        metrics_collector.record_histogram('api_response_duration', duration, {
            'method': request.method,
            'path': request.path,
            'status_code': str(response.status_code)
        })
        
        metrics_collector.increment_counter('api_requests_total', 1, {
            'method': request.method,
            'path': request.path,
            'status_code': str(response.status_code)
        })
        
        return response


# Decorator for database query metrics
def track_db_query(func):
    """Decorator to track database query performance"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        metrics_collector.record_histogram('db_query_duration', duration, {
            'function': func.__name__
        })
        
        return result
    return wrapper



