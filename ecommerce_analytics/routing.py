from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/analytics/(?P<tenant_id>[0-9a-f-]+)/$', consumers.AnalyticsConsumer.as_asgi()),
]



