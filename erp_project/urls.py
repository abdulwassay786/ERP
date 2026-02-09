"""
URL configuration for erp_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from apps.core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('login/', core_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('', core_views.dashboard, name='dashboard'),
    
    # App URLs
    path('customers/', include('apps.customers.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('invoices/', include('apps.invoices.urls')),
    path('banking/', include('apps.banking.urls')),
    path('ledger/', include('apps.ledger.urls')),
    path('payments/', include('apps.payments.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
