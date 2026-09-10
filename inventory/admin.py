from django.contrib import admin

from .models import Category, StockItem, StockTransaction, Supplier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_name", "phone", "email", "address"]
    search_fields = ["name", "contact_name", "phone", "email", "address"]


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "category", "supplier", "quantity", "reorder_level", "unit_cost", "contract_number"]
    list_filter = ["category", "supplier", "unit"]
    search_fields = ["name", "sku", "location"]


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ["item", "action", "quantity", "previous_quantity", "new_quantity", "created_at"]
    list_filter = ["action", "created_at"]
    search_fields = ["item__name", "item__sku", "reference"]
