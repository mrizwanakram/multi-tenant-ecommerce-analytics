from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from PIL import Image
import uuid
import os
from .models import Product, ProductImage


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_product_image(request, product_id):
    """Upload image for a specific product"""
    try:
        product = Product.objects.get(id=product_id, tenant=request.tenant)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if 'image' not in request.FILES:
        return Response(
            {'error': 'No image file provided'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    image_file = request.FILES['image']
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if image_file.content_type not in allowed_types:
        return Response(
            {'error': 'Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate file size (5MB max)
    if image_file.size > 5 * 1024 * 1024:
        return Response(
            {'error': 'File too large. Maximum size is 5MB'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Process image
        image = Image.open(image_file)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Resize if too large (max 2048x2048)
        max_size = (2048, 2048)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Generate unique filename
        file_extension = image_file.name.split('.')[-1].lower()
        filename = f"products/{product.id}/{uuid.uuid4()}.{file_extension}"
        
        # Save processed image
        output = ContentFile(b'', name=filename)
        image.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        # Upload to storage
        file_path = default_storage.save(filename, output)
        file_url = default_storage.url(file_path)
        
        # Create ProductImage record
        product_image = ProductImage.objects.create(
            product=product,
            image=file_path,
            alt_text=request.data.get('alt_text', ''),
            is_primary=request.data.get('is_primary', False),
            sort_order=request.data.get('sort_order', 0)
        )
        
        # If this is set as primary, unset others
        if product_image.is_primary:
            ProductImage.objects.filter(
                product=product, 
                is_primary=True
            ).exclude(id=product_image.id).update(is_primary=False)
        
        return Response({
            'id': product_image.id,
            'image_url': file_url,
            'alt_text': product_image.alt_text,
            'is_primary': product_image.is_primary,
            'sort_order': product_image.sort_order,
            'created_at': product_image.created_at
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Error processing image: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product_image(request, product_id, image_id):
    """Delete a product image"""
    try:
        product = Product.objects.get(id=product_id, tenant=request.tenant)
        product_image = ProductImage.objects.get(id=image_id, product=product)
    except (Product.DoesNotExist, ProductImage.DoesNotExist):
        return Response(
            {'error': 'Product or image not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Delete file from storage
    if product_image.image:
        default_storage.delete(product_image.image.name)
    
    # Delete database record
    product_image.delete()
    
    return Response(
        {'message': 'Image deleted successfully'}, 
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_primary_image(request, product_id, image_id):
    """Set an image as primary for a product"""
    try:
        product = Product.objects.get(id=product_id, tenant=request.tenant)
        product_image = ProductImage.objects.get(id=image_id, product=product)
    except (Product.DoesNotExist, ProductImage.DoesNotExist):
        return Response(
            {'error': 'Product or image not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Unset all other primary images for this product
    ProductImage.objects.filter(
        product=product, 
        is_primary=True
    ).update(is_primary=False)
    
    # Set this image as primary
    product_image.is_primary = True
    product_image.save()
    
    return Response(
        {'message': 'Primary image updated successfully'}, 
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_upload_images(request, product_id):
    """Upload multiple images for a product"""
    try:
        product = Product.objects.get(id=product_id, tenant=request.tenant)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if 'images' not in request.FILES:
        return Response(
            {'error': 'No images provided'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    images = request.FILES.getlist('images')
    uploaded_images = []
    errors = []
    
    for i, image_file in enumerate(images):
        try:
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                errors.append(f'Image {i+1}: Invalid file type')
                continue
            
            # Validate file size
            if image_file.size > 5 * 1024 * 1024:
                errors.append(f'Image {i+1}: File too large')
                continue
            
            # Process and save image (similar to single upload)
            image = Image.open(image_file)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            max_size = (2048, 2048)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            file_extension = image_file.name.split('.')[-1].lower()
            filename = f"products/{product.id}/{uuid.uuid4()}.{file_extension}"
            
            output = ContentFile(b'', name=filename)
            image.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            file_path = default_storage.save(filename, output)
            file_url = default_storage.url(file_path)
            
            # Create ProductImage record
            product_image = ProductImage.objects.create(
                product=product,
                image=file_path,
                alt_text=f"Product image {i+1}",
                is_primary=(i == 0),  # First image is primary
                sort_order=i
            )
            
            uploaded_images.append({
                'id': product_image.id,
                'image_url': file_url,
                'alt_text': product_image.alt_text,
                'is_primary': product_image.is_primary,
                'sort_order': product_image.sort_order
            })
            
        except Exception as e:
            errors.append(f'Image {i+1}: {str(e)}')
    
    return Response({
        'uploaded_images': uploaded_images,
        'errors': errors,
        'success_count': len(uploaded_images),
        'error_count': len(errors)
    }, status=status.HTTP_200_OK)



