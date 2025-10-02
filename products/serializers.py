from rest_framework import serializers
from .models import Category, Product, ProductImage, ProductVariant
from tenants.models import Tenant


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'parent', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for ProductImage model"""
    
    class Meta:
        model = ProductImage
        fields = [
            'id', 'image', 'alt_text', 'is_primary', 'sort_order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for ProductVariant model"""
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'name', 'sku', 'price', 'stock_quantity', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model"""
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'sku', 'price', 'cost_price',
            'category', 'category_name', 'tenant', 'tenant_name',
            'stock_quantity', 'min_stock_level', 'is_active', 'is_digital',
            'meta_title', 'meta_description', 'tags', 'created_at', 'updated_at',
            'images', 'variants'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    """Simplified serializer for product lists"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'price', 'category_name', 'stock_quantity',
            'is_active', 'primary_image', 'created_at'
        ]
    
    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return primary_image.image.url
        return None


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating products"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'sku', 'price', 'cost_price', 'category',
            'stock_quantity', 'min_stock_level', 'is_active', 'is_digital',
            'meta_title', 'meta_description', 'tags'
        ]
    
    def create(self, validated_data):
        # Add tenant from request context
        validated_data['tenant'] = self.context['request'].tenant
        return super().create(validated_data)



