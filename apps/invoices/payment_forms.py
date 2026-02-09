from django import forms
from decimal import Decimal
from apps.invoices.models import Invoice


class RecordPaymentForm(forms.Form):
    """Form for recording customer payments against invoices"""
    
    invoice = forms.ModelChoiceField(
        queryset=Invoice.objects.none(),
        label="Invoice",
        help_text="Select the invoice to record payment for"
    )
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        label="Payment Amount",
        help_text="Enter the amount received from customer"
    )
    
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Payment Date"
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Notes",
        help_text="Optional notes about this payment"
    )
    
    def __init__(self, company, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show unpaid invoices for this company
        self.fields['invoice'].queryset = Invoice.objects.filter(
            company=company,
            status__in=['sent', 'overdue'],
            is_deleted=False
        ).select_related('customer')
        
        # Set default date to today
        from datetime import date
        if not self.initial.get('payment_date'):
            self.initial['payment_date'] = date.today()
    
    def clean(self):
        cleaned_data = super().clean()
        invoice = cleaned_data.get('invoice')
        amount = cleaned_data.get('amount')
        
        if invoice and amount:
            # Check if payment amount exceeds invoice total
            if amount > invoice.total_amount:
                raise forms.ValidationError(
                    f"Payment amount ({amount}) cannot exceed invoice total ({invoice.total_amount})"
                )
        
        return cleaned_data
