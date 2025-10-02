from rest_framework import serializers
from .models import Tenant, TenantUser
from django.contrib.auth.models import User


class TenantSerializer(serializers.ModelSerializer):
    """Serializer for Tenant model"""
    
    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'domain', 'api_key', 'is_active',
            'timezone', 'currency', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'api_key', 'created_at', 'updated_at']


class TenantUserSerializer(serializers.ModelSerializer):
    """Serializer for TenantUser model"""
    user = serializers.StringRelatedField(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = TenantUser
        fields = [
            'id', 'user', 'username', 'email', 'tenant', 'role',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CreateTenantUserSerializer(serializers.ModelSerializer):
    """Serializer for creating new tenant users"""
    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = TenantUser
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'is_active'
        ]
    
    def create(self, validated_data):
        # Extract user data
        user_data = {
            'username': validated_data.pop('username'),
            'email': validated_data.pop('email'),
            'password': validated_data.pop('password'),
            'first_name': validated_data.pop('first_name', ''),
            'last_name': validated_data.pop('last_name', ''),
        }
        
        # Create user
        user = User.objects.create_user(**user_data)
        
        # Create tenant user
        tenant_user = TenantUser.objects.create(
            user=user,
            tenant=validated_data.get('tenant'),
            role=validated_data.get('role', 'viewer'),
            is_active=validated_data.get('is_active', True)
        )
        
        return tenant_user

