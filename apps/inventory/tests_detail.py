from django.test import TestCase, Client
from django.urls import reverse
from .models import Product, ItemGroup
from apps.core.models import Company, User

class ProductDetailTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.user = User.objects.create_user(username="testuser", password="password", company=self.company)
        self.client = Client()
        self.client.login(username="testuser", password="password")
        
        self.group = ItemGroup.objects.create(company=self.company, name="Electronics")
        self.product = Product.objects.create(
            company=self.company, 
            sku="E001", 
            name="Laptop", 
            group=self.group, 
            unit_price=1000,
            description="A high-end laptop"
        )

    def test_product_detail_view(self):
        url = reverse('inventory:detail', args=[self.product.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Laptop")
        self.assertContains(response, "E001")
        self.assertContains(response, "Electronics")
        self.assertContains(response, "1000") # Unit price

    def test_product_detail_requires_login(self):
        self.client.logout()
        url = reverse('inventory:detail', args=[self.product.id])
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)
        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_cannot_view_other_company_product(self):
        other_company = Company.objects.create(name="Other Company")
        other_product = Product.objects.create(
            company=other_company,
            sku="O001",
            name="Other Product",
            unit_price=50
        )
        
        url = reverse('inventory:detail', args=[other_product.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
