from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from .models import Transaction, TransactionCategory
from decimal import Decimal
import uuid

class TransactionService:
    """
    Service layer for central transaction management.
    Ensures all money movement is recorded consistently.
    """
    
    @staticmethod
    def generate_transaction_number(prefix='TRX'):
        """Generate a unique transaction number"""
        timestamp = timezone.now().strftime('%Y%m%d')
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"{prefix}-{timestamp}-{unique_id}"

    @staticmethod
    @transaction.atomic
    def create_transaction(
        company,
        transaction_type,
        direction,
        amount,
        transaction_date,
        party_type=None,
        party_id=None,
        party_name="",
        status='pending',
        category=None,
        description="",
        reference_object=None,
        user=None
    ):
        """
        Core method to create any financial transaction.
        """
        
        # Auto-determine party name if ID provided but name missing
        # (Simplified implementation)
        if party_id and not party_name:
            if party_type == 'customer':
                from apps.customers.models import Customer
                try:
                    ctx = Customer.objects.get(id=party_id)
                    party_name = ctx.name
                except:
                    pass
        
        trx = Transaction(
            company=company,
            transaction_number=TransactionService.generate_transaction_number(),
            transaction_date=transaction_date,
            transaction_type=transaction_type,
            direction=direction,
            status=status,
            amount=amount,
            total_amount=amount, # Assuming no tax for now
            party_type=party_type,
            party_id=party_id,
            party_name=party_name,
            category=category,
            description=description,
            created_by=user
        )
        
        if reference_object:
            trx.reference_object = reference_object
            
        trx.save()
        return trx
    
    @staticmethod
    def record_invoice(invoice):
        """
        Record a customer invoice as a pending 'Money In' transaction.
        """
        # Find or create 'Sales' category
        category, _ = TransactionCategory.objects.get_or_create(
            company=invoice.company,
            name="Sales",
            defaults={'category_type': 'revenue'}
        )
        
        return TransactionService.create_transaction(
            company=invoice.company,
            transaction_type='invoice',
            direction='in',
            amount=invoice.total_amount,
            transaction_date=invoice.date,
            party_type='customer',
            party_id=invoice.customer.id,
            party_name=invoice.customer.name,
            status='pending',
            category=category,
            description=f"Invoice #{invoice.invoice_number}",
            reference_object=invoice
        )
        
    @staticmethod
    def record_payment_received(payment_obj, invoice_transaction=None):
        """
        Record a payment received from customer.
        Links to the original invoice transaction if provided.
        """
        # Payment object structure depends on banking app implementation
        # Assuming standard fields based on context
        
        trx = TransactionService.create_transaction(
            company=payment_obj.company,
            transaction_type='payment_received',
            direction='in',
            amount=payment_obj.amount,
            transaction_date=payment_obj.date,
            party_type='customer',
            party_id=payment_obj.customer.id, # Assuming payment has customer
            party_name=payment_obj.customer.name,
            status='completed',
            description=f"Payment for {invoice_transaction.transaction_number if invoice_transaction else 'Unknown'}",
            reference_object=payment_obj
        )
        
        if invoice_transaction:
            trx.related_transaction = invoice_transaction
            trx.save()
            
            # Here we could auto-update invoice status if full payment
            # But avoiding side effects for now
            
        return trx

    @staticmethod
    def get_financial_summary(company, start_date=None, end_date=None):
        """
        Get aggregated financial metrics for dashboard.
        """
        queryset = Transaction.objects.filter(company=company)
        
        if start_date:
            queryset = queryset.filter(transaction_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(transaction_date__lte=end_date)
            
        # Revenue: Completed Money In
        revenue = queryset.filter(
            direction='in', 
            status='completed'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        
        # Expenses: Completed Money Out
        expenses = queryset.filter(
            direction='out', 
            status='completed'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        
        # Outstanding Receivables: Pending Money In
        receivables = queryset.filter(
            direction='in', 
            status='pending'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        
        return {
            'revenue': revenue,
            'expenses': expenses,
            'net_profit': revenue - expenses,
            'outstanding_receivables': receivables
        }
