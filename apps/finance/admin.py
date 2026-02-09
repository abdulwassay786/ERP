from django.contrib import admin
from .models import Transaction, TransactionCategory


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'parent', 'company', 'is_active']
    list_filter = ['company', 'category_type', 'is_active']
    search_fields = ['name']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_number',
        'transaction_date',
        'type_status',
        'direction_display',
        'total_amount',
        'party_name',
        'company'
    ]
    list_filter = [
        'company',
        'transaction_type',
        'status',
        'direction',
        'transaction_date'
    ]
    search_fields = ['transaction_number', 'party_name', 'description']
    date_hierarchy = 'transaction_date'
    
    def type_status(self, obj):
        return f"{obj.get_transaction_type_display()} ({obj.get_status_display()})"
    type_status.short_description = 'Type / Status'
    
    def direction_display(self, obj):
        arrow = "🟢 IN" if obj.direction == 'in' else "🔴 OUT"
        return arrow
    direction_display.short_description = 'Direction'
    
    # Read-only fields for audit trail
    readonly_fields = ['created_at', 'updated_at', 'created_by']
