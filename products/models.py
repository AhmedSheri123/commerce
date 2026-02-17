from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class PlatformModel(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='platform_images/', null=True, blank=True)
    show_only_from_not_verified_source = models.BooleanField(default=False, help_text="اعرض فقط للاشخاص من مصدر غير موثوق؟")

    def __str__(self):
        return self.name
    
    def product_count(self):
        return ProductModel.objects.filter(category__platform=self).count()

class CategoryModel(models.Model):
    name = models.CharField(max_length=100)
    platform = models.ForeignKey(PlatformModel, on_delete=models.CASCADE, related_name='categories')
    stage = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)

    def __str__(self):
        return self.name

class ProductModel(models.Model):
    name = models.CharField(max_length=100)
    stage = models.IntegerField()
    category = models.ForeignKey(CategoryModel, on_delete=models.CASCADE, related_name='products')

    price = models.DecimalField(max_digits=10, decimal_places=2)
    profit = models.DecimalField(max_digits=10, decimal_places=2)
    
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    

    def __str__(self):
        return self.name
    


                
class UserProgress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='progress')
    product = models.ForeignKey(ProductModel, on_delete=models.CASCADE, related_name='user_progress')


    total_earned = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    
    def __str__(self):
        return f"{self.user.username} - Stage {self.product.stage} - Earned {self.total_earned}"
    
    def next_stage(self):
        next_stage_products = ProductModel.objects.filter(
            category=self.product.category,
            stage=self.product.stage + 1
        )
        if not next_stage_products.exists():
            categorys = CategoryModel.objects.filter(stage=self.product.category.stage + 1, platform=self.product.category.platform)
            
            if categorys.exists():
                next_stage_products = ProductModel.objects.filter(
                    category=categorys.order_by('?').first(),
                    stage=1
                )
        return next_stage_products.order_by('?').first() if next_stage_products.exists() else None
    
    @property
    def comleted_products(self):
        total_stages = ProductModel.objects.filter(category=self.product.category, stage__lte=self.product.stage).count()
        return total_stages
    @property
    def all_products(self):
        all_stages = ProductModel.objects.filter(category=self.product.category).count()
        return all_stages
    
    @property
    def is_done(self):
        return self.all_products == self.comleted_products
    
    def progress_percentage(self):
        total_stages = self.comleted_products
        if total_stages == 0:
            return 0
        all_stages = self.all_products
        if all_stages == 0:
            return 0
        return round((total_stages / all_stages) * 100, 0)