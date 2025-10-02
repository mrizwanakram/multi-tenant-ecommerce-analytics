from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Tenant, TenantUser
from .serializers import TenantSerializer, TenantUserSerializer, CreateTenantUserSerializer


class TenantViewSet(viewsets.ModelViewSet):
    """ViewSet for Tenant management"""
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter tenants based on user permissions"""
        if self.request.user.is_superuser:
            return Tenant.objects.all()
        
        # For regular users, return only their associated tenants
        return Tenant.objects.filter(
            users__user=self.request.user,
            users__is_active=True
        )
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """Get users for a specific tenant"""
        tenant = self.get_object()
        users = TenantUser.objects.filter(tenant=tenant, is_active=True)
        serializer = TenantUserSerializer(users, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_user(self, request, pk=None):
        """Add a new user to the tenant"""
        tenant = self.get_object()
        serializer = CreateTenantUserSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(tenant=tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def analytics_summary(self, request, pk=None):
        """Get analytics summary for the tenant"""
        tenant = self.get_object()
        
        # This would typically involve more complex analytics queries
        summary = {
            'total_products': tenant.products.count(),
            'total_orders': tenant.orders.count(),
            'total_customers': tenant.customers.count(),
            'total_revenue': sum(order.total_amount for order in tenant.orders.all()),
        }
        
        return Response(summary)


class TenantUserViewSet(viewsets.ModelViewSet):
    """ViewSet for TenantUser management"""
    queryset = TenantUser.objects.all()
    serializer_class = TenantUserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter tenant users based on user permissions"""
        if self.request.user.is_superuser:
            return TenantUser.objects.all()
        
        # For regular users, return only users from their tenants
        return TenantUser.objects.filter(
            tenant__users__user=self.request.user,
            tenant__users__is_active=True
        )