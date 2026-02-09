from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.PaymentListView.as_view(), name='list'),
    path('create/', views.PaymentCreateView.as_view(), name='create'),
    path('htmx/unpaid-invoices/', views.unpaid_invoices_hx, name='unpaid_invoices_hx'),
]
