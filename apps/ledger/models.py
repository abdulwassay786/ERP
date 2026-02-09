from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from decimal import Decimal


class LedgerEntry(models.Model):
    """
    Unified ledger entry for tracking all financial transactions.
    
    This model uses a double-entry-inspired approach where:
    - DEBIT = Money owed TO us (customer invoices, supplier refunds)
    - CREDIT = Money we owe OR received (payments from customers, supplier invoices)
    
    Running balance is calculated as: previous_balance + debit - credit
    """
    
    PARTY_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
    ]
    
    ENTRY_TYPE_CHOICES = [
        ('invoice', 'Invoice'),
        ('payment', 'Payment'),
        ('purchase', 'Purchase'),
        ('adjustment', 'Adjustment'),
    ]
    
    # Core fields
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='ledger_entries',
        db_index=True
    )
    
    # Party information (customer or supplier)
    party_type = models.CharField(
        max_length=20,
        choices=PARTY_TYPE_CHOICES,
        help_text="Whether this entry is for a customer or supplier"
    )
    party_id = models.PositiveIntegerField(
        help_text="ID of the customer or supplier"
    )
    
    # Transaction details
    entry_type = models.CharField(
        max_length=20,
        choices=ENTRY_TYPE_CHOICES,
        help_text="Type of transaction"
    )
    
    debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount owed TO us (increases balance)"
    )
    
    credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount we owe OR received (decreases balance)"
    )
    
    running_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Balance after this entry (denormalized for performance)"
    )
    
    # Reference to source object (invoice, payment, etc.)
    reference_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    reference_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    reference_object = GenericForeignKey('reference_type', 'reference_id')
    
    # Metadata
    description = models.TextField(
        blank=True,
        help_text="Human-readable description of this entry"
    )
    transaction_date = models.DateField(
        help_text="Date of the transaction"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    
    class Meta:
        ordering = ['transaction_date', 'created_at']
        verbose_name_plural = "Ledger Entries"
        
        # Composite indexes for common queries
        indexes = [
            # For ledger statements and balance queries
            models.Index(
                fields=['company', 'party_type', 'party_id', 'transaction_date'],
                name='ledger_party_date_idx'
            ),
            # For filtering by entry type
            models.Index(
                fields=['company', 'party_type', 'entry_type'],
                name='ledger_type_idx'
            ),
            # For reverse lookups from source objects
            models.Index(
                fields=['reference_type', 'reference_id'],
                name='ledger_reference_idx'
            ),
        ]
        
        # Prevent duplicate entries for the same reference
        constraints = [
            models.UniqueConstraint(
                fields=['reference_type', 'reference_id', 'entry_type'],
                name='unique_reference_entry',
                condition=models.Q(reference_type__isnull=False)
            )
        ]
    
    def __str__(self):
        balance_str = f"Balance: {self.running_balance}"
        if self.debit > 0:
            return f"{self.get_party_type_display()} {self.party_id} - Debit {self.debit} ({balance_str})"
        else:
            return f"{self.get_party_type_display()} {self.party_id} - Credit {self.credit} ({balance_str})"
    
    def clean(self):
        """Validate that either debit or credit is set, but not both"""
        from django.core.exceptions import ValidationError
        
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("Entry cannot have both debit and credit. Use separate entries.")
        
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("Entry must have either debit or credit amount.")
