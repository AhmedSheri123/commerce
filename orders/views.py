from django.shortcuts import render
from .models import OrderModel
from django.utils import timezone
from django.contrib.auth.decorators import login_required
# Create your views here.

@login_required
def index(request):
    """Simple homepage view that renders templates/home/index.html"""
    user = request.user
    filter_by_day = request.GET.get('filter-by-day', 7)
    orders = OrderModel.objects.filter(created_at__gte=timezone.now() - timezone.timedelta(days=int(filter_by_day)), user=user)
    return render(request, 'dashboard/orders/index.html', {'orders': orders, 'filter_by_day': filter_by_day})