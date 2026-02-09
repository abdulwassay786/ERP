from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import SoftDeleteMixin, CompanyScopedManager



class ItemGroup(SoftDeleteMixin):
    """Group/Category for products"""
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='item_groups'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyScopedManager()

    class Meta:
        ordering = ['name']
        unique_together = ['company', 'name']

    def __str__(self):
        return self.name


class Product(SoftDeleteMixin):
    """Product/Inventory model"""
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='products'
    )
    group = models.ForeignKey(
        ItemGroup,
        on_delete=models.SET_NULL,
        related_name='products',
        null=True,
        blank=True
    )
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    quantity_in_stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        help_text='Product image'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyScopedManager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sku} - {self.name}"
