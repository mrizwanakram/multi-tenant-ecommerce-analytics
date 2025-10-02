import pytest
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from tenants.models import Tenant, TenantUser
from products.models import Product, Category
from customers.models import Customer
from orders.models import Order
from payments.models import Payment, PaymentMethod


class APITestCase(TestCase):
    """Base test case for API tests"""
    
    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            domain="test.example.com"
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.tenant_user = TenantUser.objects.create(
            user=self.user,
            tenant=self.tenant,
            role="admin"
        )
        
        # Set tenant in request
        self.client.force_authenticate(user=self.user)
        self.client.defaults['HTTP_X_TENANT_ID'] = str(self.tenant.id)


class TenantAPITest(APITestCase):
    """Test cases for Tenant API endpoints"""
    
    def test_tenant_list(self):
        """Test listing tenants"""
        url = reverse('tenant-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_tenant_detail(self):
        """Test retrieving tenant details"""
        url = reverse('tenant-detail', kwargs={'pk': self.tenant.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.tenant.name)
    
    def test_tenant_creation(self):
        """Test creating a new tenant"""
        url = reverse('tenant-list')
        data = {
            'name': 'New Tenant',
            'domain': 'new.example.com'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Tenant')


class ProductAPITest(APITestCase):
    """Test cases for Product API endpoints"""
    
    def setUp(self):
        super().setUp()
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
    
    def test_product_list(self):
        """Test listing products"""
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_product_detail(self):
        """Test retrieving product details"""
        url = reverse('product-detail', kwargs={'pk': self.product.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.product.name)
    
    def test_product_creation(self):
        """Test creating a new product"""
        url = reverse('product-list')
        data = {
            'name': 'New Product',
            'sku': 'NEW-001',
            'price': '149.99',
            'category': self.category.id
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Product')
    
    def test_product_analytics(self):
        """Test product analytics endpoint"""
        url = reverse('product-analytics', kwargs={'pk': self.product.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('analytics', response.data)


class CustomerAPITest(APITestCase):
    """Test cases for Customer API endpoints"""
    
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            tenant=self.tenant
        )
    
    def test_customer_list(self):
        """Test listing customers"""
        url = reverse('customer-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_customer_detail(self):
        """Test retrieving customer details"""
        url = reverse('customer-detail', kwargs={'pk': self.customer.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.customer.email)
    
    def test_customer_creation(self):
        """Test creating a new customer"""
        url = reverse('customer-list')
        data = {
            'email': 'new@example.com',
            'first_name': 'Jane',
            'last_name': 'Smith'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'new@example.com')
    
    def test_customer_analytics(self):
        """Test customer analytics endpoint"""
        url = reverse('customer-analytics', kwargs={'pk': self.customer.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('analytics', response.data)


class OrderAPITest(APITestCase):
    """Test cases for Order API endpoints"""
    
    def setUp(self):
        super().setUp()
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
    
    def test_order_list(self):
        """Test listing orders"""
        url = reverse('order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_order_detail(self):
        """Test retrieving order details"""
        url = reverse('order-detail', kwargs={'pk': self.order.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_amount'], '99.99')
    
    def test_order_creation(self):
        """Test creating a new order"""
        url = reverse('order-list')
        data = {
            'customer': self.customer.id,
            'total_amount': '149.99',
            'payment_method': 'credit_card'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total_amount'], '149.99')
    
    def test_order_analytics(self):
        """Test order analytics endpoint"""
        url = reverse('order-analytics', kwargs={'pk': self.order.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('analytics', response.data)


class PaymentAPITest(APITestCase):
    """Test cases for Payment API endpoints"""
    
    def setUp(self):
        super().setUp()
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
    
    def test_payment_list(self):
        """Test listing payments"""
        url = reverse('payment-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_payment_detail(self):
        """Test retrieving payment details"""
        url = reverse('payment-detail', kwargs={'pk': self.payment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], '99.99')
    
    def test_payment_method_list(self):
        """Test listing payment methods"""
        url = reverse('paymentmethod-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_payment_method_creation(self):
        """Test creating a new payment method"""
        url = reverse('paymentmethod-list')
        data = {
            'name': 'PayPal',
            'payment_type': 'paypal',
            'configuration': {
                'client_id': 'test_client_id',
                'client_secret': 'test_client_secret'
            }
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'PayPal')


class AnalyticsAPITest(APITestCase):
    """Test cases for Analytics API endpoints"""
    
    def test_analytics_summary(self):
        """Test analytics summary endpoint"""
        url = reverse('analytics-summary')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', response.data)
    
    def test_sales_metrics(self):
        """Test sales metrics endpoint"""
        url = reverse('sales-metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('metrics', response.data)
    
    def test_product_performance(self):
        """Test product performance endpoint"""
        url = reverse('product-performance')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('performance', response.data)
    
    def test_customer_segments(self):
        """Test customer segments endpoint"""
        url = reverse('customer-segments')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('segments', response.data)


class AuthenticationTest(APITestCase):
    """Test cases for authentication"""
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users are denied access"""
        self.client.force_authenticate(user=None)
        url = reverse('tenant-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_tenant_isolation(self):
        """Test that tenants can only access their own data"""
        # Create another tenant
        other_tenant = Tenant.objects.create(
            name="Other Tenant",
            domain="other.example.com"
        )
        
        # Create product for other tenant
        other_category = Category.objects.create(
            name="Other Category",
            tenant=other_tenant
        )
        other_product = Product.objects.create(
            name="Other Product",
            sku="OTHER-001",
            price=Decimal('199.99'),
            tenant=other_tenant,
            category=other_category
        )
        
        # Try to access other tenant's product
        url = reverse('product-detail', kwargs={'pk': other_product.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_jwt_authentication(self):
        """Test JWT token authentication"""
        from rest_framework_simplejwt.tokens import RefreshToken
        
        # Generate JWT token
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Test with JWT token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        url = reverse('tenant-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

