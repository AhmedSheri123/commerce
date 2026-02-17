from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    return render(request, 'home/index.html')
