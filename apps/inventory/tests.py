from django.test import TestCase, Client
from django.urls import reverse
from .models import Product, ItemGroup
from apps.core.models import Company, User

class ItemGroupTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.user = User.objects.create_user(username="testuser", password="password", company=self.company)
        self.client = Client()
        self.client.login(username="testuser", password="password")

    def test_create_item_group(self):
        """Test creating an item group"""
        url = reverse('inventory:group_create')
        data = {
            'name': 'Electronics',
            'description': 'Electronic items'
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('inventory:group_list'))
        self.assertTrue(ItemGroup.objects.filter(name='Electronics').exists())

    def test_assign_group_to_product(self):
        """Test assigning a group to a product"""
        group = ItemGroup.objects.create(company=self.company, name="Groceries")
        
        file_path = reverse('inventory:create')
        data = {
            'sku': 'APP001',
            'name': 'Apple',
            'description': 'Fresh Apple',
            'unit_price': '1.00',
            'quantity_in_stock': 100,
            'group': group.id
        }
        response = self.client.post(file_path, data)
        self.assertRedirects(response, reverse('inventory:list'))
        
        product = Product.objects.get(sku='APP001')
        self.assertEqual(product.group, group)

    def test_filter_groups_by_company(self):
        """Test that groups are filtered by company"""
        other_company = Company.objects.create(name="Other Company")
        other_group = ItemGroup.objects.create(company=other_company, name="Other Group")
        
        my_group = ItemGroup.objects.create(company=self.company, name="My Group")
        
        response = self.client.get(reverse('inventory:group_list'))
        self.assertContains(response, "My Group")
        self.assertNotContains(response, "Other Group")
