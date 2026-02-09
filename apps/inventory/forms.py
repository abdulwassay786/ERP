from django import forms
from django import forms
from .models import Product, ItemGroup


class ItemGroupForm(forms.ModelForm):
    """Form for item groups"""
    class Meta:
        model = ItemGroup
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Group Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
        }


class ProductForm(forms.ModelForm):
    """Form for creating and updating products"""
    
    class Meta:
        model = Product
        fields = ['group', 'sku', 'name', 'description', 'unit_price', 'quantity_in_stock', 'image']
        widgets = {
            'group': forms.Select(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SKU'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Unit Price', 'step': '0.01'}),
            'quantity_in_stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity'}),
        }
