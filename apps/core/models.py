from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Company(models.Model):
    """Company model for multi-tenancy"""
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Custom User model with company relationship"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True
    )
    phone = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.username} ({self.company})"


class SoftDeleteMixin(models.Model):
    """Mixin for soft delete functionality"""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Soft delete the object"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore a soft-deleted object"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class CompanyScopedManager(models.Manager):
    """Manager that filters by company automatically"""
    
    def get_queryset(self):
        """Override to exclude soft-deleted records by default"""
        return super().get_queryset().filter(is_deleted=False)

    def for_company(self, company):
        """Filter queryset by company"""
        return self.get_queryset().filter(company=company)

    def all_with_deleted(self):
        """Get all records including soft-deleted ones"""
        return super().get_queryset()
