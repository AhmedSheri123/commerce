from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required
def index(request):
    # count of completed products and balance and profit and withdrawn balance
    user = request.user
    profile = user.profile
    user_progress = user.progress if hasattr(user, 'progress') else None

    completed_products = []
    all_products = []
    remaining_products = []
    total_earned = 0

    if user_progress:
        completed_products = user_progress.comleted_products or []
        all_products = user_progress.all_products or []
        remaining_products = (all_products - completed_products) if all_products else []
        total_earned = user_progress.total_earned or 0


    return render(request, 'dashboard/analysis/index.html', {
        'profile': profile,
        'user_progress': user_progress,
        'total_earned': total_earned,
        'completed_products': completed_products,
        'all_products': all_products,
        'remaining_products': remaining_products
    })