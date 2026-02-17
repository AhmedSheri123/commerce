from django.db import models

# Create your models here.

class OrderModel(models.Model):
    product = models.ForeignKey('products.ProductModel', on_delete=models.CASCADE, related_name='orders')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    profit = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.product.name} x {self.total_price} for {self.user.username}"