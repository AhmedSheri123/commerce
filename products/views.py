import time
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from orders.models import OrderModel
from .models import CategoryModel, PlatformModel, ProductGroupModel, ProductModel, UserProgress


def _get_progress_for_platform(user, platform_id):
    progress = getattr(user, "progress", None)
    if not progress or not progress.product_group:
        return None
    if progress.product_group.category.platform_id != int(platform_id):
        return None
    return progress


def _first_group(platform_id):
    return (
        ProductGroupModel.objects.filter(category__platform_id=platform_id)
        .order_by("category__stage", "stage", "id")
        .first()
    )


def _next_group(progress):
    if not progress:
        return None
    return progress.next_stage()


def _active_group(user, platform_id):
    progress = _get_progress_for_platform(user, platform_id)
    if progress:
        return _next_group(progress)
    return _first_group(platform_id)


@login_required
def products(request):
    user = request.user
    profile = user.profile
    platforms = PlatformModel.objects.filter(
        show_only_from_not_verified_source=not (profile.from_verified_source)
    )

    progress = getattr(user, "progress", None)
    is_done = False
    if progress and progress.product_group:
        is_done = _next_group(progress) is None

    return render(
        request,
        "dashboard/products/products.html",
        {"platforms": platforms, "is_done": is_done},
    )


@login_required
def view_product_ajax(request):
    platform_id = request.GET.get("platform_id")
    if not platform_id:
        return JsonResponse({"data": []})

    group = _active_group(request.user, platform_id)
    if not group:
        return JsonResponse({"data": []})

    if group.target_total_price and group.products_count:
        suggestion, suggested_total = ProductGroupModel.suggest_items_for_target(
            category=group.category,
            target_total=group.target_total_price,
            products_count=group.products_count,
        )
    else:
        random_product = ProductModel.objects.filter(category=group.category).order_by("?").first()
        suggestion = [{"product": random_product, "quantity": 1, "line_total": random_product.price}] if random_product else []
        suggested_total = suggestion[0]["line_total"] if suggestion else 0

    if not suggestion:
        return JsonResponse({"data": []})

    products = []
    total_units = sum(int(row["quantity"]) for row in suggestion)
    group_profit = Decimal(group.profit or 0)
    per_unit_profit = (group_profit / Decimal(total_units)) if total_units else Decimal("0")
    for row in suggestion:
        p = row["product"]
        qty = int(row["quantity"])
        line_profit = per_unit_profit * qty
        products.append(
            {
                "product_id": p.id,
                "product_name": p.name,
                "product_image_url": p.image.url if p.image else None,
                "buy_price": float(p.price),
                "sell_price": float(p.price + per_unit_profit),
                "profit": float(per_unit_profit),
                "quantity": qty,
                "line_total": float(row["line_total"]),
                "line_profit": float(line_profit),
            }
        )

    payload = {
        "product_type": group.category.name,
        "group_id": group.id,
        "products_count": len(products),
        "group_total": float(suggested_total),
        "group_profit": float(group_profit),
        "products": products,
    }
    return JsonResponse({"data": [payload]})


@login_required
def view_products_ajax(request):
    platform_id = request.GET.get("platform_id")
    if not platform_id:
        return JsonResponse({"data": None})

    platform = PlatformModel.objects.filter(id=platform_id).first()
    if not platform:
        return JsonResponse({"data": None})

    progress = _get_progress_for_platform(request.user, platform_id)
    active = _active_group(request.user, platform_id)

    category = None
    if active:
        category = active.category
    elif progress and progress.product_group:
        category = progress.product_group.category
    else:
        category = CategoryModel.objects.filter(platform_id=platform_id).order_by("stage", "id").first()

    groups = list(ProductGroupModel.objects.filter(category=category).order_by("-stage", "-id")) if category else []

    data = {
        "platform_name": platform.name,
        "platform_image": platform.image.url if platform.image else None,
        "products_count": len(groups),
        "product_data": [],
    }

    for group in groups:
        if active and group.id == active.id:
            status = "current"
            name = group.name or f"Group {group.stage if group.stage is not None else group.id}"
        elif progress and progress.product_group and group.category_id == progress.product_group.category_id:
            if group.stage is not None and progress.product_group.stage is not None and group.stage <= progress.product_group.stage:
                status = "completed"
                name = group.name or f"Group {group.stage}"
            else:
                status = "locked"
                name = "Locked"
        else:
            status = "locked"
            name = "Locked"

        data["product_data"].append(
            {
                "stage": group.stage if group.stage is not None else group.id,
                "product_name": name,
                "status": status,
                "has_gift": False,
            }
        )

    return JsonResponse({"data": data})


@login_required
def buy_product_ajax(request):
    time.sleep(4)
    user = request.user
    profile = getattr(user, "profile", None)
    group_id = request.GET.get("group_id")

    if not group_id:
        return JsonResponse({"message": "Missing group id.", "status": "error"})

    group = ProductGroupModel.objects.select_related("category", "category__platform").filter(id=group_id).first()
    if not group:
        return JsonResponse({"message": "Group not found.", "status": "error"})

    active = _active_group(user, group.category.platform_id)
    if not active or active.id != group.id:
        return JsonResponse({"message": "This group is not the current active group.", "status": "error"})

    if not profile or not profile.is_enabled:
        return JsonResponse({"message": "حسابك غير مفعل, لا يمكنك العمل معنا", "status": "error"})

    suggestion, suggested_total = ProductGroupModel.suggest_items_for_target(
        category=group.category,
        target_total=group.target_total_price or 0,
        products_count=group.products_count or 1,
    )
    if not suggestion:
        return JsonResponse({"message": "No products found for this group.", "status": "error"})

    if float(suggested_total) > float(profile.balance):
        return JsonResponse(
            {
                "message": f"رصيدك غير كاف. يجب عليك ايداع مبلغ وقدره ${round(float(suggested_total) - float(profile.balance), 2)}",
                "status": "error",
            }
        )

    total_units = sum(int(row["quantity"]) for row in suggestion)
    total_profit = Decimal(group.profit or 0)
    per_unit_profit = (total_profit / Decimal(total_units)) if total_units else Decimal("0")

    for row in suggestion:
        product = row["product"]
        qty = int(row["quantity"])
        for _ in range(qty):
            OrderModel.objects.create(
                product=product,
                user=user,
                total_price=product.price,
                profit=per_unit_profit,
            )

    progress = getattr(user, "progress", None)
    if progress:
        progress.product_group = group
        progress.total_earned += total_profit
        progress.save()
    else:
        progress = UserProgress.objects.create(
            user=user,
            product_group=group,
            total_earned=total_profit,
        )

    profile.balance += total_profit
    profile.save()

    is_done = progress.is_done if progress else False
    return JsonResponse(
        {
            "message": f"لقد تم الاستثمار بالمجموعة بنجاح. وكسبت مبلغ وقدره {round(total_profit, 2)}$",
            "status": "success",
            "is_done": is_done,
        }
    )
