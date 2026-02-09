from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum, Q, F, Max
from decimal import Decimal
from datetime import date
from typing import Optional, List, Dict


class LedgerService:
    """
    Service layer for all ledger operations.
    
    CRITICAL: Always use this service to create ledger entries.
    Never create LedgerEntry objects directly to prevent balance corruption.
    """
    
    @staticmethod
    @transaction.atomic
    def _create_entry(
        company,
        party_type: str,
        party_id: int,
        entry_type: str,
        debit: Decimal,
        credit: Decimal,
        transaction_date: date,
        description: str,
        reference_object=None
    ):
        """
        Internal method to create a ledger entry with proper locking and balance calculation.
        
        This method:
        1. Locks the party's ledger to prevent race conditions
        2. Calculates the new running balance
        3. Creates the entry atomically
        """
        from apps.ledger.models import LedgerEntry
        
        # Get the last entry for this party with row-level lock
        last_entry = LedgerEntry.objects.select_for_update().filter(
            company=company,
            party_type=party_type,
            party_id=party_id
        ).order_by('-transaction_date', '-created_at').first()
        
        # Calculate running balance
        previous_balance = last_entry.running_balance if last_entry else Decimal('0.00')
        running_balance = previous_balance + debit - credit
        
        # Get ContentType for reference object if provided
        reference_type = None
        reference_id = None
        if reference_object:
            reference_type = ContentType.objects.get_for_model(reference_object)
            reference_id = reference_object.pk
        
        # Create the entry
        entry = LedgerEntry.objects.create(
            company=company,
            party_type=party_type,
            party_id=party_id,
            entry_type=entry_type,
            debit=debit,
            credit=credit,
            running_balance=running_balance,
            transaction_date=transaction_date,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id
        )
        
        return entry
    
    # ==================== CUSTOMER OPERATIONS ====================
    
    @staticmethod
    def create_customer_invoice_entry(company, customer, invoice):
        """
        Create ledger entry when invoice is sent to customer.
        
        Debit: Customer now owes us money
        """
        return LedgerService._create_entry(
            company=company,
            party_type='customer',
            party_id=customer.id,
            entry_type='invoice',
            debit=invoice.total_amount,
            credit=Decimal('0.00'),
            transaction_date=invoice.date,
            description=f"Invoice {invoice.invoice_number}",
            reference_object=invoice
        )
    
    @staticmethod
    def create_customer_payment_entry(company, customer, amount, payment_date, description="", reference_object=None):
        """
        Create ledger entry when customer makes a payment.
        
        Credit: Customer paid us, reducing their balance
        """
        return LedgerService._create_entry(
            company=company,
            party_type='customer',
            party_id=customer.id,
            entry_type='payment',
            debit=Decimal('0.00'),
            credit=amount,
            transaction_date=payment_date,
            description=description or f"Payment received from {customer.name}",
            reference_object=reference_object
        )
    
    # ==================== SUPPLIER OPERATIONS ====================
    
    @staticmethod
    def create_supplier_purchase_entry(company, supplier, amount, purchase_date, description="", reference_object=None):
        """
        Create ledger entry when we purchase from supplier.
        
        Credit: We now owe the supplier money
        """
        return LedgerService._create_entry(
            company=company,
            party_type='supplier',
            party_id=supplier.id,
            entry_type='purchase',
            debit=Decimal('0.00'),
            credit=amount,
            transaction_date=purchase_date,
            description=description or f"Purchase from {supplier.name}",
            reference_object=reference_object
        )
    
    @staticmethod
    def create_supplier_payment_entry(company, supplier, amount, payment_date, description="", reference_object=None):
        """
        Create ledger entry when we pay a supplier.
        
        Debit: We paid the supplier, reducing what we owe
        """
        return LedgerService._create_entry(
            company=company,
            party_type='supplier',
            party_id=supplier.id,
            entry_type='payment',
            debit=amount,
            credit=Decimal('0.00'),
            transaction_date=payment_date,
            description=description or f"Payment to {supplier.name}",
            reference_object=reference_object
        )
    
    # ==================== ADJUSTMENTS ====================
    
    @staticmethod
    def create_adjustment_entry(
        company,
        party_type: str,
        party_id: int,
        amount: Decimal,
        is_debit: bool,
        adjustment_date: date,
        description: str
    ):
        """
        Create manual adjustment entry.
        
        Use for corrections, discounts, write-offs, etc.
        """
        debit = amount if is_debit else Decimal('0.00')
        credit = Decimal('0.00') if is_debit else amount
        
        return LedgerService._create_entry(
            company=company,
            party_type=party_type,
            party_id=party_id,
            entry_type='adjustment',
            debit=debit,
            credit=credit,
            transaction_date=adjustment_date,
            description=description,
            reference_object=None
        )
    
    # ==================== QUERY METHODS ====================
    
    @staticmethod
    def get_customer_outstanding(company, customer_id: int) -> Decimal:
        """
        Get current outstanding balance for a customer.
        
        Returns the running balance from the most recent entry.
        Positive = customer owes us money
        """
        from apps.ledger.models import LedgerEntry
        
        last_entry = LedgerEntry.objects.filter(
            company=company,
            party_type='customer',
            party_id=customer_id
        ).order_by('-transaction_date', '-created_at').first()
        
        return last_entry.running_balance if last_entry else Decimal('0.00')
    
    @staticmethod
    def get_supplier_payable(company, supplier_id: int) -> Decimal:
        """
        Get current payable balance for a supplier.
        
        Returns the running balance from the most recent entry.
        Negative = we owe the supplier money
        """
        from apps.ledger.models import LedgerEntry
        
        last_entry = LedgerEntry.objects.filter(
            company=company,
            party_type='supplier',
            party_id=supplier_id
        ).order_by('-transaction_date', '-created_at').first()
        
        return last_entry.running_balance if last_entry else Decimal('0.00')
    
    @staticmethod
    def get_ledger_statement(
        company,
        party_type: str,
        party_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """
        Get ledger statement for a party within a date range.
        
        Returns list of entries with transaction details.
        """
        from apps.ledger.models import LedgerEntry
        
        queryset = LedgerEntry.objects.filter(
            company=company,
            party_type=party_type,
            party_id=party_id
        )
        
        if start_date:
            queryset = queryset.filter(transaction_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(transaction_date__lte=end_date)
        
        entries = queryset.order_by('transaction_date', 'created_at')
        
        return [{
            'date': entry.transaction_date,
            'description': entry.description,
            'entry_type': entry.get_entry_type_display(),
            'debit': entry.debit,
            'credit': entry.credit,
            'balance': entry.running_balance,
            'reference': entry.reference_object
        } for entry in entries]
    
    @staticmethod
    def get_all_outstanding_customers(company) -> List[Dict]:
        """
        Get all customers with outstanding balances.
        
        Returns list of {customer_id, customer_name, balance}
        """
        from apps.ledger.models import LedgerEntry
        from apps.customers.models import Customer
        
        # Get latest entry for each customer
        latest_entries = LedgerEntry.objects.filter(
            company=company,
            party_type='customer'
        ).values('party_id').annotate(
            latest_date=Max('transaction_date'),
            latest_created=Max('created_at')
        )
        
        results = []
        for entry_info in latest_entries:
            last_entry = LedgerEntry.objects.filter(
                company=company,
                party_type='customer',
                party_id=entry_info['party_id'],
                transaction_date=entry_info['latest_date'],
                created_at=entry_info['latest_created']
            ).first()
            
            if last_entry and last_entry.running_balance > 0:
                try:
                    customer = Customer.objects.get(id=entry_info['party_id'], company=company)
                    results.append({
                        'customer_id': customer.id,
                        'customer_name': customer.name,
                        'balance': last_entry.running_balance
                    })
                except Customer.DoesNotExist:
                    pass
        
        return sorted(results, key=lambda x: x['balance'], reverse=True)
    
    @staticmethod
    def get_all_payable_suppliers(company) -> List[Dict]:
        """
        Get all suppliers we owe money to.
        
        Returns list of {supplier_id, supplier_name, balance}
        Note: Requires a Supplier model to be created
        """
        from apps.ledger.models import LedgerEntry
        
        # Get latest entry for each supplier
        latest_entries = LedgerEntry.objects.filter(
            company=company,
            party_type='supplier'
        ).values('party_id').annotate(
            latest_date=Max('transaction_date'),
            latest_created=Max('created_at')
        )
        
        results = []
        for entry_info in latest_entries:
            last_entry = LedgerEntry.objects.filter(
                company=company,
                party_type='supplier',
                party_id=entry_info['party_id'],
                transaction_date=entry_info['latest_date'],
                created_at=entry_info['latest_created']
            ).first()
            
            if last_entry and last_entry.running_balance < 0:
                results.append({
                    'supplier_id': entry_info['party_id'],
                    'balance': abs(last_entry.running_balance)  # Show as positive
                })
        
        return sorted(results, key=lambda x: x['balance'], reverse=True)
    
    # ==================== UTILITY METHODS ====================
    
    @staticmethod
    @transaction.atomic
    def recalculate_party_balance(company, party_type: str, party_id: int):
        """
        Recalculate running balances for a party from scratch.
        
        Use this if you suspect balance corruption.
        WARNING: This locks the entire party ledger during recalculation.
        """
        from apps.ledger.models import LedgerEntry
        
        entries = LedgerEntry.objects.select_for_update().filter(
            company=company,
            party_type=party_type,
            party_id=party_id
        ).order_by('transaction_date', 'created_at')
        
        running_balance = Decimal('0.00')
        for entry in entries:
            running_balance = running_balance + entry.debit - entry.credit
            if entry.running_balance != running_balance:
                entry.running_balance = running_balance
                entry.save(update_fields=['running_balance'])
        
        return running_balance
