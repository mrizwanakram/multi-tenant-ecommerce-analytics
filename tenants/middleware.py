from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .models import Tenant
import re


class TenantMiddleware(MiddlewareMixin):
    """Middleware to identify tenant from request"""
    
    def process_request(self, request):
        tenant = None
        
        # 1. Check for tenant_id in headers
        tenant_id = request.headers.get('X-Tenant-ID')
        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id, is_active=True)
            except Tenant.DoesNotExist:
                pass
        
        # 2. Check for tenant domain in subdomain
        if not tenant:
            host = request.get_host()
            if '.' in host:
                subdomain = host.split('.')[0]
                if subdomain not in ['www', 'api', 'admin']:
                    try:
                        tenant = Tenant.objects.get(domain=subdomain, is_active=True)
                    except Tenant.DoesNotExist:
                        pass
        
        # 3. Check for tenant_id in query parameters
        if not tenant:
            tenant_id = request.GET.get('tenant_id')
            if tenant_id:
                try:
                    tenant = Tenant.objects.get(id=tenant_id, is_active=True)
                except Tenant.DoesNotExist:
                    pass
        
        # 4. Check for tenant_id in API key
        if not tenant:
            api_key = request.headers.get('X-API-Key')
            if api_key:
                try:
                    tenant = Tenant.objects.get(api_key=api_key, is_active=True)
                except Tenant.DoesNotExist:
                    pass
        
        # Add tenant to request
        request.tenant = tenant
        
        # Validate tenant for protected endpoints
        if not tenant and self._is_protected_endpoint(request.path):
            return JsonResponse({
                'error': 'Tenant not found or inactive',
                'detail': 'Please provide a valid tenant identifier'
            }, status=400)
        
        return None
    
    def _is_protected_endpoint(self, path):
        """Check if the endpoint requires tenant authentication"""
        protected_patterns = [
            r'^/api/',
        ]
        
        for pattern in protected_patterns:
            if re.match(pattern, path):
                return True
        return False

