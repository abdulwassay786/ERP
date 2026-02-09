from django.urls import path
from . import views

app_name = 'ledger'

urlpatterns = [
    path('', views.LedgerIndexView.as_view(), name='index'),
    path('customer/<int:customer_id>/', views.CustomerStatementView.as_view(), name='customer_statement'),
    path('supplier/<int:supplier_id>/', views.SupplierStatementView.as_view(), name='supplier_statement'),
]
