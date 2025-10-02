from django.contrib import admin
from .models import Tenant, TenantUser


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'domain']
    readonly_fields = ['id', 'api_key', 'created_at', 'updated_at']


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'tenant', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'tenant', 'created_at']
    search_fields = ['user__username', 'user__email', 'tenant__name']
    readonly_fields = ['created_at']