from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    path('', views.InvoiceListView.as_view(), name='list'),
    path('<int:pk>/', views.InvoiceDetailView.as_view(), name='detail'),
    path('create/', views.InvoiceCreateView.as_view(), name='create'),
    path('<int:pk>/update/', views.InvoiceUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='delete'),
    path('record-payment/', views.RecordPaymentView.as_view(), name='record_payment'),
    path('export-pdf/', views.InvoiceListPDFView.as_view(), name='list_export_pdf'),
    path('<int:pk>/pdf/', views.InvoiceDetailPDFView.as_view(), name='pdf'),
]
