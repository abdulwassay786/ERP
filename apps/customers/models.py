from django.db import models
from apps.core.models import SoftDeleteMixin, CompanyScopedManager


class Customer(SoftDeleteMixin):
    """Customer model"""
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='customers'
    )
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyScopedManager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
