from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Customer, CustomerSegment, CustomerNote
from .serializers import (
    CustomerSerializer, CustomerCreateSerializer, CustomerListSerializer,
    CustomerAnalyticsSerializer, CustomerSegmentSerializer, CustomerNoteSerializer
)


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for Customer management"""
    queryset = Customer.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_vip', 'gender', 'newsletter_subscribed', 'sms_subscribed']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    ordering_fields = ['first_name', 'last_name', 'created_at', 'last_login']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter customers by tenant"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return Customer.objects.filter(tenant=self.request.tenant)
        return Customer.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return CustomerListSerializer
        elif self.action == 'create':
            return CustomerCreateSerializer
        elif self.action == 'analytics':
            return CustomerAnalyticsSerializer
        return CustomerSerializer
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get customer analytics"""
        customer = self.get_object()
        serializer = CustomerAnalyticsSerializer(customer)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add a note to customer"""
        customer = self.get_object()
        serializer = CustomerNoteSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(
                customer=customer,
                created_by=request.user
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def vip_customers(self, request):
        """Get VIP customers"""
        queryset = self.get_queryset().filter(is_vip=True)
        serializer = CustomerListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def new_customers(self, request):
        """Get new customers (last 30 days)"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        queryset = self.get_queryset().filter(created_at__gte=thirty_days_ago)
        serializer = CustomerListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def inactive_customers(self, request):
        """Get inactive customers (no orders in last 90 days)"""
        ninety_days_ago = timezone.now() - timedelta(days=90)
        queryset = self.get_queryset().filter(
            Q(last_login__lt=ninety_days_ago) | Q(last_login__isnull=True)
        )
        serializer = CustomerListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_customers(self, request):
        """Get top customers by total spent"""
        queryset = self.get_queryset().annotate(
            total_spent=Sum('orders__total_amount')
        ).order_by('-total_spent')[:10]
        serializer = CustomerListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def analytics_summary(self, request):
        """Get customer analytics summary"""
        queryset = self.get_queryset()
        
        # Date range filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Calculate analytics
        total_customers = queryset.count()
        active_customers = queryset.filter(is_active=True).count()
        vip_customers = queryset.filter(is_vip=True).count()
        new_customers = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Newsletter subscribers
        newsletter_subscribers = queryset.filter(newsletter_subscribed=True).count()
        sms_subscribers = queryset.filter(sms_subscribed=True).count()
        
        # Gender distribution
        gender_distribution = queryset.values('gender').annotate(count=Count('id'))
        
        # Customer acquisition by month (last 12 months)
        twelve_months_ago = timezone.now() - timedelta(days=365)
        monthly_acquisition = queryset.filter(
            created_at__gte=twelve_months_ago
        ).extra(
            select={'month': 'strftime("%Y-%m", created_at)'}
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        analytics_data = {
            'total_customers': total_customers,
            'active_customers': active_customers,
            'vip_customers': vip_customers,
            'new_customers': new_customers,
            'newsletter_subscribers': newsletter_subscribers,
            'sms_subscribers': sms_subscribers,
            'gender_distribution': list(gender_distribution),
            'monthly_acquisition': list(monthly_acquisition)
        }
        
        return Response(analytics_data)


class CustomerSegmentViewSet(viewsets.ModelViewSet):
    """ViewSet for CustomerSegment management"""
    queryset = CustomerSegment.objects.all()
    serializer_class = CustomerSegmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'customer_count', 'total_spent']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter segments by tenant"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return CustomerSegment.objects.filter(tenant=self.request.tenant)
        return CustomerSegment.objects.none()
    
    @action(detail=True, methods=['get'])
    def customers(self, request, pk=None):
        """Get customers in this segment"""
        segment = self.get_object()
        # This would typically involve more complex filtering based on criteria
        customers = Customer.objects.filter(tenant=self.request.tenant)
        serializer = CustomerListSerializer(customers, many=True)
        return Response(serializer.data)


class CustomerNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for CustomerNote management"""
    queryset = CustomerNote.objects.all()
    serializer_class = CustomerNoteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer']
    search_fields = ['note']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter notes by tenant through customer"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return CustomerNote.objects.filter(customer__tenant=self.request.tenant)
        return CustomerNote.objects.none()