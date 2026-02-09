from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem


class InvoiceForm(forms.ModelForm):
    """Form for creating and updating invoices"""
    
    class Meta:
        model = Invoice
        fields = ['invoice_number', 'customer', 'date', 'due_date', 'status', 'notes']
        widgets = {
            'invoice_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Invoice Number'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes'}),
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if self.company:
            # Filter customer choices by company
            from apps.customers.models import Customer
            self.fields['customer'].queryset = Customer.objects.for_company(self.company)


class InvoiceItemForm(forms.ModelForm):
    """Form for invoice items"""
    
    class Meta:
        model = InvoiceItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Qty'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if self.company:
            # Filter product choices by company
            from apps.inventory.models import Product
            self.fields['product'].queryset = Product.objects.for_company(self.company)


# Formset for invoice items
InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=2,
    can_delete=True,
    min_num=1,
    validate_min=True
)
