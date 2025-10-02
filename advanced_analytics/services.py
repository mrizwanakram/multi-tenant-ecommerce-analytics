import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from django.core.cache import cache
from .models import RealTimeMetric, AnalyticsReport, DataExport, AlertRule, AlertLog
from products.models import Product, Category
from orders.models import Order, OrderItem
from customers.models import Customer
from analytics.models import SalesMetric, CustomerAnalytics, ProductAnalytics
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import json


class AdvancedAnalyticsService:
    """Service for advanced analytics calculations and data processing"""
    
    def __init__(self, tenant):
        self.tenant = tenant
    
    def get_realtime_metrics(self, metric_types=None):
        """Get real-time metrics for dashboard"""
        if metric_types is None:
            metric_types = ['revenue', 'orders', 'customers', 'conversion']
        
        metrics = {}
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for metric_type in metric_types:
            if metric_type == 'revenue':
                current_value = self._calculate_revenue(today_start, now)
                previous_value = self._calculate_revenue(
                    today_start - timedelta(days=1), 
                    today_start
                )
            elif metric_type == 'orders':
                current_value = self._calculate_orders(today_start, now)
                previous_value = self._calculate_orders(
                    today_start - timedelta(days=1), 
                    today_start
                )
            elif metric_type == 'customers':
                current_value = self._calculate_customers(today_start, now)
                previous_value = self._calculate_customers(
                    today_start - timedelta(days=1), 
                    today_start
                )
            elif metric_type == 'conversion':
                current_value = self._calculate_conversion_rate(today_start, now)
                previous_value = self._calculate_conversion_rate(
                    today_start - timedelta(days=1), 
                    today_start
                )
            else:
                continue
            
            # Calculate change percentage
            change_percentage = None
            if previous_value and previous_value > 0:
                change_percentage = ((current_value - previous_value) / previous_value) * 100
            
            # Create or update real-time metric
            metric, created = RealTimeMetric.objects.get_or_create(
                tenant=self.tenant,
                metric_type=metric_type,
                period_start=today_start,
                defaults={
                    'current_value': current_value,
                    'previous_value': previous_value,
                    'change_percentage': change_percentage,
                    'period_end': now,
                }
            )
            
            if not created:
                metric.current_value = current_value
                metric.previous_value = previous_value
                metric.change_percentage = change_percentage
                metric.period_end = now
                metric.save()
            
            metrics[metric_type] = {
                'current_value': float(current_value),
                'previous_value': float(previous_value) if previous_value else None,
                'change_percentage': float(change_percentage) if change_percentage else None,
                'trend': 'up' if change_percentage and change_percentage > 0 else 'down' if change_percentage and change_percentage < 0 else 'neutral'
            }
        
        return metrics
    
    def _calculate_revenue(self, start_date, end_date):
        """Calculate revenue for date range"""
        revenue = Order.objects.filter(
            tenant=self.tenant,
            created_at__gte=start_date,
            created_at__lte=end_date,
            status__in=['paid', 'shipped', 'delivered']
        ).aggregate(total=Sum('total_amount'))['total']
        return Decimal(str(revenue)) if revenue else Decimal('0.00')
    
    def _calculate_orders(self, start_date, end_date):
        """Calculate order count for date range"""
        return Order.objects.filter(
            tenant=self.tenant,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
    
    def _calculate_customers(self, start_date, end_date):
        """Calculate new customers for date range"""
        return Customer.objects.filter(
            tenant=self.tenant,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
    
    def _calculate_conversion_rate(self, start_date, end_date):
        """Calculate conversion rate for date range"""
        # This is a simplified calculation
        # In reality, you'd need session data to calculate proper conversion rate
        orders = Order.objects.filter(
            tenant=self.tenant,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Assuming some baseline sessions (this would come from analytics)
        sessions = max(orders * 10, 100)  # Placeholder calculation
        return (orders / sessions) * 100 if sessions > 0 else 0
    
    def generate_sales_chart_data(self, start_date, end_date, group_by='day'):
        """Generate sales chart data for visualization"""
        orders = Order.objects.filter(
            tenant=self.tenant,
            created_at__gte=start_date,
            created_at__lte=end_date,
            status__in=['paid', 'shipped', 'delivered']
        ).order_by('created_at')
        
        # Convert to DataFrame for easier manipulation
        data = []
        for order in orders:
            data.append({
                'date': order.created_at.date(),
                'revenue': float(order.total_amount),
                'orders': 1,
                'customers': 1 if order.customer else 0
            })
        
        df = pd.DataFrame(data)
        
        if df.empty:
            return {
                'labels': [],
                'datasets': []
            }
        
        # Group by specified period
        if group_by == 'day':
            grouped = df.groupby('date').agg({
                'revenue': 'sum',
                'orders': 'sum',
                'customers': 'sum'
            }).reset_index()
        elif group_by == 'week':
            df['week'] = df['date'].dt.to_period('W')
            grouped = df.groupby('week').agg({
                'revenue': 'sum',
                'orders': 'sum',
                'customers': 'sum'
            }).reset_index()
            grouped['date'] = grouped['week'].dt.start_time.dt.date
        elif group_by == 'month':
            df['month'] = df['date'].dt.to_period('M')
            grouped = df.groupby('month').agg({
                'revenue': 'sum',
                'orders': 'sum',
                'customers': 'sum'
            }).reset_index()
            grouped['date'] = grouped['month'].dt.start_time.dt.date
        
        return {
            'labels': [str(date) for date in grouped['date']],
            'datasets': [
                {
                    'label': 'Revenue',
                    'data': grouped['revenue'].tolist(),
                    'type': 'line',
                    'yAxisID': 'y'
                },
                {
                    'label': 'Orders',
                    'data': grouped['orders'].tolist(),
                    'type': 'bar',
                    'yAxisID': 'y1'
                }
            ]
        }
    
    def generate_product_performance_data(self, start_date, end_date, limit=10):
        """Generate product performance data"""
        products = Product.objects.filter(
            tenant=self.tenant,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).annotate(
            total_sales=Sum('orderitem__quantity'),
            total_revenue=Sum('orderitem__price')
        ).order_by('-total_revenue')[:limit]
        
        data = []
        for product in products:
            data.append({
                'id': str(product.id),
                'name': product.name,
                'sales': product.total_sales or 0,
                'revenue': float(product.total_revenue or 0),
                'price': float(product.price),
                'category': product.category.name if product.category else 'Uncategorized'
            })
        
        return data
    
    def generate_customer_segmentation_data(self, start_date, end_date):
        """Generate customer segmentation data"""
        customers = Customer.objects.filter(
            tenant=self.tenant,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).annotate(
            total_orders=Count('orders'),
            total_spent=Sum('orders__total_amount')
        )
        
        # Segment customers based on RFM analysis
        segments = {
            'champions': [],
            'loyal_customers': [],
            'potential_loyalists': [],
            'new_customers': [],
            'at_risk': [],
            'cannot_lose_them': [],
            'hibernating': []
        }
        
        for customer in customers:
            total_spent = float(customer.total_spent or 0)
            total_orders = customer.total_orders or 0
            
            if total_spent > 1000 and total_orders > 10:
                segments['champions'].append(customer)
            elif total_spent > 500 and total_orders > 5:
                segments['loyal_customers'].append(customer)
            elif total_spent > 100 and total_orders > 2:
                segments['potential_loyalists'].append(customer)
            elif total_orders == 1:
                segments['new_customers'].append(customer)
            elif total_spent < 50 and total_orders < 3:
                segments['at_risk'].append(customer)
            elif total_spent > 2000:
                segments['cannot_lose_them'].append(customer)
            else:
                segments['hibernating'].append(customer)
        
        return {
            'segments': {k: len(v) for k, v in segments.items()},
            'total_customers': customers.count(),
            'average_order_value': customers.aggregate(avg=Avg('orders__total_amount'))['avg'] or 0
        }
    
    def generate_plotly_chart(self, chart_type, data, title="Chart"):
        """Generate Plotly chart configuration"""
        if chart_type == 'line':
            fig = px.line(data, x='date', y='revenue', title=title)
        elif chart_type == 'bar':
            fig = px.bar(data, x='date', y='revenue', title=title)
        elif chart_type == 'pie':
            fig = px.pie(data, values='revenue', names='category', title=title)
        elif chart_type == 'scatter':
            fig = px.scatter(data, x='orders', y='revenue', title=title)
        else:
            fig = px.line(data, x='date', y='revenue', title=title)
        
        # Convert to JSON
        chart_json = json.dumps(fig, cls=PlotlyJSONEncoder)
        return chart_json
    
    def check_alert_rules(self):
        """Check all active alert rules and trigger alerts if needed"""
        now = timezone.now()
        active_rules = AlertRule.objects.filter(
            tenant=self.tenant,
            is_active=True
        )
        
        for rule in active_rules:
            # Check if we're in cooldown period
            if rule.last_triggered:
                cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
                if now < cooldown_end:
                    continue
            
            # Get current metric value
            current_value = self._get_metric_value(rule.metric_type)
            
            # Check if alert condition is met
            should_alert = self._evaluate_alert_condition(
                current_value, 
                rule.comparison_operator, 
                rule.threshold_value
            )
            
            if should_alert:
                # Create alert log
                AlertLog.objects.create(
                    tenant=self.tenant,
                    alert_rule=rule,
                    metric_value=current_value,
                    threshold_value=rule.threshold_value,
                    message=f"Alert: {rule.metric_type} is {rule.comparison_operator} {rule.threshold_value} (current: {current_value})"
                )
                
                # Update last triggered
                rule.last_triggered = now
                rule.save()
                
                # Send notifications (implement based on your notification system)
                self._send_alert_notification(rule, current_value)
    
    def _get_metric_value(self, metric_type):
        """Get current value for a metric type"""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if metric_type == 'revenue':
            return self._calculate_revenue(today_start, now)
        elif metric_type == 'orders':
            return self._calculate_orders(today_start, now)
        elif metric_type == 'customers':
            return self._calculate_customers(today_start, now)
        else:
            return Decimal('0.00')
    
    def _evaluate_alert_condition(self, current_value, operator, threshold):
        """Evaluate if alert condition is met"""
        if operator == 'gt':
            return current_value > threshold
        elif operator == 'gte':
            return current_value >= threshold
        elif operator == 'lt':
            return current_value < threshold
        elif operator == 'lte':
            return current_value <= threshold
        elif operator == 'eq':
            return current_value == threshold
        elif operator == 'ne':
            return current_value != threshold
        return False
    
    def _send_alert_notification(self, rule, current_value):
        """Send alert notification (implement based on your notification system)"""
        # This would integrate with your notification system
        # For now, just log the alert
        print(f"ALERT: {rule.name} - {rule.metric_type} = {current_value}")


class DataExportService:
    """Service for data export functionality"""
    
    def __init__(self, tenant):
        self.tenant = tenant
    
    def export_orders(self, filters, date_range_start, date_range_end, format='csv'):
        """Export orders data"""
        orders = Order.objects.filter(
            tenant=self.tenant,
            created_at__gte=date_range_start,
            created_at__lte=date_range_end
        )
        
        # Apply filters
        if filters.get('status'):
            orders = orders.filter(status__in=filters['status'])
        if filters.get('customer_id'):
            orders = orders.filter(customer_id=filters['customer_id'])
        
        # Convert to DataFrame
        data = []
        for order in orders:
            data.append({
                'Order ID': str(order.id),
                'Order Number': order.order_number,
                'Customer': order.customer.full_name if order.customer else 'Guest',
                'Email': order.customer.email if order.customer else order.email,
                'Status': order.status,
                'Total Amount': float(order.total_amount),
                'Created At': order.created_at,
                'Updated At': order.updated_at
            })
        
        df = pd.DataFrame(data)
        
        if format == 'csv':
            return df.to_csv(index=False)
        elif format == 'excel':
            return df.to_excel(index=False)
        elif format == 'json':
            return df.to_json(orient='records', date_format='iso')
        else:
            return df.to_csv(index=False)
    
    def export_customers(self, filters, date_range_start, date_range_end, format='csv'):
        """Export customers data"""
        customers = Customer.objects.filter(
            tenant=self.tenant,
            created_at__gte=date_range_start,
            created_at__lte=date_range_end
        )
        
        # Apply filters
        if filters.get('segment'):
            customers = customers.filter(segment=filters['segment'])
        
        # Convert to DataFrame
        data = []
        for customer in customers:
            data.append({
                'Customer ID': str(customer.id),
                'Full Name': customer.full_name,
                'Email': customer.email,
                'Phone': customer.phone,
                'Date of Birth': customer.date_of_birth,
                'Gender': customer.gender,
                'Created At': customer.created_at,
                'Updated At': customer.updated_at
            })
        
        df = pd.DataFrame(data)
        
        if format == 'csv':
            return df.to_csv(index=False)
        elif format == 'excel':
            return df.to_excel(index=False)
        elif format == 'json':
            return df.to_json(orient='records', date_format='iso')
        else:
            return df.to_csv(index=False)



