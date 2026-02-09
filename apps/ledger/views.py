from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import CompanyRequiredMixin
from apps.customers.models import Customer
# from apps.suppliers.models import Supplier # Supplier model not yet created in the codebase context
from .services import LedgerService
from datetime import date, timedelta

class CustomerStatementView(CompanyRequiredMixin, TemplateView):
    template_name = 'ledger/customer_statement.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.request.company
        customer_id = kwargs.get('customer_id')
        customer = get_object_or_404(Customer, id=customer_id, company=company)
        
        # Default to last 30 days if not specified
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str:
            start_date = date.fromisoformat(start_date_str)
        else:
            start_date = date.today().replace(day=1) # Start of current month
            
        if end_date_str:
            end_date = date.fromisoformat(end_date_str)
        else:
            end_date = date.today()
            
        statement = LedgerService.get_ledger_statement(
            company=company,
            party_type='customer',
            party_id=customer.id,
            start_date=start_date,
            end_date=end_date
        )
        
        context.update({
            'customer': customer,
            'statement': statement,
            'start_date': start_date,
            'end_date': end_date,
            'current_balance': LedgerService.get_customer_outstanding(company, customer.id)
        })
        return context

class LedgerIndexView(CompanyRequiredMixin, TemplateView):
    template_name = 'ledger/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.request.company
        
        # Get all customers who have ledger entries (regardless of balance)
        from apps.ledger.models import LedgerEntry
        from apps.customers.models import Customer
        
        # Find all unique customer IDs that have ledger entries
        # Use set() to ensure uniqueness
        customer_ids_with_entries = set(
            LedgerEntry.objects.filter(
                company=company,
                party_type='customer'
            ).values_list('party_id', flat=True)
        )
        
        # Get customer details and their current balances
        customers = []
        for customer_id in customer_ids_with_entries:
            try:
                customer = Customer.objects.get(id=customer_id, company=company)
                balance = LedgerService.get_customer_outstanding(company, customer_id)
                customers.append({
                    'customer_id': customer.id,
                    'customer_name': customer.name,
                    'balance': balance
                })
            except Customer.DoesNotExist:
                pass
        
        # Sort by balance (highest first), then by name
        customers.sort(key=lambda x: (-x['balance'], x['customer_name']))
        
        # Get all suppliers with balances
        suppliers = LedgerService.get_all_payable_suppliers(company)
        
        context.update({
            'customers': customers,
            'suppliers': suppliers,
        })
        return context

class SupplierStatementView(CompanyRequiredMixin, TemplateView):
    template_name = 'ledger/supplier_statement.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Placeholder implementation until Supplier model exists
        # company = self.request.company
        # supplier_id = kwargs.get('supplier_id')
        # supplier = get_object_or_404(Supplier, id=supplier_id, company=company)
        
        context.update({
            'error': "Supplier module implementation pending"
        })
        return context
