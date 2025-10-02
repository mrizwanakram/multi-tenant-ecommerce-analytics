from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Order, OrderItem, OrderStatusHistory, Refund
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderListSerializer,
    OrderUpdateStatusSerializer, OrderItemSerializer, RefundSerializer
)


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for Order management"""
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'payment_method']
    search_fields = ['order_number', 'customer__first_name', 'customer__last_name', 'customer__email']
    ordering_fields = ['created_at', 'total_amount', 'order_number']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter orders by tenant"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return Order.objects.filter(tenant=self.request.tenant).select_related('customer')
        return Order.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        elif self.action == 'update_status':
            return OrderUpdateStatusSerializer
        return OrderSerializer
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update order status"""
        order = self.get_object()
        serializer = OrderUpdateStatusSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.update(order, serializer.validated_data)
            return Response({'message': 'Order status updated successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def create_refund(self, request, pk=None):
        """Create a refund for an order"""
        order = self.get_object()
        serializer = RefundSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(
                order=order,
                processed_by=request.user
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get order analytics"""
        queryset = self.get_queryset()
        
        # Date range filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Calculate analytics
        total_orders = queryset.count()
        total_revenue = queryset.aggregate(total=Sum('total_amount'))['total'] or 0
        average_order_value = queryset.aggregate(avg=Avg('total_amount'))['avg'] or 0
        
        # Orders by status
        orders_by_status = queryset.values('status').annotate(count=Count('id'))
        
        # Orders by payment status
        orders_by_payment = queryset.values('payment_status').annotate(count=Count('id'))
        
        # Daily orders (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_orders = queryset.filter(created_at__gte=thirty_days_ago).extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(count=Count('id')).order_by('day')
        
        analytics_data = {
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'average_order_value': float(average_order_value),
            'orders_by_status': list(orders_by_status),
            'orders_by_payment_status': list(orders_by_payment),
            'daily_orders': list(daily_orders)
        }
        
        return Response(analytics_data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent orders"""
        queryset = self.get_queryset()[:10]
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending orders"""
        queryset = self.get_queryset().filter(status='pending')
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def high_value(self, request):
        """Get high value orders"""
        min_amount = request.query_params.get('min_amount', 100)
        queryset = self.get_queryset().filter(total_amount__gte=min_amount)
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)


class RefundViewSet(viewsets.ModelViewSet):
    """ViewSet for Refund management"""
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'order']
    search_fields = ['order__order_number', 'reason']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter refunds by tenant through order"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return Refund.objects.filter(order__tenant=self.request.tenant)
        return Refund.objects.none()
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a refund"""
        refund = self.get_object()
        refund.status = 'approved'
        refund.processed_by = request.user
        refund.processed_at = timezone.now()
        refund.save()
        
        return Response({'message': 'Refund approved successfully'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a refund"""
        refund = self.get_object()
        refund.status = 'rejected'
        refund.processed_by = request.user
        refund.processed_at = timezone.now()
        refund.save()
        
        return Response({'message': 'Refund rejected'})