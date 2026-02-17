from django.shortcuts import render

from orders.models import OrderModel
from .models import ProductModel, CategoryModel, PlatformModel, UserProgress
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import time

@login_required
def products(request):
    """Simple homepage view that renders templates/home/index.html"""
    user = request.user
    profile = user.profile
    platforms = PlatformModel.objects.filter(show_only_from_not_verified_source = not(profile.from_verified_source))
    user_progress = user.progress if hasattr(user, 'progress') else None

    is_done = user_progress.is_done if user_progress else False
    return render(request, 'dashboard/products/products.html', {'platforms': platforms, 'is_done':is_done})


@login_required
def view_product_ajax(request):
    platform_id = request.GET.get('platform_id')

    data = []

    user_progress = UserProgress.objects.filter(
        user=request.user,
        product__category__platform_id=platform_id
    ).select_related('product').first()

    if user_progress:
        product = user_progress.next_stage()            
    else:
        product = ProductModel.objects.filter(
            category__platform_id=platform_id
        ).order_by('stage').first()

    if not product:
        return JsonResponse({"data": []})

    # حساب التقدم (مؤقت)
    progress = 0
    if user_progress:
        progress = user_progress.progress_percentage()

    product_data = {
        "category": product.category.name,  # أجهزة إلكترونية
        'product_id': product.id,
        "product_name": product.name,
        "product_image_url": product.image.url if product.image else None,
        "buy_price": float(product.price),
        "sell_price": float(product.price + product.profit),
        "profit": float(product.profit),
        "progress": progress,
    }

    data.append({
        "product_type": product.category.name,
        "products_count": product.category.products.count(),
        "products": [product_data]  # ✅ list
    })

    return JsonResponse({"data": data})

@login_required
def view_products_ajax(request):
    platform_id = request.GET.get('platform_id')
    platform = PlatformModel.objects.get(id=platform_id)
    user_progress = UserProgress.objects.filter(
        user=request.user,
        product__category__platform_id=platform_id
    ).first()

    if user_progress:
        products = ProductModel.objects.filter(
            category__platform_id=platform_id,
            category=user_progress.product.category,
        ).order_by('-stage')
    else:
        products = ProductModel.objects.filter(
            category__platform_id=platform_id,
            category__stage=1
        ).order_by('-stage')

    data = {
        "platform_name": platform.name,
        "platform_image": platform.image.url if platform.image else None,
        "products_count": products.count() if products.exists() else 0,
        'product_data': []
    }
    for product in products:
        product_name = product.name
        has_gift = False

        if user_progress:
            if product.stage <= user_progress.product.stage:
                status = 'completed'
            elif product.stage == user_progress.product.stage + 1:
                status = 'current'
            else:
                product_name = "🔒"
                status = 'locked'
        else:
            if product.stage == 1:
                status = 'current'
            else:
                product_name = "🔒"
                status = 'locked'

        product_data = {
            'stage': product.stage,
            'product_name': product_name,
            'status': status,
            'has_gift': has_gift
            }
    
        data['product_data'].append(product_data)
    return JsonResponse({"data": data})

@login_required
def buy_product_ajax(request):
    time.sleep(4)  # Simulate processing time
    user = request.user
    profile = user.profile if hasattr(user, 'profile') else None
    user_progress = user.progress if hasattr(user, 'progress') else None

    # This is a placeholder for the buy product logic
    product_id = request.GET.get('product_id')
    product = ProductModel.objects.get(id=product_id)
    # Here you would implement the logic to handle the purchase, update user progress, etc.
    if not profile.is_enabled:
        return JsonResponse({"message": "حسابك غير مفعل, لا يمكنك العمل معنا", "status": "error"})
    #exchange money and update user progress
    if not profile or product.price > profile.balance:
        return JsonResponse({"message": f"رصيدك غير كافٍ. يجب عليك ايداع مبلغ وقدره ${round(product.price - profile.balance, 0)}", "status": "error"})
    
    if user_progress:
        if user_progress.product == product:
            return JsonResponse({"message": "لقد قمت بشراء هذا المنتج مسبقاً.", "status": "error"})
        if user_progress.product.category.platform != product.category.platform:
            return JsonResponse({"message": "يجب انهاء المهمة الاولى قبل البدء بمهمة جديدة.", "status": "error"})
        user_progress.product = product
        user_progress.total_earned += product.profit
    else:
        user_progress = UserProgress.objects.create(
            user=user,
            product=product,
            total_earned=product.profit
        )
    
    profile.balance += (product.profit)
    profile.save()
    user_progress.save()

    order = OrderModel.objects.create(
        product=product,
        user=user,
        total_price=product.price,
        profit=product.profit
    )

    is_done = user_progress.is_done if user_progress else False

    return JsonResponse({"message": f"لقد تم الاستثمار بالمنتج بنجاح. وكسبت مبلغ وقدره {product.profit}$", "status": "success", "is_done": is_done})