from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category, StockItem, StockTransaction


class InventoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="manager", password="strong-password-123")
        self.category = Category.objects.create(name="Beverages")
        self.item = StockItem.objects.create(
            name="Mint Tea",
            sku="TEA-001",
            category=self.category,
            quantity=8,
            reorder_level=10,
            unit_cost="2.50",
        )

    def test_low_stock_and_value_properties(self):
        self.assertTrue(self.item.is_low_stock)
        self.assertEqual(self.item.stock_value, 20)

    def test_stock_list_requires_login(self):
        response = self.client.get(reverse("view_stock"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_stock_search_returns_matching_item(self):
        self.client.login(username="manager", password="strong-password-123")
        response = self.client.get(reverse("view_stock"), {"q": "mint"})
        self.assertContains(response, "Mint Tea")
        self.assertContains(response, "TEA-001")

    def test_stock_in_adjustment_records_transaction(self):
        self.client.login(username="manager", password="strong-password-123")
        response = self.client.post(
            reverse("stock_adjust", args=[self.item.pk]),
            {"action": StockTransaction.ACTION_IN, "quantity": 5, "reference": "Delivery", "note": ""},
        )
        self.item.refresh_from_db()
        self.assertRedirects(response, self.item.get_absolute_url())
        self.assertEqual(self.item.quantity, 13)
        self.assertEqual(self.item.transactions.count(), 1)
        self.assertEqual(self.item.transactions.first().new_quantity, 13)

    def test_stock_out_cannot_exceed_available_quantity(self):
        self.client.login(username="manager", password="strong-password-123")
        response = self.client.post(
            reverse("stock_adjust", args=[self.item.pk]),
            {"action": StockTransaction.ACTION_OUT, "quantity": 99, "reference": "", "note": ""},
        )
        self.item.refresh_from_db()
        self.assertRedirects(response, self.item.get_absolute_url())
        self.assertEqual(self.item.quantity, 8)
        self.assertEqual(self.item.transactions.count(), 0)
