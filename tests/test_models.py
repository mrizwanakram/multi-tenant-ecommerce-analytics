import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from tenants.models import Tenant, TenantUser
from products.models import Product, Category
from customers.models import Customer
from orders.models import Order, OrderItem
from payments.models import Payment, PaymentMethod
from analytics.models import SalesMetric, PriceHistory
import uuid


class TenantModelTest(TestCase):
    """Test cases for Tenant model"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            domain="test.example.com"
        )
    
    def test_tenant_creation(self):
        """Test tenant creation with required fields"""
        self.assertEqual(self.tenant.name, "Test Tenant")
        self.assertEqual(self.tenant.domain, "test.example.com")
        self.assertTrue(self.tenant.is_active)
        self.assertIsNotNone(self.tenant.api_key)
    
    def test_tenant_str_representation(self):
        """Test string representation of tenant"""
        self.assertEqual(str(self.tenant), "Test Tenant")
    
    def test_tenant_api_key_generation(self):
        """Test that API key is automatically generated"""
        self.assertIsNotNone(self.tenant.api_key)
        self.assertEqual(len(self.tenant.api_key), 36)  # UUID length


class ProductModelTest(TestCase):
    """Test cases for Product model"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            domain="test.example.com"
        )
        self.category = Category.objects.create(
            name="Electronics",
            tenant=self.tenant
        )
        self.product = Product.objects.create(
            name="Test Product",
            sku="TEST-001",
            price=Decimal('99.99'),
            tenant=self.tenant,
            category=self.category
        )
    
    def test_product_creation(self):
        """Test product creation with required fields"""
        self.assertEqual(self.product.name, "Test Product")
        self.assertEqual(self.product.sku, "TEST-001")
        self.assertEqual(self.product.price, Decimal('99.99'))
        self.assertEqual(self.product.tenant, self.tenant)
        self.assertEqual(self.product.category, self.category)
    
    def test_product_str_representation(self):
        """Test string representation of product"""
        expected = f"{self.product.name} ({self.product.sku})"
        self.assertEqual(str(self.product), expected)
    
    def test_product_profit_margin_calculation(self):
        """Test profit margin calculation"""
        self.product.cost_price = Decimal('50.00')
        self.product.save()
        
        expected_margin = ((Decimal('99.99') - Decimal('50.00')) / Decimal('99.99')) * 100
        self.assertEqual(self.product.profit_margin, expected_margin)
    
    def test_product_profit_margin_no_cost_price(self):
        """Test profit margin when cost price is not set"""
        self.assertEqual(self.product.profit_margin, 0)


class CustomerModelTest(TestCase):
    """Test cases for Customer model"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            domain="test.example.com"
        )
        self.customer = Customer.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            tenant=self.tenant
        )
    
    def test_customer_creation(self):
        """Test customer creation with required fields"""
        self.assertEqual(self.customer.email, "test@example.com")
        self.assertEqual(self.customer.first_name, "John")
        self.assertEqual(self.customer.last_name, "Doe")
        self.assertEqual(self.customer.tenant, self.tenant)
    
    def test_customer_full_name_property(self):
        """Test full_name property"""
        expected = f"{self.customer.first_name} {self.customer.last_name}"
        self.assertEqual(self.customer.full_name, expected)
    
    def test_customer_str_representation(self):
        """Test string representation of customer"""
        expected = f"{self.customer.first_name} {self.customer.last_name} ({self.customer.email})"
        self.assertEqual(str(self.customer), expected)


class OrderModelTest(TestCase):
    """Test cases for Order model"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            domain="test.example.com"
        )
        self.customer = Customer.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            tenant=self.tenant
        )
        self.order = Order.objects.create(
            customer=self.customer,
            tenant=self.tenant,
            total_amount=Decimal('99.99'),
            payment_method='credit_card'
        )
    
    def test_order_creation(self):
        """Test order creation with required fields"""
        self.assertEqual(self.order.customer, self.customer)
        self.assertEqual(self.order.tenant, self.tenant)
        self.assertEqual(self.order.total_amount, Decimal('99.99'))
        self.assertEqual(self.order.status, 'pending')
        self.assertEqual(self.order.payment_status, 'pending')
    
    def test_order_number_generation(self):
        """Test automatic order number generation"""
        self.assertIsNotNone(self.order.order_number)
        self.assertTrue(self.order.order_number.startswith('ORD-'))
    
    def test_order_str_representation(self):
        """Test string representation of order"""
        expected = f"Order {self.order.order_number} - {self.customer.full_name}"
        self.assertEqual(str(self.order), expected)


