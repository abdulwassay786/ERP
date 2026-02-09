from django import forms
from apps.customers.models import Customer
from apps.banking.models import BankAccount
from .models import Payment

class PaymentForm(forms.ModelForm):
    """
    Form for recording a new payment.
    Includes logic to filter invoices based on selected customer (via HTMX).
    """
    invoice = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="Link to Invoice (Optional)",
        help_text="Optionally link this payment to a specific invoice",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Payment
        fields = [
            'customer', 
            'invoice',
            'payment_date', 
            'amount', 
            'payment_method', 
            'reference', 
            'notes'
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'customer': forms.Select(attrs={
                'class': 'form-select',
                'hx-get': '/payments/htmx/unpaid-invoices/',
                'hx-target': '#unpaid-invoices-list',
                'hx-trigger': 'change'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, company, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.company = company
        self.fields['customer'].queryset = Customer.objects.filter(company=company, is_deleted=False)

        
        # Invoice queryset depends on customer, but initially we just filter by company
        # Ideally this would be dynamic via JS, but for now strict scoping is enough
        from apps.invoices.models import Invoice
        self.fields['invoice'].queryset = Invoice.objects.filter(
            company=company
        ).exclude(status='paid').order_by('-date')
