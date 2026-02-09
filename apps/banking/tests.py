from django.test import TestCase, Client
from django.urls import reverse
from .models import BankAccount
from apps.core.models import Company, User
from django.db import IntegrityError

class BankAccountTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.user = User.objects.create_user(username="testuser", password="password", company=self.company)
        self.client = Client()
        self.client.login(username="testuser", password="password")

    def test_create_bank_account_redirect(self):
        """Test that creating a bank account redirects to the list."""
        url = reverse('banking:account_create')
        data = {
            'account_name': 'Main Account',
            'account_number': '1234567890',
            'bank_name': 'Test Bank',
            'balance': '1000.00',
        }
        response = self.client.post(url, data)
        # Should redirect
        self.assertRedirects(response, reverse('banking:account_list'))
        
        # Check it was created
        self.assertTrue(BankAccount.objects.filter(account_number='1234567890').exists())

    def test_create_bank_account_htmx_redirect(self):
        """Test that creating a bank account via HTMX returns HX-Location."""
        url = reverse('banking:account_create')
        data = {
            'account_name': 'HTMX Account',
            'account_number': '0987654321',
            'bank_name': 'HTML Bank',
            'balance': '500.00',
        }
        headers = {'HTTP_HX-Request': 'true'}
        response = self.client.post(url, data, **headers)
        
        # Should be 204 No Content
        self.assertEqual(response.status_code, 204)
        # Should have HX-Location header
        self.assertEqual(response['HX-Location'], reverse('banking:account_list'))
        
        # Check it was created
        self.assertTrue(BankAccount.objects.filter(account_number='0987654321').exists())

    def test_unique_account_number(self):
        """Test that account numbers must be unique."""
        BankAccount.objects.create(
            company=self.company,
            account_name="Existing Account",
            account_number="UNIQUE123",
            bank_name="Bank A",
            balance=100
        )
        
        # Try to create another with same number using ORM
        with self.assertRaises(IntegrityError):
            BankAccount.objects.create(
                company=self.company,
                account_name="Duplicate Account",
                account_number="UNIQUE123",
                bank_name="Bank B",
                balance=200
            )

    def test_create_duplicate_via_view(self):
        """Test that the view handles duplicates gracefully (form validation)."""
        BankAccount.objects.create(
            company=self.company,
            account_name="Existing Account",
            account_number="DUP123",
            bank_name="Bank A",
            balance=100
        )
        
        url = reverse('banking:account_create')
        data = {
            'account_name': 'Duplicate Attempt',
            'account_number': 'DUP123',
            'bank_name': 'Bank B',
            'balance': '100.00',
        }
        response = self.client.post(url, data)
        # Should be 200 (re-render form with errors)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'account_number', 'Bank account with this Account number already exists.')
