from django.core.cache import cache
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_ratelimit.decorators import ratelimit
from functools import wraps
import time


def rate_limit_by_tenant(view_func):
    """Rate limit decorator that applies limits per tenant"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if hasattr(request, 'tenant') and request.tenant:
            # Use tenant ID as part of the cache key
            cache_key = f"rate_limit_{request.tenant.id}_{request.META.get('REMOTE_ADDR')}"
            
            # Check current request count
            current_requests = cache.get(cache_key, 0)
            max_requests = 100  # requests per minute
            
            if current_requests >= max_requests:
                return JsonResponse({
                    'error': 'Rate limit exceeded. Please try again later.'
                }, status=429)
            
            # Increment counter
            cache.set(cache_key, current_requests + 1, 60)  # 60 seconds TTL
        
        return view_func(request, *args, **kwargs)
    return wrapper


def cache_tenant_data(timeout=300):
    """Cache decorator that includes tenant in cache key"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if hasattr(request, 'tenant') and request.tenant:
                cache_key = f"tenant_{request.tenant.id}_{view_func.__name__}_{hash(str(request.GET))}"
                cached_data = cache.get(cache_key)
                
                if cached_data is not None:
                    return cached_data
                
                response = view_func(request, *args, **kwargs)
                cache.set(cache_key, response, timeout)
                return response
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def validate_tenant_access(view_func):
    """Validate that user has access to the tenant"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant') or not request.tenant:
            return JsonResponse({
                'error': 'Tenant not found or access denied'
            }, status=403)
        
        # Additional tenant access validation can be added here
        # For example, check if user belongs to tenant
        
        return view_func(request, *args, **kwargs)
    return wrapper


class TenantRateLimitMixin:
    """Mixin to add tenant-based rate limiting to views"""
    
    @method_decorator(ratelimit(key='tenant', rate='100/m', method='GET'))
    @method_decorator(ratelimit(key='tenant', rate='50/m', method='POST'))
    @method_decorator(ratelimit(key='tenant', rate='20/m', method='PUT'))
    @method_decorator(ratelimit(key='tenant', rate='10/m', method='DELETE'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


def get_tenant_from_request(request):
    """Extract tenant from request headers or subdomain"""
    # Check for tenant ID in headers
    tenant_id = request.META.get('HTTP_X_TENANT_ID')
    if tenant_id:
        try:
            from .models import Tenant
            return Tenant.objects.get(id=tenant_id, is_active=True)
        except Tenant.DoesNotExist:
            pass
    
    # Check for API key in headers
    api_key = request.META.get('HTTP_X_API_KEY')
    if api_key:
        try:
            from .models import Tenant
            return Tenant.objects.get(api_key=api_key, is_active=True)
        except Tenant.DoesNotExist:
            pass
    
    # Check for tenant ID in query parameters
    tenant_id = request.GET.get('tenant_id')
    if tenant_id:
        try:
            from .models import Tenant
            return Tenant.objects.get(id=tenant_id, is_active=True)
        except Tenant.DoesNotExist:
            pass
    
    # Check subdomain
    host = request.META.get('HTTP_HOST', '')
    if '.' in host:
        subdomain = host.split('.')[0]
        if subdomain != 'www' and subdomain != 'api':
            try:
                from .models import Tenant
                return Tenant.objects.get(domain__icontains=subdomain, is_active=True)
            except Tenant.DoesNotExist:
                pass
    
    return None

