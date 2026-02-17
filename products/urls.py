from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.products, name='products'),
    path('view_product_ajax/', views.view_product_ajax, name='view_product_ajax'),
    path('view_products_ajax/', views.view_products_ajax, name='view_products_ajax'),
    path('buy_product_ajax/', views.buy_product_ajax, name='buy_product_ajax'),
]