class PaymentModelTest(TestCase):
    """Test cases for Payment model"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            domain="test.example.com"
        )
        self.customer = Customer.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            tenant=self.tenant
        )
        self.order = Order.objects.create(
            customer=self.customer,
            tenant=self.tenant,
            total_amount=Decimal('99.99'),
            payment_method='credit_card'
        )
        self.payment_method = PaymentMethod.objects.create(
            tenant=self.tenant,
            name="Stripe",
            payment_type="stripe",
            configuration={"secret_key": "sk_test_123"}
        )
        self.payment = Payment.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method=self.payment_method,
            amount=Decimal('99.99'),
            status='pending'
        )
    
    def test_payment_creation(self):
        """Test payment creation with required fields"""
        self.assertEqual(self.payment.tenant, self.tenant)
        self.assertEqual(self.payment.order, self.order)
        self.assertEqual(self.payment.payment_method, self.payment_method)
        self.assertEqual(self.payment.amount, Decimal('99.99'))
        self.assertEqual(self.payment.status, 'pending')
    
    def test_payment_str_representation(self):
        """Test string representation of payment"""
        expected = f"Payment {self.payment.id} - {self.order.id} - {self.payment.status}"
        self.assertEqual(str(self.payment), expected)


class SalesMetricModelTest(TestCase):
    """Test cases for SalesMetric model"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            domain="test.example.com"
        )
        self.sales_metric = SalesMetric.objects.create(
            tenant=self.tenant,
            date="2024-01-01",
            revenue=Decimal('1000.00'),
            orders_count=10,
            customers_count=5
        )
    
    def test_sales_metric_creation(self):
        """Test sales metric creation"""
        self.assertEqual(self.sales_metric.tenant, self.tenant)
        self.assertEqual(self.sales_metric.date, "2024-01-01")
        self.assertEqual(self.sales_metric.revenue, Decimal('1000.00'))
        self.assertEqual(self.sales_metric.orders_count, 10)
        self.assertEqual(self.sales_metric.customers_count, 5)
    
    def test_sales_metric_str_representation(self):
        """Test string representation of sales metric"""
        expected = f"{self.tenant.name} - 2024-01-01 - $1000.00"
        self.assertEqual(str(self.sales_metric), expected)


class PriceHistoryModelTest(TestCase):
    """Test cases for PriceHistory model"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            domain="test.example.com"
        )
        self.category = Category.objects.create(
            name="Electronics",
            tenant=self.tenant
        )
        self.product = Product.objects.create(
            name="Test Product",
            sku="TEST-001",
            price=Decimal('99.99'),
            tenant=self.tenant,
            category=self.category
        )
        self.price_history = PriceHistory.objects.create(
            product=self.product,
            price=Decimal('89.99')
        )
    
    def test_price_history_creation(self):
        """Test price history creation"""
        self.assertEqual(self.price_history.product, self.product)
        self.assertEqual(self.price_history.price, Decimal('89.99'))
        self.assertIsNotNone(self.price_history.created_at)
    
    def test_price_history_str_representation(self):
        """Test string representation of price history"""
        expected = f"{self.product.name} - $89.99"
        self.assertEqual(str(self.price_history), expected)

