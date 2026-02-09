from django import forms
from .models import BankAccount, BankTransaction


class BankAccountForm(forms.ModelForm):
    """Form for creating and updating bank accounts"""
    
    class Meta:
        model = BankAccount
        fields = ['account_name', 'account_number', 'bank_name']
        widgets = {
            'account_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account Name'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account Number'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank Name'}),
        }


class BankTransactionForm(forms.ModelForm):
    """Form for creating bank transactions"""
    
    class Meta:
        model = BankTransaction
        fields = ['bank_account', 'transaction_date', 'transaction_type', 'amount', 'description', 'slip_file']
        widgets = {
            'bank_account': forms.Select(attrs={'class': 'form-control'}),
            'transaction_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'slip_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if self.company:
            # Filter bank account choices by company
            self.fields['bank_account'].queryset = BankAccount.objects.for_company(self.company)
