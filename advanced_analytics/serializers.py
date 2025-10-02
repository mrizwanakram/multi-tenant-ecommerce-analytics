from rest_framework import serializers
from .models import (
    DashboardWidget, RealTimeMetric, AnalyticsReport, 
    DataExport, AlertRule, AlertLog
)


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """Serializer for DashboardWidget model"""
    
    class Meta:
        model = DashboardWidget
        fields = [
            'id', 'name', 'description', 'widget_type', 'chart_type',
            'config', 'position_x', 'position_y', 'width', 'height',
            'data_source', 'refresh_interval', 'is_active', 'is_public',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RealTimeMetricSerializer(serializers.ModelSerializer):
    """Serializer for RealTimeMetric model"""
    
    class Meta:
        model = RealTimeMetric
        fields = [
            'id', 'metric_type', 'current_value', 'previous_value',
            'change_percentage', 'period_start', 'period_end',
            'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalyticsReportSerializer(serializers.ModelSerializer):
    """Serializer for AnalyticsReport model"""
    
    class Meta:
        model = AnalyticsReport
        fields = [
            'id', 'name', 'report_type', 'description', 'filters',
            'date_range_start', 'date_range_end', 'data', 'summary',
            'pdf_file', 'excel_file', 'status', 'created_at', 'updated_at',
            'generated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'generated_at']


class DataExportSerializer(serializers.ModelSerializer):
    """Serializer for DataExport model"""
    
    class Meta:
        model = DataExport
        fields = [
            'id', 'name', 'export_type', 'export_format', 'filters',
            'fields', 'date_range_start', 'date_range_end', 'file',
            'file_size', 'status', 'error_message', 'created_at',
            'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'file', 'file_size', 'created_at', 'updated_at', 'completed_at'
        ]


class AlertRuleSerializer(serializers.ModelSerializer):
    """Serializer for AlertRule model"""
    
    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'description', 'alert_type', 'metric_type',
            'comparison_operator', 'threshold_value', 'is_active',
            'cooldown_minutes', 'email_recipients', 'webhook_url',
            'created_at', 'updated_at', 'last_triggered'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_triggered']


class AlertLogSerializer(serializers.ModelSerializer):
    """Serializer for AlertLog model"""
    alert_rule_name = serializers.CharField(source='alert_rule.name', read_only=True)
    
    class Meta:
        model = AlertLog
        fields = [
            'id', 'alert_rule', 'alert_rule_name', 'metric_value',
            'threshold_value', 'message', 'status', 'triggered_at'
        ]
        read_only_fields = ['id', 'triggered_at']



