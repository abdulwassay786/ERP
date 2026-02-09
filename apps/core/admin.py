from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Company, User


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'tax_id', 'phone', 'email', 'created_at']
    search_fields = ['name', 'tax_id', 'email']
    list_filter = ['created_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'company', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'company']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Company Information', {'fields': ('company', 'phone')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Company Information', {'fields': ('company', 'phone')}),
    )
