from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import SoftDeleteMixin, CompanyScopedManager


class BankAccount(SoftDeleteMixin):
    """Bank Account model"""
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='bank_accounts'
    )
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100, unique=True)
    bank_name = models.CharField(max_length=255)
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyScopedManager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.account_name} - {self.account_number}"

    def update_balance(self):
        """Recalculate balance from transactions"""
        credits = self.transactions.filter(transaction_type='credit').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        debits = self.transactions.filter(transaction_type='debit').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        self.balance = credits - debits
        self.save()


class BankTransaction(SoftDeleteMixin):
    """Bank Transaction model - manual entry only"""
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]

    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='bank_transactions'
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_date = models.DateField()
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    description = models.TextField(blank=True)
    slip_file = models.FileField(upload_to='transaction_slips/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyScopedManager()

    class Meta:
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.transaction_type.upper()} - {self.amount} on {self.transaction_date}"

    def save(self, *args, **kwargs):
        """Update bank account balance after saving"""
        super().save(*args, **kwargs)
        self.bank_account.update_balance()
