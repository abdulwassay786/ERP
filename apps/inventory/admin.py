from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'unit_price', 'quantity_in_stock', 'company', 'created_at', 'is_deleted']
    list_filter = ['company', 'is_deleted', 'created_at']
    search_fields = ['sku', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']
