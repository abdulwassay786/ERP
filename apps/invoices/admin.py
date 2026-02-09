from django.contrib import admin
from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'date', 'due_date', 'status', 'total_amount', 'company', 'is_deleted']
    list_filter = ['status', 'company', 'is_deleted', 'date']
    search_fields = ['invoice_number', 'customer__name']
    readonly_fields = ['total_amount', 'created_at', 'updated_at', 'deleted_at']
    inlines = [InvoiceItemInline]


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product', 'quantity', 'unit_price', 'line_total']
    list_filter = ['invoice__company']
    search_fields = ['invoice__invoice_number', 'product__name']
