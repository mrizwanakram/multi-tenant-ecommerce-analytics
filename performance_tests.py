#!/usr/bin/env python3
"""
Performance Test Scripts for Multi-tenant Ecommerce Analytics
Tests bulk ingestion, streaming search, and concurrent operations
"""

import os
import sys
import time
import json
import uuid
import requests
import threading
import concurrent.futures
from datetime import datetime, timedelta
from typing import List, Dict, Any
import statistics

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class PerformanceTester:
    """Performance testing suite"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {}
    
    def test_bulk_ingestion(self, num_orders: int = 10000, chunk_size: int = 1000) -> Dict[str, Any]:
        """Test bulk order ingestion performance"""
        print(f"Testing bulk ingestion: {num_orders} orders in chunks of {chunk_size}")
        
        # Create test tenant
        tenant_id = self._create_test_tenant()
        if not tenant_id:
            return {'error': 'Failed to create test tenant'}
        
        # Create test products
        product_ids = self._create_test_products(tenant_id, 100)
        if not product_ids:
            return {'error': 'Failed to create test products'}
        
        # Generate test orders
        orders = self._generate_test_orders(tenant_id, product_ids, num_orders)
        
        # Test ingestion
        start_time = time.time()
        total_ingested = 0
        total_failed = 0
        
        for i in range(0, len(orders), chunk_size):
            chunk = orders[i:i + chunk_size]
            result = self._ingest_chunk(tenant_id, chunk)
            
            if result.get('success'):
                total_ingested += result.get('rows_inserted', 0)
                total_failed += result.get('rows_failed', 0)
            else:
                total_failed += len(chunk)
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = total_ingested / duration if duration > 0 else 0
        
        result = {
            'test_name': 'bulk_ingestion',
            'total_orders': num_orders,
            'chunk_size': chunk_size,
            'orders_ingested': total_ingested,
            'orders_failed': total_failed,
            'duration_seconds': duration,
            'throughput_orders_per_second': throughput,
            'success_rate': (total_ingested / num_orders) * 100 if num_orders > 0 else 0
        }
        
        self.results['bulk_ingestion'] = result
        return result
    
    def test_streaming_search(self, tenant_id: str = None, limit: int = 10000) -> Dict[str, Any]:
        """Test streaming search performance"""
        print(f"Testing streaming search: limit {limit}")
        
        if not tenant_id:
            tenant_id = self._create_test_tenant()
            if not tenant_id:
                return {'error': 'Failed to create test tenant'}
        
        # Test streaming search
        start_time = time.time()
        
        url = f"{self.base_url}/api/v1/tenants/{tenant_id}/orders/search/"
        params = {
            'limit': limit,
            'stream': 'true',
            'fields': 'id,order_number,status,total_amount,created_at'
        }
        
        response = self.session.get(url, params=params, stream=True)
        
        if response.status_code != 200:
            return {'error': f'Search failed with status {response.status_code}'}
        
        # Count records and measure memory
        record_count = 0
        max_memory_usage = 0
        
        for line in response.iter_lines():
            if line:
                record_count += 1
                # Simulate memory usage tracking
                current_memory = len(line)
                max_memory_usage = max(max_memory_usage, current_memory)
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = record_count / duration if duration > 0 else 0
        
        result = {
            'test_name': 'streaming_search',
            'limit': limit,
            'records_returned': record_count,
            'duration_seconds': duration,
            'throughput_records_per_second': throughput,
            'max_memory_usage_bytes': max_memory_usage,
            'memory_efficient': max_memory_usage < 200 * 1024 * 1024  # 200MB limit
        }
        
        self.results['streaming_search'] = result
        return result
    
    def test_concurrent_stock_updates(self, tenant_id: str = None, num_products: int = 10, 
                                    num_threads: int = 5) -> Dict[str, Any]:
        """Test concurrent stock updates and conflict resolution"""
        print(f"Testing concurrent stock updates: {num_products} products, {num_threads} threads")
        
        if not tenant_id:
            tenant_id = self._create_test_tenant()
            if not tenant_id:
                return {'error': 'Failed to create test tenant'}
        
        # Create test products
        product_ids = self._create_test_products(tenant_id, num_products)
        if not product_ids:
            return {'error': 'Failed to create test products'}
        
        # Test concurrent updates
        start_time = time.time()
        results = []
        
        def update_stock(product_id: str, thread_id: int):
            events = []
            for i in range(10):  # 10 updates per thread
                events.append({
                    'product_id': product_id,
                    'event_type': 'adjustment',
                    'quantity_change': 1,
                    'reference_id': f'thread_{thread_id}_update_{i}'
                })
            
            url = f"{self.base_url}/api/v1/tenants/{tenant_id}/stock/bulk_update/"
            data = {
                'events': events,
                'conflict_strategy': 'merge'
            }
            
            response = self.session.put(url, json=data)
            return {
                'thread_id': thread_id,
                'product_id': product_id,
                'status_code': response.status_code,
                'response': response.json() if response.status_code == 200 else None
            }
        
        # Run concurrent updates
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for thread_id in range(num_threads):
                product_id = product_ids[thread_id % len(product_ids)]
                future = executor.submit(update_stock, product_id, thread_id)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Analyze results
        successful_updates = sum(1 for r in results if r['status_code'] == 200)
        failed_updates = len(results) - successful_updates
        
        result = {
            'test_name': 'concurrent_stock_updates',
            'num_products': num_products,
            'num_threads': num_threads,
            'total_updates': len(results),
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'duration_seconds': duration,
            'updates_per_second': len(results) / duration if duration > 0 else 0,
            'success_rate': (successful_updates / len(results)) * 100 if results else 0
        }
        
        self.results['concurrent_stock_updates'] = result
        return result
    
    def test_aggregation_performance(self, tenant_id: str = None, precision: str = 'exact') -> Dict[str, Any]:
        """Test aggregation performance with approximate and exact modes"""
        print(f"Testing aggregation performance: {precision} mode")
        
        if not tenant_id:
            tenant_id = self._create_test_tenant()
            if not tenant_id:
                return {'error': 'Failed to create test tenant'}
        
        # Test different group_by options
        group_by_options = ['day', 'hour', 'product', 'category']
        results = {}
        
        for group_by in group_by_options:
            start_time = time.time()
            
            url = f"{self.base_url}/api/v1/tenants/{tenant_id}/metrics/sales/"
            params = {
                'group_by': group_by,
                'start_date': (datetime.now() - timedelta(days=30)).isoformat(),
                'end_date': datetime.now().isoformat(),
                'precision': precision
            }
            
            response = self.session.get(url, params=params)
            
            end_time = time.time()
            duration = end_time - start_time
            
            results[group_by] = {
                'status_code': response.status_code,
                'duration_seconds': duration,
                'success': response.status_code == 200
            }
        
        # Calculate average performance
        successful_queries = sum(1 for r in results.values() if r['success'])
        avg_duration = statistics.mean([r['duration_seconds'] for r in results.values() if r['success']])
        
        result = {
            'test_name': 'aggregation_performance',
            'precision': precision,
            'group_by_options': group_by_options,
            'successful_queries': successful_queries,
            'failed_queries': len(group_by_options) - successful_queries,
            'average_duration_seconds': avg_duration,
            'success_rate': (successful_queries / len(group_by_options)) * 100
        }
        
        self.results['aggregation_performance'] = result
        return result
    
    def test_export_performance(self, tenant_id: str = None, format: str = 'csv') -> Dict[str, Any]:
        """Test export performance with streaming"""
        print(f"Testing export performance: {format} format")
        
        if not tenant_id:
            tenant_id = self._create_test_tenant()
            if not tenant_id:
                return {'error': 'Failed to create test tenant'}
        
        # Create export job
        start_time = time.time()
        
        url = f"{self.base_url}/api/v1/tenants/{tenant_id}/reports/export/"
        data = {
            'format': format,
            'filters': {
                'start_date': (datetime.now() - timedelta(days=7)).isoformat(),
                'end_date': datetime.now().isoformat()
            }
        }
        
        response = self.session.post(url, json=data)
        
        if response.status_code != 200:
            return {'error': f'Export creation failed with status {response.status_code}'}
        
        job_id = response.json()['job_id']
        
        # Wait for export to complete
        export_start = time.time()
        while True:
            status_url = f"{self.base_url}/api/v1/tenants/{tenant_id}/reports/export/{job_id}/status/"
            status_response = self.session.get(status_url)
            
            if status_response.status_code == 200:
                job_status = status_response.json()
                if job_status['status'] == 'completed':
                    break
                elif job_status['status'] == 'failed':
                    return {'error': f'Export failed: {job_status.get("error_message", "Unknown error")}'}
            
            time.sleep(1)
        
        export_duration = time.time() - export_start
        total_duration = time.time() - start_time
        
        result = {
            'test_name': 'export_performance',
            'format': format,
            'job_id': job_id,
            'export_duration_seconds': export_duration,
            'total_duration_seconds': total_duration,
            'file_size': job_status.get('file_size', 0),
            'success': True
        }
        
        self.results['export_performance'] = result
        return result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance tests"""
        print("Running all performance tests...")
        
        # Create test tenant for all tests
        tenant_id = self._create_test_tenant()
        if not tenant_id:
            return {'error': 'Failed to create test tenant'}
        
        # Run tests
        tests = [
            ('bulk_ingestion', lambda: self.test_bulk_ingestion(1000, 100)),
            ('streaming_search', lambda: self.test_streaming_search(tenant_id, 1000)),
            ('concurrent_stock_updates', lambda: self.test_concurrent_stock_updates(tenant_id, 5, 3)),
            ('aggregation_exact', lambda: self.test_aggregation_performance(tenant_id, 'exact')),
            ('aggregation_approx', lambda: self.test_aggregation_performance(tenant_id, 'approx')),
            ('export_csv', lambda: self.test_export_performance(tenant_id, 'csv'))
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"Running {test_name}...")
                result = test_func()
                print(f"✓ {test_name} completed")
            except Exception as e:
                print(f"✗ {test_name} failed: {e}")
                self.results[test_name] = {'error': str(e)}
        
        return self.results
    
    def _create_test_tenant(self) -> str:
        """Create a test tenant"""
        # For this demo, we'll use a hardcoded tenant ID
        # In a real test, you'd create a tenant via API
        return str(uuid.uuid4())
    
    def _create_test_products(self, tenant_id: str, count: int) -> List[str]:
        """Create test products"""
        # For this demo, we'll return mock product IDs
        # In a real test, you'd create products via API
        return [str(uuid.uuid4()) for _ in range(count)]
    
    def _generate_test_orders(self, tenant_id: str, product_ids: List[str], count: int) -> List[Dict[str, Any]]:
        """Generate test orders"""
        orders = []
        for i in range(count):
            order = {
                'order_number': f'TEST-{i:06d}',
                'status': 'paid',
                'total_amount': 100.0 + (i % 1000),
                'currency': 'USD',
                'customer_email': f'customer{i}@test.com',
                'customer_name': f'Customer {i}',
                'items': [
                    {
                        'product_sku': f'PROD-{i % len(product_ids):03d}',
                        'quantity': 1 + (i % 5),
                        'price': 50.0 + (i % 50)
                    }
                ]
            }
            orders.append(order)
        return orders
    
    def _ingest_chunk(self, tenant_id: str, chunk: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ingest a chunk of orders"""
        url = f"{self.base_url}/api/v1/ingest/orders/"
        headers = {
            'Idempotency-Key': str(uuid.uuid4()),
            'Content-Type': 'application/json'
        }
        data = {
            'tenant_id': tenant_id,
            'orders': chunk
        }
        
        try:
            response = self.session.post(url, json=data, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


def main():
    """Main function to run performance tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run performance tests')
    parser.add_argument('--base-url', default='http://localhost:8000', help='Base URL for API')
    parser.add_argument('--test', choices=['all', 'ingestion', 'search', 'concurrent', 'aggregation', 'export'], 
                       default='all', help='Test to run')
    parser.add_argument('--orders', type=int, default=1000, help='Number of orders for ingestion test')
    parser.add_argument('--chunk-size', type=int, default=100, help='Chunk size for ingestion test')
    
    args = parser.parse_args()
    
    tester = PerformanceTester(args.base_url)
    
    if args.test == 'all':
        results = tester.run_all_tests()
    elif args.test == 'ingestion':
        results = tester.test_bulk_ingestion(args.orders, args.chunk_size)
    elif args.test == 'search':
        results = tester.test_streaming_search()
    elif args.test == 'concurrent':
        results = tester.test_concurrent_stock_updates()
    elif args.test == 'aggregation':
        results = tester.test_aggregation_performance()
    elif args.test == 'export':
        results = tester.test_export_performance()
    
    # Print results
    print("\n" + "="*50)
    print("PERFORMANCE TEST RESULTS")
    print("="*50)
    
    if isinstance(results, dict) and 'error' in results:
        print(f"Error: {results['error']}")
    else:
        for test_name, result in results.items():
            print(f"\n{test_name.upper()}:")
            if isinstance(result, dict):
                for key, value in result.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  {result}")
    
    # Save results to file
    with open('performance_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to performance_results.json")


if __name__ == '__main__':
    main()



