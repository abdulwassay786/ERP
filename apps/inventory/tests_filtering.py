from django.test import TestCase, Client
from django.urls import reverse
from .models import Product, ItemGroup
from apps.core.models import Company, User

class ProductFilterTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.user = User.objects.create_user(username="testuser", password="password", company=self.company)
        self.client = Client()
        self.client.login(username="testuser", password="password")
        
        self.group1 = ItemGroup.objects.create(company=self.company, name="Electronics")
        self.group2 = ItemGroup.objects.create(company=self.company, name="Groceries")
        
        self.p1 = Product.objects.create(company=self.company, sku="E001", name="Laptop", group=self.group1, unit_price=1000)
        self.p2 = Product.objects.create(company=self.company, sku="G001", name="Apple", group=self.group2, unit_price=1)
        self.p3 = Product.objects.create(company=self.company, sku="E002", name="Mouse", group=self.group1, unit_price=20)

    def test_filter_by_group(self):
        url = reverse('inventory:list')
        response = self.client.get(url, {'group': self.group1.id})
        
        self.assertContains(response, "Laptop")
        self.assertContains(response, "Mouse")
        self.assertNotContains(response, "Apple")

    def test_search_by_name(self):
        url = reverse('inventory:list')
        response = self.client.get(url, {'q': 'Lap'})
        
        self.assertContains(response, "Laptop")
        self.assertNotContains(response, "Mouse")
        self.assertNotContains(response, "Apple")

    def test_search_by_sku(self):
        url = reverse('inventory:list')
        response = self.client.get(url, {'q': 'G001'})
        
        self.assertContains(response, "Apple")
        self.assertNotContains(response, "Laptop")
