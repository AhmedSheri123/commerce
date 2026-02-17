from django.contrib import admin
from .models import ProductModel, CategoryModel, PlatformModel, UserProgress
# Register your models here.

admin.site.register(ProductModel)
admin.site.register(CategoryModel) 
admin.site.register(PlatformModel)
admin.site.register(UserProgress)