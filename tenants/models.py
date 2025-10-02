from django.db import models
from django.contrib.auth.models import User
import uuid


class Tenant(models.Model):
    """Multi-tenant model for ecommerce analytics"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    domain = models.CharField(max_length=100, unique=True)
    api_key = models.CharField(max_length=255, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Tenant-specific settings
    timezone = models.CharField(max_length=50, default='UTC')
    currency = models.CharField(max_length=3, default='USD')
    
    class Meta:
        db_table = 'tenants'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = str(uuid.uuid4())
        super().save(*args, **kwargs)


class TenantUser(models.Model):
    """Extended user model for tenant-specific user data"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='users')
    role = models.CharField(max_length=50, choices=[
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('analyst', 'Analyst'),
        ('viewer', 'Viewer'),
    ], default='viewer')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tenant_users'
        unique_together = ['user', 'tenant']
    
    def __str__(self):
        return f"{self.user.username} - {self.tenant.name}"