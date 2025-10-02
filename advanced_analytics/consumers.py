import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .services import AdvancedAnalyticsService
from .models import RealTimeMetric


class AnalyticsConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time analytics updates"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.tenant_id = self.scope['url_route']['kwargs']['tenant_id']
        self.room_group_name = f'analytics_{self.tenant_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial data
        await self.send_initial_data()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle received WebSocket message"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'subscribe_metrics':
                await self.handle_subscribe_metrics(data)
            elif message_type == 'request_chart_data':
                await self.handle_request_chart_data(data)
            elif message_type == 'request_widget_data':
                await self.handle_request_widget_data(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Unknown message type'
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def send_initial_data(self):
        """Send initial analytics data"""
        try:
            tenant = await self.get_tenant()
            if tenant:
                service = AdvancedAnalyticsService(tenant)
                metrics = await database_sync_to_async(service.get_realtime_metrics)()
                
                await self.send(text_data=json.dumps({
                    'type': 'initial_data',
                    'metrics': metrics
                }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error loading initial data: {str(e)}'
            }))
    
    async def handle_subscribe_metrics(self, data):
        """Handle metric subscription request"""
        metric_types = data.get('metric_types', ['revenue', 'orders', 'customers'])
        
        try:
            tenant = await self.get_tenant()
            if tenant:
                service = AdvancedAnalyticsService(tenant)
                metrics = await database_sync_to_async(service.get_realtime_metrics)(metric_types)
                
                await self.send(text_data=json.dumps({
                    'type': 'metrics_update',
                    'metrics': metrics
                }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error getting metrics: {str(e)}'
            }))
    
    async def handle_request_chart_data(self, data):
        """Handle chart data request"""
        chart_type = data.get('chart_type', 'sales')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        group_by = data.get('group_by', 'day')
        
        try:
            tenant = await self.get_tenant()
            if tenant:
                service = AdvancedAnalyticsService(tenant)
                
                if chart_type == 'sales':
                    chart_data = await database_sync_to_async(service.generate_sales_chart_data)(
                        start_date, end_date, group_by
                    )
                elif chart_type == 'products':
                    chart_data = await database_sync_to_async(service.generate_product_performance_data)(
                        start_date, end_date
                    )
                elif chart_type == 'customers':
                    chart_data = await database_sync_to_async(service.generate_customer_segmentation_data)(
                        start_date, end_date
                    )
                else:
                    chart_data = {}
                
                await self.send(text_data=json.dumps({
                    'type': 'chart_data',
                    'chart_type': chart_type,
                    'data': chart_data
                }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error generating chart data: {str(e)}'
            }))
    
    async def handle_request_widget_data(self, data):
        """Handle widget data request"""
        widget_id = data.get('widget_id')
        
        try:
            tenant = await self.get_tenant()
            if tenant:
                # Get widget configuration
                widget = await self.get_widget(widget_id)
                if widget:
                    service = AdvancedAnalyticsService(tenant)
                    
                    # Generate data based on widget configuration
                    if widget.data_source == 'realtime_metrics':
                        metrics = await database_sync_to_async(service.get_realtime_metrics)()
                        widget_data = metrics
                    elif widget.data_source == 'sales_chart':
                        chart_data = await database_sync_to_async(service.generate_sales_chart_data)(
                            widget.config.get('start_date'),
                            widget.config.get('end_date'),
                            widget.config.get('group_by', 'day')
                        )
                        widget_data = chart_data
                    else:
                        widget_data = {}
                    
                    await self.send(text_data=json.dumps({
                        'type': 'widget_data',
                        'widget_id': widget_id,
                        'data': widget_data
                    }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error generating widget data: {str(e)}'
            }))
    
    async def metrics_update(self, event):
        """Handle metrics update message"""
        await self.send(text_data=json.dumps({
            'type': 'metrics_update',
            'metrics': event['metrics']
        }))
    
    async def chart_update(self, event):
        """Handle chart update message"""
        await self.send(text_data=json.dumps({
            'type': 'chart_update',
            'chart_type': event['chart_type'],
            'data': event['data']
        }))
    
    async def widget_update(self, event):
        """Handle widget update message"""
        await self.send(text_data=json.dumps({
            'type': 'widget_update',
            'widget_id': event['widget_id'],
            'data': event['data']
        }))
    
    @database_sync_to_async
    def get_tenant(self):
        """Get tenant by ID"""
        from tenants.models import Tenant
        try:
            return Tenant.objects.get(id=self.tenant_id)
        except Tenant.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_widget(self, widget_id):
        """Get widget by ID"""
        try:
            return DashboardWidget.objects.get(id=widget_id, tenant_id=self.tenant_id)
        except DashboardWidget.DoesNotExist:
            return None



