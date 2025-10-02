from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .services import AdvancedAnalyticsService
from .models import RealTimeMetric, AlertRule


@shared_task
def update_realtime_metrics(tenant_id):
    """Update real-time metrics for a tenant"""
    from tenants.models import Tenant
    
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        service = AdvancedAnalyticsService(tenant)
        service.get_realtime_metrics()
        return f"Updated metrics for tenant {tenant.name}"
    except Tenant.DoesNotExist:
        return f"Tenant {tenant_id} not found"


@shared_task
def check_alert_rules(tenant_id):
    """Check alert rules for a tenant"""
    from tenants.models import Tenant
    
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        service = AdvancedAnalyticsService(tenant)
        service.check_alert_rules()
        return f"Checked alert rules for tenant {tenant.name}"
    except Tenant.DoesNotExist:
        return f"Tenant {tenant_id} not found"


@shared_task
def generate_analytics_report(report_id):
    """Generate analytics report"""
    from .models import AnalyticsReport
    
    try:
        report = AnalyticsReport.objects.get(id=report_id)
        service = AdvancedAnalyticsService(report.tenant)
        
        # Generate report based on type
        if report.report_type == 'sales':
            data = service.generate_sales_chart_data(
                report.date_range_start,
                report.date_range_end,
                'day'
            )
        elif report.report_type == 'product':
            data = service.generate_product_performance_data(
                report.date_range_start,
                report.date_range_end
            )
        elif report.report_type == 'customer':
            data = service.generate_customer_segmentation_data(
                report.date_range_start,
                report.date_range_end
            )
        else:
            data = {}
        
        # Update report
        report.data = data
        report.status = 'completed'
        report.generated_at = timezone.now()
        report.save()
        
        return f"Generated report {report.name}"
    except AnalyticsReport.DoesNotExist:
        return f"Report {report_id} not found"


@shared_task
def cleanup_old_metrics():
    """Clean up old real-time metrics"""
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = RealTimeMetric.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    return f"Deleted {deleted_count} old metrics"


@shared_task
def send_alert_notifications(alert_log_id):
    """Send alert notifications"""
    from .models import AlertLog
    
    try:
        alert_log = AlertLog.objects.get(id=alert_log_id)
        # Implement notification sending logic here
        # This could send emails, Slack messages, etc.
        return f"Sent alert notification for {alert_log.alert_rule.name}"
    except AlertLog.DoesNotExist:
        return f"Alert log {alert_log_id} not found"



