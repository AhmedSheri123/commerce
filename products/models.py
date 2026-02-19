from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
import random
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
    category = models.ForeignKey(CategoryModel, on_delete=models.CASCADE, related_name='products')

    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    

    def __str__(self):
        return self.name


class ProductGroupModel(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    target_total_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    products_count = models.PositiveIntegerField(default=1)
    category = models.ForeignKey(
        CategoryModel,
        on_delete=models.CASCADE,
        related_name='product_groups',
        null=True,
        blank=True,
    )
    stage = models.IntegerField(null=True)
    profit = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @classmethod
    def suggest_items_for_target(cls, category, target_total, products_count):
        """
        Return suggested products and quantities close to target total price.
        The result shape:
        [
            {"product": ProductModel, "quantity": int, "line_total": Decimal},
            ...
        ], total_sum
        """
        if not category or products_count < 1:
            return [], Decimal("0")

        products = list(
            ProductModel.objects.filter(category=category, price__gt=0).order_by("price", "id")
        )
        if not products:
            return [], Decimal("0")

        target_total = Decimal(str(target_total))
        products_count = min(products_count, len(products))
        avg_target = target_total / Decimal(products_count)

        # Start from a near-optimal pool, then randomize selection so results vary each time.
        sorted_by_distance = sorted(products, key=lambda p: abs(p.price - avg_target))
        pool_size = min(len(sorted_by_distance), max(products_count * 3, products_count))
        candidate_pool = sorted_by_distance[:pool_size]
        selected = random.sample(candidate_pool, products_count)
        suggestion = [{"product": p, "quantity": 1} for p in selected]

        def calc_total(items):
            total = Decimal("0")
            for row in items:
                total += row["product"].price * row["quantity"]
            return total

        current_total = calc_total(suggestion)
        max_steps = 300
        steps = 0

        # Increase quantities greedily to get closer to target.
        while current_total < target_total and steps < max_steps:
            steps += 1
            ranked_choices = []

            for idx, row in enumerate(suggestion):
                candidate_total = current_total + row["product"].price
                candidate_diff = abs(target_total - candidate_total)
                ranked_choices.append((candidate_diff, idx))

            if not ranked_choices:
                break

            ranked_choices.sort(key=lambda x: x[0])
            top_k = min(3, len(ranked_choices))
            _, best_idx = random.choice(ranked_choices[:top_k])
            best_diff = ranked_choices[0][0]

            current_diff = abs(target_total - current_total)
            if best_diff is not None and best_diff >= current_diff:
                break

            suggestion[best_idx]["quantity"] += 1
            current_total = calc_total(suggestion)

        random.shuffle(suggestion)
        for row in suggestion:
            row["line_total"] = row["product"].price * row["quantity"]

        return suggestion, current_total

                
class UserProgress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='progress')
    product_group = models.ForeignKey(ProductGroupModel, on_delete=models.CASCADE, related_name='user_progress', null=True)


    total_earned = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    
    def __str__(self):
        return f"{self.user.username} - Stage {self.product_group} - Earned {self.total_earned}"
    
    def next_stage(self):
        if not self.product_group:
            return None

        current = self.product_group
        same_category = ProductGroupModel.objects.filter(category=current.category)
        if current.stage is not None:
            next_group = same_category.filter(stage__gt=current.stage).order_by("stage", "id").first()
        else:
            next_group = same_category.filter(id__gt=current.id).order_by("id").first()
        if next_group:
            return next_group

        next_category = CategoryModel.objects.filter(
            platform=current.category.platform,
            stage__gt=current.category.stage,
        ).order_by("stage", "id").first()
        if not next_category:
            return None

        return ProductGroupModel.objects.filter(category=next_category).order_by("stage", "id").first()
        
    @property
    def comleted_products(self):
        if not self.product_group:
            return 0
        if self.product_group.stage is not None:
            return ProductGroupModel.objects.filter(
                category=self.product_group.category,
                stage__lte=self.product_group.stage,
            ).count()
        return ProductGroupModel.objects.filter(
            category=self.product_group.category,
            id__lte=self.product_group.id,
        ).count()
    @property
    def all_products(self):
        if not self.product_group:
            return 0
        return ProductGroupModel.objects.filter(category=self.product_group.category).count()
    
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
