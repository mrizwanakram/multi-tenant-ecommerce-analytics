from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tenants.models import Tenant, TenantUser
from products.models import Category, Product, ProductVariant
from customers.models import Customer, CustomerSegment
from orders.models import Order, OrderItem
from analytics.models import AnalyticsEvent, SalesMetric, ProductAnalytics, CustomerAnalytics
from decimal import Decimal
import random
from datetime import datetime, timedelta
import uuid


class Command(BaseCommand):
    help = 'Populate the database with sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenants',
            type=int,
            default=2,
            help='Number of tenants to create'
        )
        parser.add_argument(
            '--products-per-tenant',
            type=int,
            default=20,
            help='Number of products per tenant'
        )
        parser.add_argument(
            '--customers-per-tenant',
            type=int,
            default=50,
            help='Number of customers per tenant'
        )
        parser.add_argument(
            '--orders-per-tenant',
            type=int,
            default=100,
            help='Number of orders per tenant'
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate sample data...')
        
        # Create tenants
        tenants = self.create_tenants(options['tenants'])
        
        for tenant in tenants:
            self.stdout.write(f'Creating data for tenant: {tenant.name}')
            
            # Create categories
            categories = self.create_categories(tenant)
            
            # Create products
            products = self.create_products(tenant, categories, options['products_per_tenant'])
            
            # Create customers
            customers = self.create_customers(tenant, options['customers_per_tenant'])
            
            # Create customer segments
            self.create_customer_segments(tenant, customers)
            
            # Create orders
            orders = self.create_orders(tenant, customers, products, options['orders_per_tenant'])
            
            # Create analytics data
            self.create_analytics_data(tenant, products, customers, orders)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated sample data!')
        )

    def create_tenants(self, count):
        """Create sample tenants"""
        tenants = []
        for i in range(count):
            tenant = Tenant.objects.create(
                name=f'Sample Store {i+1}',
                domain=f'store{i+1}',
                timezone='UTC',
                currency='USD'
            )
            tenants.append(tenant)
            self.stdout.write(f'Created tenant: {tenant.name}')
        return tenants

    def create_categories(self, tenant):
        """Create product categories"""
        categories = [
            'Electronics', 'Clothing', 'Books', 'Home & Garden', 'Sports',
            'Beauty', 'Toys', 'Automotive', 'Health', 'Food & Beverage'
        ]
        
        created_categories = []
        for category_name in categories:
            category = Category.objects.create(
                name=category_name,
                description=f'Products in {category_name} category',
                tenant=tenant
            )
            created_categories.append(category)
        
        return created_categories

    def create_products(self, tenant, categories, count):
        """Create sample products"""
        products = []
        
        product_names = [
            'Wireless Headphones', 'Smart Watch', 'Laptop Stand', 'Bluetooth Speaker',
            'Phone Case', 'Charging Cable', 'Power Bank', 'Tablet Cover',
            'Gaming Mouse', 'Mechanical Keyboard', 'Monitor Stand', 'Webcam',
            'Desk Lamp', 'Coffee Maker', 'Water Bottle', 'Backpack',
            'Running Shoes', 'Yoga Mat', 'Dumbbells', 'Resistance Bands'
        ]
        
        for i in range(count):
            category = random.choice(categories)
            name = random.choice(product_names) + f' {i+1}'
            
            product = Product.objects.create(
                name=name,
                description=f'High-quality {name.lower()} for your needs',
                sku=f'SKU-{tenant.domain.upper()}-{i+1:04d}',
                price=Decimal(str(random.uniform(10, 500))).quantize(Decimal('0.01')),
                cost_price=Decimal(str(random.uniform(5, 250))).quantize(Decimal('0.01')),
                category=category,
                tenant=tenant,
                stock_quantity=random.randint(0, 100),
                min_stock_level=random.randint(5, 20),
                is_active=random.choice([True, True, True, False]),  # 75% active
                is_digital=random.choice([True, False, False, False]),  # 25% digital
                tags=random.sample(['popular', 'new', 'sale', 'premium', 'eco-friendly'], random.randint(1, 3))
            )
            products.append(product)
            
            # Create product analytics
            ProductAnalytics.objects.create(
                product=product,
                total_views=random.randint(0, 1000),
                unique_views=random.randint(0, 500),
                add_to_cart_count=random.randint(0, 100),
                purchase_count=random.randint(0, 50),
                total_revenue=product.price * random.randint(0, 20),
                total_units_sold=random.randint(0, 20),
                average_rating=Decimal(str(random.uniform(3.0, 5.0))).quantize(Decimal('0.1')),
                total_reviews=random.randint(0, 50)
            )
        
        return products

    def create_customers(self, tenant, count):
        """Create sample customers"""
        customers = []
        
        first_names = ['John', 'Jane', 'Mike', 'Sarah', 'David', 'Lisa', 'Chris', 'Emma', 'Alex', 'Maria']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
        
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            customer = Customer.objects.create(
                email=f'{first_name.lower()}.{last_name.lower()}{i+1}@example.com',
                first_name=first_name,
                last_name=last_name,
                phone=f'+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}',
                tenant=tenant,
                address_line_1=f'{random.randint(100, 9999)} Main St',
                city=random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']),
                state=random.choice(['NY', 'CA', 'IL', 'TX', 'AZ']),
                postal_code=f'{random.randint(10000, 99999)}',
                country='USA',
                is_vip=random.choice([True, False, False, False]),  # 25% VIP
                newsletter_subscribed=random.choice([True, False]),
                sms_subscribed=random.choice([True, False, False])  # 33% SMS
            )
            customers.append(customer)
        
        return customers

    def create_customer_segments(self, tenant, customers):
        """Create customer segments"""
        # High-value customers
        high_value_customers = random.sample(customers, min(10, len(customers) // 5))
        CustomerSegment.objects.create(
            name='High Value Customers',
            description='Customers with high lifetime value',
            tenant=tenant,
            criteria={'min_total_spent': 1000},
            customer_count=len(high_value_customers)
        )
        
        # New customers
        new_customers = random.sample(customers, min(15, len(customers) // 3))
        CustomerSegment.objects.create(
            name='New Customers',
            description='Recently registered customers',
            tenant=tenant,
            criteria={'registration_days': 30},
            customer_count=len(new_customers)
        )

    def create_orders(self, tenant, customers, products, count):
        """Create sample orders"""
        orders = []
        
        statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
        payment_methods = ['credit_card', 'paypal', 'stripe', 'bank_transfer']
        
        for i in range(count):
            customer = random.choice(customers)
            status = random.choices(statuses, weights=[10, 20, 15, 50, 5])[0]
            
            # Create order
            order = Order.objects.create(
                order_number=f'ORD-{tenant.domain.upper()}-{i+1:06d}',
                customer=customer,
                tenant=tenant,
                status=status,
                subtotal=Decimal('0.00'),
                total_amount=Decimal('0.00'),
                payment_status='paid' if status in ['confirmed', 'shipped', 'delivered'] else 'pending',
                payment_method=random.choice(payment_methods),
                shipping_address={
                    'address_line_1': customer.address_line_1,
                    'city': customer.city,
                    'state': customer.state,
                    'postal_code': customer.postal_code,
                    'country': customer.country
                },
                billing_address={
                    'address_line_1': customer.address_line_1,
                    'city': customer.city,
                    'state': customer.state,
                    'postal_code': customer.postal_code,
                    'country': customer.country
                }
            )
            
            # Create order items
            num_items = random.randint(1, 5)
            selected_products = random.sample(products, min(num_items, len(products)))
            
            subtotal = Decimal('0.00')
            for product in selected_products:
                quantity = random.randint(1, 3)
                unit_price = product.price
                total_price = unit_price * quantity
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                    product_name=product.name,
                    product_sku=product.sku
                )
                
                subtotal += total_price
            
            # Update order totals
            tax_rate = Decimal('0.08')  # 8% tax
            shipping_cost = Decimal('9.99') if subtotal < 50 else Decimal('0.00')
            tax_amount = subtotal * tax_rate
            total_amount = subtotal + tax_amount + shipping_cost
            
            order.subtotal = subtotal
            order.tax_amount = tax_amount
            order.shipping_amount = shipping_cost
            order.total_amount = total_amount
            order.save()
            
            orders.append(order)
        
        return orders

    def create_analytics_data(self, tenant, products, customers, orders):
        """Create analytics data"""
        # Create sales metrics for the last 30 days
        for i in range(30):
            date = datetime.now().date() - timedelta(days=i)
            
            # Calculate daily metrics
            daily_orders = [order for order in orders if order.created_at.date() == date]
            total_revenue = sum(order.total_amount for order in daily_orders)
            total_orders = len(daily_orders)
            total_units = sum(sum(item.quantity for item in order.items.all()) for order in daily_orders)
            
            if total_orders > 0:
                avg_order_value = total_revenue / total_orders
            else:
                avg_order_value = Decimal('0.00')
            
            # Create sales metric
            SalesMetric.objects.create(
                tenant=tenant,
                date=date,
                total_orders=total_orders,
                total_revenue=total_revenue,
                total_units_sold=total_units,
                average_order_value=avg_order_value,
                new_customers=random.randint(0, 5),
                returning_customers=random.randint(0, 10),
                total_customers=len(customers),
                unique_products_sold=len(set(item.product for order in daily_orders for item in order.items.all())),
                conversion_rate=Decimal(str(random.uniform(1.0, 5.0))).quantize(Decimal('0.01')),
                cart_abandonment_rate=Decimal(str(random.uniform(60.0, 80.0))).quantize(Decimal('0.01'))
            )
        
        # Create customer analytics
        for customer in customers:
            customer_orders = [order for order in orders if order.customer == customer]
            total_spent = sum(order.total_amount for order in customer_orders)
            total_orders_count = len(customer_orders)
            
            if total_orders_count > 0:
                avg_order_value = total_spent / total_orders_count
            else:
                avg_order_value = Decimal('0.00')
            
            CustomerAnalytics.objects.create(
                customer=customer,
                total_orders=total_orders_count,
                total_spent=total_spent,
                average_order_value=avg_order_value,
                first_order_date=customer_orders[0].created_at if customer_orders else None,
                last_order_date=customer_orders[-1].created_at if customer_orders else None,
                unique_products_purchased=len(set(item.product for order in customer_orders for item in order.items.all())),
                total_page_views=random.randint(0, 100),
                total_sessions=random.randint(0, 20)
            )
        
        # Create analytics events
        event_types = ['page_view', 'product_view', 'add_to_cart', 'purchase', 'search']
        for _ in range(1000):  # Create 1000 random events
            AnalyticsEvent.objects.create(
                tenant=tenant,
                event_type=random.choice(event_types),
                customer=random.choice(customers) if random.choice([True, False]) else None,
                product=random.choice(products) if random.choice([True, False]) else None,
                order=random.choice(orders) if random.choice([True, False]) else None,
                session_id=str(uuid.uuid4()),
                event_data={'test': True},
                page_url=f'https://{tenant.domain}.example.com/products/',
                created_at=datetime.now() - timedelta(days=random.randint(0, 30))
            )
