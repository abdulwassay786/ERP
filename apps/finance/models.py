from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from decimal import Decimal


class TransactionCategory(models.Model):
    """
    Categories for organizing transactions in reports.
    Examples: Sales, Services, Materials, Salaries, Rent, etc.
    """
    CATEGORY_TYPE_CHOICES = [
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]
    
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='transaction_categories'
    )
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPE_CHOICES)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Transaction Categories"
        unique_together = [('company', 'name')]
        ordering = ['category_type', 'name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Transaction(models.Model):
    """
    Central model for ALL money movement.
    Single source of truth for financial data (Cash Flow, P&L).
    """
    
    # Transaction classification
    TRANSACTION_TYPE_CHOICES = [
        ('invoice', 'Customer Invoice'),
        ('payment_received', 'Payment Received'),
        ('purchase', 'Supplier Purchase'),
        ('payment_made', 'Payment Made'),
        ('expense', 'Expense'),
        ('adjustment', 'Adjustment'),
        ('transfer', 'Internal Transfer'),
    ]
    
    # Direction relative to company
    DIRECTION_CHOICES = [
        ('in', 'Money In'),
        ('out', 'Money Out'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),      # Expected (e.g. invoice sent, check issued)
        ('completed', 'Completed'),  # Cleared/Received
        ('cancelled', 'Cancelled'),  # Voided
    ]
    
    PARTY_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        ('internal', 'Internal'),
        ('other', 'Other'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('check', 'Check'),
        ('card', 'Card'),
        ('other', 'Other'),
    ]
    
    # Core identification
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='transactions',
        db_index=True
    )
    transaction_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique reference number (e.g. TRX-0001)"
    )
    transaction_date = models.DateField(
        db_index=True,
        help_text="Date transaction occurred or is expected"
    )
    
    # Classification
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, db_index=True)
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transactions'
    )
    
    # Amounts
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Base amount before tax"
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total amount including tax"
    )
    
    # Party information (Denormalized for performance)
    party_type = models.CharField(max_length=20, choices=PARTY_TYPE_CHOICES, null=True, blank=True)
    party_id = models.PositiveIntegerField(null=True, blank=True)
    party_name = models.CharField(max_length=255, blank=True, help_text="Snapshot of customer/supplier name")
    
    # Payment details (for completed transactions)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    bank_account = models.ForeignKey(
        'banking.BankAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_transactions'
    )
    
    # Linking and References
    # Link to source doc (Invoice, Payment, BankTransaction)
    reference_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    reference_object = GenericForeignKey('reference_type', 'reference_id')
    
    # Link to related transaction (e.g. Payment linked to Invoice)
    related_transaction = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_modifications', # e.g. payments against an invoice
        help_text="Link payment to invoice, or refund to payment"
    )
    
    # Metadata
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            # Primary query patterns
            models.Index(fields=['company', 'transaction_date']),
            models.Index(fields=['company', 'transaction_type', 'status']),
            models.Index(fields=['company', 'party_type', 'party_id']),
            models.Index(fields=['company', 'direction', 'status']),
            models.Index(fields=['company', 'category', 'transaction_date']),
            
            # For reference lookups
            models.Index(fields=['reference_type', 'reference_id']),
        ]
        
    def __str__(self):
        return f"{self.transaction_number}: {self.get_direction_display()} {self.total_amount}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total if not set
        if self.total_amount is None:
            self.total_amount = (self.amount or 0) + (self.tax_amount or 0)
        
        # Ensure party_name is populated if party_id is present but name missing
        # (Simplified logic - in real app would lookup model based on party_type)
            
        super().save(*args, **kwargs)
