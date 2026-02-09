from django.contrib import admin
from .models import BankAccount, BankTransaction


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['account_name', 'account_number', 'bank_name', 'balance', 'company', 'is_deleted']
    list_filter = ['company', 'is_deleted', 'created_at']
    search_fields = ['account_name', 'account_number', 'bank_name']
    readonly_fields = ['balance', 'created_at', 'updated_at', 'deleted_at']


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ['bank_account', 'transaction_date', 'transaction_type', 'amount', 'company', 'is_deleted']
    list_filter = ['transaction_type', 'company', 'is_deleted', 'transaction_date']
    search_fields = ['description', 'bank_account__account_name']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']
