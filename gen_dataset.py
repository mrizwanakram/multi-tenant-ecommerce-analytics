#!/usr/bin/env python3
"""
Dataset Generator for Multi-tenant Ecommerce Analytics Assessment
Generates synthetic data for testing high-throughput ingestion and analytics
"""

import os
import sys
import django
import argparse
import csv
import json
import random
import uuid
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import sqlite3
from pathlib import Path

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_analytics.settings')
django.setup()

from analytics.models import Tenant, Product, Customer, Order, OrderItem, PriceHistory, StockEvent


class DatasetGenerator:
    """Generate synthetic ecommerce data for performance testing"""
    
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Performance tracking
        self.start_time = None
        self.rows_generated = 0
        
        # Data generation settings
        self.categories = [
            'Electronics', 'Clothing', 'Books', 'Home & Garden', 'Sports',
            'Beauty', 'Toys', 'Automotive', 'Health', 'Food & Beverage'
        ]
        
        self.first_names = [
            'John', 'Jane', 'Michael', 'Sarah', 'David', 'Lisa', 'Robert', 'Emily',
            'James', 'Jessica', 'William', 'Ashley', 'Richard', 'Amanda', 'Joseph',
            'Jennifer', 'Thomas', 'Michelle', 'Christopher', 'Kimberly'
        ]
        
        self.last_names = [
            'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
            'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez',
            'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin'
        ]
    
    def generate_tenants(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate tenant data"""
        print(f"Generating {count} tenants...")
        tenants = []
        
        for i in range(count):
            tenant = {
                'id': str(uuid.uuid4()),
                'name': f'Tenant {i+1}',
                'domain': f'tenant{i+1}.example.com',
                'created_at': datetime.now() - timedelta(days=random.randint(30, 365)),
                'is_active': True
            }
            tenants.append(tenant)
        
        self._save_to_csv('tenants.csv', tenants)
        return tenants
    
    def generate_products(self, tenants: List[Dict], products_per_tenant: int = 500000) -> List[Dict[str, Any]]:
        """Generate product data"""
        print(f"Generating {products_per_tenant} products per tenant...")
        products = []
        
        for tenant in tenants:
            tenant_id = tenant['id']
            print(f"  Generating products for {tenant['name']}...")
            
            for i in range(products_per_tenant):
                product = {
                    'id': str(uuid.uuid4()),
                    'tenant_id': tenant_id,
                    'name': f'Product {i+1} - {random.choice(self.categories)}',
                    'sku': f'SKU-{tenant["name"].replace(" ", "")}-{i+1:06d}',
                    'category': random.choice(self.categories),
                    'price': round(random.uniform(10.0, 1000.0), 2),
                    'created_at': tenant['created_at'] + timedelta(days=random.randint(0, 30)),
                    'updated_at': datetime.now()
                }
                products.append(product)
        
        self._save_to_csv('products.csv', products)
        return products
    
    def generate_customers(self, tenants: List[Dict], customers_per_tenant: int = 100000) -> List[Dict[str, Any]]:
        """Generate customer data"""
        print(f"Generating {customers_per_tenant} customers per tenant...")
        customers = []
        
        for tenant in tenants:
            tenant_id = tenant['id']
            print(f"  Generating customers for {tenant['name']}...")
            
            for i in range(customers_per_tenant):
                first_name = random.choice(self.first_names)
                last_name = random.choice(self.last_names)
                customer = {
                    'id': str(uuid.uuid4()),
                    'tenant_id': tenant_id,
                    'name': f'{first_name} {last_name}',
                    'email': f'{first_name.lower()}.{last_name.lower()}{i}@example.com',
                    'phone': f'+1-{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}',
                    'created_at': tenant['created_at'] + timedelta(days=random.randint(0, 300)),
                    'updated_at': datetime.now()
                }
                customers.append(customer)
        
        self._save_to_csv('customers.csv', customers)
        return customers
    
    def generate_orders(self, tenants: List[Dict], products: List[Dict], customers: List[Dict], 
                       orders_per_tenant: int = 2000000) -> List[Dict[str, Any]]:
        """Generate order data"""
        print(f"Generating {orders_per_tenant} orders per tenant...")
        orders = []
        
        # Group products and customers by tenant
        products_by_tenant = {}
        customers_by_tenant = {}
        
        for product in products:
            tenant_id = product['tenant_id']
            if tenant_id not in products_by_tenant:
                products_by_tenant[tenant_id] = []
            products_by_tenant[tenant_id].append(product)
        
        for customer in customers:
            tenant_id = customer['tenant_id']
            if tenant_id not in customers_by_tenant:
                customers_by_tenant[tenant_id] = []
            customers_by_tenant[tenant_id].append(customer)
        
        for tenant in tenants:
            tenant_id = tenant['id']
            tenant_products = products_by_tenant.get(tenant_id, [])
            tenant_customers = customers_by_tenant.get(tenant_id, [])
            
            print(f"  Generating orders for {tenant['name']}...")
            
            for i in range(orders_per_tenant):
                # Random order date within last year
                order_date = datetime.now() - timedelta(days=random.randint(1, 365))
                
                order = {
                    'id': str(uuid.uuid4()),
                    'tenant_id': tenant_id,
                    'customer_id': random.choice(tenant_customers)['id'] if tenant_customers else None,
                    'order_number': f'ORD-{tenant["name"].replace(" ", "")}-{i+1:08d}',
                    'status': random.choices(
                        ['pending', 'paid', 'shipped', 'delivered', 'cancelled', 'refunded'],
                        weights=[5, 60, 20, 10, 3, 2]
                    )[0],
                    'total_amount': 0,  # Will be calculated after order items
                    'currency': 'USD',
                    'created_at': order_date,
                    'updated_at': order_date
                }
                orders.append(order)
        
        self._save_to_csv('orders.csv', orders)
        return orders
    
    def generate_order_items(self, orders: List[Dict], products: List[Dict], 
                           avg_items_per_order: int = 3) -> List[Dict[str, Any]]:
        """Generate order items data"""
        print(f"Generating order items (avg {avg_items_per_order} per order)...")
        order_items = []
        
        # Group products by tenant
        products_by_tenant = {}
        for product in products:
            tenant_id = product['tenant_id']
            if tenant_id not in products_by_tenant:
                products_by_tenant[tenant_id] = []
            products_by_tenant[tenant_id].append(product)
        
        # Group orders by tenant and update total amounts
        orders_by_tenant = {}
        for order in orders:
            tenant_id = order['tenant_id']
            if tenant_id not in orders_by_tenant:
                orders_by_tenant[tenant_id] = []
            orders_by_tenant[tenant_id].append(order)
        
        for tenant_id, tenant_orders in orders_by_tenant.items():
            tenant_products = products_by_tenant.get(tenant_id, [])
            print(f"  Generating order items for tenant {tenant_id}...")
            
            for order in tenant_orders:
                # Generate 1-5 items per order (avg 3)
                num_items = random.randint(1, 5)
                order_total = Decimal('0.00')
                
                for _ in range(num_items):
                    product = random.choice(tenant_products)
                    quantity = random.randint(1, 5)
                    price = Decimal(str(product['price']))
                    total_price = price * quantity
                    order_total += total_price
                    
                    order_item = {
                        'id': str(uuid.uuid4()),
                        'order_id': order['id'],
                        'product_id': product['id'],
                        'quantity': quantity,
                        'price': float(price),
                        'total_price': float(total_price),
                        'created_at': order['created_at']
                    }
                    order_items.append(order_item)
                
                # Update order total
                order['total_amount'] = float(order_total)
        
        # Update orders CSV with correct totals
        self._save_to_csv('orders.csv', orders)
        self._save_to_csv('order_items.csv', order_items)
        return order_items
    
    def generate_price_history(self, products: List[Dict], samples_per_product: int = 100) -> List[Dict[str, Any]]:
        """Generate price history data"""
        print(f"Generating price history ({samples_per_product} samples per product)...")
        price_history = []
        
        for product in products:
            print(f"  Generating price history for product {product['sku']}...")
            current_price = product['price']
            
            for i in range(samples_per_product):
                # Generate price changes over time
                price_change = random.uniform(-0.1, 0.1)  # ±10% change
                new_price = current_price * (1 + price_change)
                new_price = max(1.0, new_price)  # Minimum price of $1
                
                price_entry = {
                    'id': str(uuid.uuid4()),
                    'product_id': product['id'],
                    'price': round(new_price, 2),
                    'created_at': product['created_at'] + timedelta(days=random.randint(0, 30))
                }
                price_history.append(price_entry)
                current_price = new_price
        
        self._save_to_csv('price_history.csv', price_history)
        return price_history
    
    def generate_stock_events(self, products: List[Dict], events_per_product: int = 1000) -> List[Dict[str, Any]]:
        """Generate stock events data"""
        print(f"Generating stock events ({events_per_product} events per product)...")
        stock_events = []
        
        for product in products:
            print(f"  Generating stock events for product {product['sku']}...")
            current_stock = random.randint(100, 1000)  # Initial stock
            
            for i in range(events_per_product):
                event_type = random.choices(
                    ['sale', 'return', 'adjustment', 'restock'],
                    weights=[70, 10, 5, 15]
                )[0]
                
                if event_type == 'sale':
                    quantity_change = -random.randint(1, 10)
                elif event_type == 'return':
                    quantity_change = random.randint(1, 5)
                elif event_type == 'restock':
                    quantity_change = random.randint(10, 100)
                else:  # adjustment
                    quantity_change = random.randint(-20, 20)
                
                current_stock = max(0, current_stock + quantity_change)
                
                stock_event = {
                    'id': str(uuid.uuid4()),
                    'product_id': product['id'],
                    'event_type': event_type,
                    'quantity_change': quantity_change,
                    'quantity_after': current_stock,
                    'reference_id': f'REF-{i+1:06d}',
                    'created_at': product['created_at'] + timedelta(days=random.randint(0, 30))
                }
                stock_events.append(stock_event)
        
        self._save_to_csv('stock_events.csv', stock_events)
        return stock_events
    
    def _save_to_csv(self, filename: str, data: List[Dict[str, Any]]):
        """Save data to CSV file"""
        if not data:
            return
        
        filepath = self.output_dir / filename
        print(f"  Saving {len(data)} records to {filepath}")
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
    
    def bulk_insert_to_db(self, tenants: List[Dict], products: List[Dict], 
                         customers: List[Dict], orders: List[Dict], 
                         order_items: List[Dict], price_history: List[Dict], 
                         stock_events: List[Dict], chunk_size: int = 10000):
        """Bulk insert data into database using raw SQL for performance"""
        print("Bulk inserting data to database...")
        
        # Use raw SQL for maximum performance
        from django.db import connection
        
        def bulk_insert_raw(table_name: str, data: List[Dict], chunk_size: int):
            if not data:
                return
            
            cursor = connection.cursor()
            columns = list(data[0].keys())
            placeholders = ', '.join(['?' for _ in columns])
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # Insert in chunks
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                values = [tuple(row[col] for col in columns) for row in chunk]
                cursor.executemany(query, values)
                print(f"    Inserted {len(chunk)} records into {table_name}")
        
        # Insert in order to respect foreign key constraints
        bulk_insert_raw('tenants', tenants, chunk_size)
        bulk_insert_raw('products', products, chunk_size)
        bulk_insert_raw('customers', customers, chunk_size)
        bulk_insert_raw('orders', orders, chunk_size)
        bulk_insert_raw('order_items', order_items, chunk_size)
        bulk_insert_raw('price_history', price_history, chunk_size)
        bulk_insert_raw('stock_events', stock_events, chunk_size)
    
    def generate_dataset(self, tenants: int = 10, products_per_tenant: int = 500000,
                        customers_per_tenant: int = 100000, orders_per_tenant: int = 2000000,
                        avg_items_per_order: int = 3, samples_per_product: int = 100,
                        events_per_product: int = 1000, insert_to_db: bool = False,
                        chunk_size: int = 10000):
        """Generate complete dataset"""
        self.start_time = time.time()
        print(f"Starting dataset generation...")
        print(f"Configuration:")
        print(f"  Tenants: {tenants}")
        print(f"  Products per tenant: {products_per_tenant}")
        print(f"  Customers per tenant: {customers_per_tenant}")
        print(f"  Orders per tenant: {orders_per_tenant}")
        print(f"  Average items per order: {avg_items_per_order}")
        print(f"  Price history samples per product: {samples_per_product}")
        print(f"  Stock events per product: {events_per_product}")
        print(f"  Insert to DB: {insert_to_db}")
        print(f"  Chunk size: {chunk_size}")
        print()
        
        # Generate data
        tenants_data = self.generate_tenants(tenants)
        products_data = self.generate_products(tenants_data, products_per_tenant)
        customers_data = self.generate_customers(tenants_data, customers_per_tenant)
        orders_data = self.generate_orders(tenants_data, products_data, customers_data, orders_per_tenant)
        order_items_data = self.generate_order_items(orders_data, products_data, avg_items_per_order)
        price_history_data = self.generate_price_history(products_data, samples_per_product)
        stock_events_data = self.generate_stock_events(products_data, events_per_product)
        
        # Calculate totals
        total_products = len(products_data)
        total_customers = len(customers_data)
        total_orders = len(orders_data)
        total_order_items = len(order_items_data)
        total_price_history = len(price_history_data)
        total_stock_events = len(stock_events_data)
        
        print(f"\nDataset generation completed!")
        print(f"Total records generated:")
        print(f"  Tenants: {len(tenants_data)}")
        print(f"  Products: {total_products}")
        print(f"  Customers: {total_customers}")
        print(f"  Orders: {total_orders}")
        print(f"  Order Items: {total_order_items}")
        print(f"  Price History: {total_price_history}")
        print(f"  Stock Events: {total_stock_events}")
        
        # Calculate throughput
        elapsed_time = time.time() - self.start_time
        total_records = (len(tenants_data) + total_products + total_customers + 
                        total_orders + total_order_items + total_price_history + total_stock_events)
        throughput = total_records / elapsed_time if elapsed_time > 0 else 0
        
        print(f"\nPerformance metrics:")
        print(f"  Total time: {elapsed_time:.2f} seconds")
        print(f"  Total records: {total_records:,}")
        print(f"  Throughput: {throughput:,.0f} records/second")
        
        # Insert to database if requested
        if insert_to_db:
            print(f"\nBulk inserting to database...")
            insert_start = time.time()
            self.bulk_insert_to_db(tenants_data, products_data, customers_data, 
                                 orders_data, order_items_data, price_history_data, 
                                 stock_events_data, chunk_size)
            insert_time = time.time() - insert_start
            insert_throughput = total_records / insert_time if insert_time > 0 else 0
            print(f"  Insert time: {insert_time:.2f} seconds")
            print(f"  Insert throughput: {insert_throughput:,.0f} records/second")
        
        print(f"\nFiles saved to: {self.output_dir.absolute()}")
        return {
            'tenants': len(tenants_data),
            'products': total_products,
            'customers': total_customers,
            'orders': total_orders,
            'order_items': total_order_items,
            'price_history': total_price_history,
            'stock_events': total_stock_events,
            'total_records': total_records,
            'generation_time': elapsed_time,
            'generation_throughput': throughput
        }


def main():
    parser = argparse.ArgumentParser(description='Generate synthetic ecommerce dataset')
    parser.add_argument('--tenants', type=int, default=10, help='Number of tenants')
    parser.add_argument('--products', type=int, default=500000, help='Products per tenant')
    parser.add_argument('--customers', type=int, default=100000, help='Customers per tenant')
    parser.add_argument('--orders', type=int, default=2000000, help='Orders per tenant')
    parser.add_argument('--items-per-order', type=int, default=3, help='Average items per order')
    parser.add_argument('--price-samples', type=int, default=100, help='Price history samples per product')
    parser.add_argument('--stock-events', type=int, default=1000, help='Stock events per product')
    parser.add_argument('--insert-db', action='store_true', help='Insert data into database')
    parser.add_argument('--chunk-size', type=int, default=10000, help='Chunk size for bulk insert')
    parser.add_argument('--output-dir', type=str, default='data', help='Output directory for CSV files')
    parser.add_argument('--preset', type=str, choices=['small', 'medium', 'large'], 
                       help='Use preset configuration')
    
    args = parser.parse_args()
    
    # Apply presets
    if args.preset == 'small':
        args.tenants = 2
        args.products = 10000
        args.customers = 5000
        args.orders = 50000
        args.stock_events = 100
    elif args.preset == 'medium':
        args.tenants = 5
        args.products = 100000
        args.customers = 50000
        args.orders = 500000
        args.stock_events = 500
    elif args.preset == 'large':
        args.tenants = 10
        args.products = 500000
        args.customers = 100000
        args.orders = 2000000
        args.stock_events = 1000
    
    # Generate dataset
    generator = DatasetGenerator(args.output_dir)
    generator.generate_dataset(
        tenants=args.tenants,
        products_per_tenant=args.products,
        customers_per_tenant=args.customers,
        orders_per_tenant=args.orders,
        avg_items_per_order=args.items_per_order,
        samples_per_product=args.price_samples,
        events_per_product=args.stock_events,
        insert_to_db=args.insert_db,
        chunk_size=args.chunk_size
    )


if __name__ == '__main__':
    main()



