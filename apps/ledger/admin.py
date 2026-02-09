from django.contrib import admin
from .models import LedgerEntry


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    """
    Read-only admin for ledger entries.
    Entries should only be created via LedgerService to prevent corruption.
    """
    list_display = [
        'id',
        'transaction_date',
        'company',
        'party_type',
        'party_id',
        'entry_type',
        'debit',
        'credit',
        'running_balance',
        'description'
    ]
    
    list_filter = [
        'company',
        'party_type',
        'entry_type',
        'transaction_date'
    ]
    
    search_fields = [
        'description',
        'party_id'
    ]
    
    ordering = ['-transaction_date', '-created_at']
    
    readonly_fields = [
        'company',
        'party_type',
        'party_id',
        'entry_type',
        'debit',
        'credit',
        'running_balance',
        'reference_type',
        'reference_id',
        'description',
        'transaction_date',
        'created_at'
    ]
    
    # Make entries read-only to prevent manual corruption
    def has_add_permission(self, request):
        """Prevent manual entry creation - use LedgerService instead"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing - entries are immutable"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion - entries are immutable"""
        return False
