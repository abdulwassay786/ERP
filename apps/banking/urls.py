from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'banking'

urlpatterns = [
    # Bank Accounts
    path('', RedirectView.as_view(url='accounts/', permanent=False), name='index'),
    path('accounts/', views.BankAccountListView.as_view(), name='account_list'),
    path('accounts/create/', views.BankAccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/update/', views.BankAccountUpdateView.as_view(), name='account_update'),
    path('accounts/<int:pk>/delete/', views.BankAccountDeleteView.as_view(), name='account_delete'),
    
    # Bank Transactions
    path('transactions/', views.BankTransactionListView.as_view(), name='transaction_list'),
    path('transactions/create/', views.BankTransactionCreateView.as_view(), name='transaction_create'),
    path('transactions/delete/<int:pk>/', views.BankTransactionDeleteView.as_view(), name='transaction_delete'),
    path('transactions/export-pdf/', views.TransactionListPDFView.as_view(), name='transaction_export_pdf'),
]
