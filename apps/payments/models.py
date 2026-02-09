from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.core.models import SoftDeleteMixin, CompanyScopedManager


class Payment(SoftDeleteMixin):
    """
    Payment model - represents a payment received from a customer.
    
    CRITICAL PRINCIPLES:
    - A payment is a separate business event from an invoice.
    - Payments create CREDIT entries in the ledger (reduce receivables).
    - Payment allocation is tracked separately via PaymentAllocation.
    - Status is derived from allocations, not stored directly.
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('cheque', 'Cheque'),
    ]
    
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='payments',
        help_text="Customer who made this payment"
    )
    
    payment_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique payment reference number"
    )
    
    payment_date = models.DateField(
        help_text="Date when payment was received"
    )
    
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Total payment amount"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    
    bank_account = models.ForeignKey(
        'banking.BankAccount',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments',
        help_text="Bank account if payment method is bank/cheque"
    )
    
    reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="External reference (cheque number, transaction ID, etc.)"
    )
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CompanyScopedManager()
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['company', 'customer', 'payment_date']),
            models.Index(fields=['payment_number']),
        ]
    
    def __str__(self):
        return f"{self.payment_number} - {self.customer} - Rs {self.amount}"

    def save(self, *args, **kwargs):
        if not self.payment_number:
            import datetime
            today = datetime.date.today()
            prefix = f"PAY-{today.strftime('%Y%m%d')}"
            
            # Find last payment number for today to increment
            last_payment = Payment.objects.filter(
                company=self.company,
                payment_number__startswith=prefix
            ).order_by('payment_number').last()
            
            if last_payment:
                # Extract sequence number
                try:
                    sequence = int(last_payment.payment_number.split('-')[-1])
                    new_sequence = sequence + 1
                except ValueError:
                    new_sequence = 1
            else:
                new_sequence = 1
                
            self.payment_number = f"{prefix}-{new_sequence:04d}"
            
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate payment data"""
        super().clean()
        
        # Removed strict bank account validation as per user request
        pass
    
    @property
    def allocated_amount(self):
        """Total amount allocated to invoices"""
        return self.allocations.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def unallocated_amount(self):
        """Amount not yet allocated to any invoice"""
        return self.amount - self.allocated_amount
    
    @property
    def is_fully_allocated(self):
        """Check if entire payment is allocated"""
        return self.unallocated_amount == Decimal('0.00')


class PaymentAllocation(models.Model):
    """
    Tracks how much of a payment is allocated to a specific invoice.
    
    CRITICAL PRINCIPLES:
    - Sum of allocations for a payment cannot exceed payment amount.
    - Allocation amount cannot exceed invoice outstanding amount.
    - Deleting an allocation must reverse ledger effects.
    """
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    
    invoice = models.ForeignKey(
        'invoices.Invoice',
        on_delete=models.PROTECT,
        related_name='payment_allocations'
    )
    
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Amount of payment allocated to this invoice"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['payment', 'invoice']),
            models.Index(fields=['invoice']),
        ]
        # Prevent duplicate allocations
        constraints = [
            models.UniqueConstraint(
                fields=['payment', 'invoice'],
                name='unique_payment_invoice_allocation'
            )
        ]
    
    def __str__(self):
        return f"{self.payment.payment_number} -> {self.invoice.invoice_number}: Rs {self.amount}"
    
    def clean(self):
        """Validate allocation"""
        super().clean()
        
        # Payment and invoice must belong to same customer
        if self.payment.customer != self.invoice.customer:
            raise ValidationError(
                "Payment and invoice must belong to the same customer"
            )
        
        # Payment and invoice must belong to same company
        if self.payment.company != self.invoice.company:
            raise ValidationError(
                "Payment and invoice must belong to the same company"
            )
        
        # Check total allocations don't exceed payment amount
        existing_allocations = PaymentAllocation.objects.filter(
            payment=self.payment
        ).exclude(pk=self.pk)
        
        total_allocated = existing_allocations.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        if total_allocated + self.amount > self.payment.amount:
            raise ValidationError(
                f"Total allocations (Rs {total_allocated + self.amount}) "
                f"cannot exceed payment amount (Rs {self.payment.amount})"
            )
        
        # Check allocation doesn't exceed invoice outstanding
        invoice_paid = self.invoice.payment_allocations.exclude(
            pk=self.pk
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        invoice_outstanding = self.invoice.total_amount - invoice_paid
        
        if self.amount > invoice_outstanding:
            raise ValidationError(
                f"Allocation amount (Rs {self.amount}) cannot exceed "
                f"invoice outstanding (Rs {invoice_outstanding})"
            )
