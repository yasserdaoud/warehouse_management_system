from decimal import Decimal

from django.db import models
from django.urls import reverse
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=120, unique=True)
    contact_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("contacts")


class Contract(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_TERMINATED = "terminated"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_TERMINATED, "Terminated"),
    ]

    number = models.CharField(max_length=120, unique=True)

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "number"]

    def __str__(self):
        return self.number

    def get_absolute_url(self):
        return reverse("contract_detail", kwargs={"pk": self.pk})

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE


class StockItem(models.Model):
    UNIT_CHOICES = [
        ("pcs", "Pieces"),
        ("box", "Boxes"),
        ("pack", "Packs"),
    ]

    name = models.CharField(max_length=140)
    sku = models.CharField(max_length=40, unique=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    quantity = models.PositiveIntegerField(default=0)

    reorder_level = models.PositiveIntegerField(default=10)

    unit = models.CharField(
        max_length=12,
        choices=UNIT_CHOICES,
        default="pcs",
    )

    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    location = models.CharField(
        max_length=120,
        blank=True,
    )

    # Contract number
    contract_number = models.CharField(
        max_length=120,
        blank=True,
    )

    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_items",
    )

    # Item image
    image = models.ImageField(
        upload_to="stock_items/",
        blank=True,
        null=True,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def get_absolute_url(self):
        return reverse(
            "stock_detail",
            kwargs={"pk": self.pk},
        )

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    @property
    def stock_value(self):
        return self.quantity * Decimal(self.unit_cost)


class StockTransaction(models.Model):
    ACTION_IN = "in"
    ACTION_OUT = "out"
    ACTION_INSER = "inservice"
    ACTION_ADJUST = "adjust"

    ACTION_CHOICES = [
        (ACTION_IN, "Stock in"),
        (ACTION_OUT, "Stock out"),
        (ACTION_INSER, "Stock in service"),
        (ACTION_ADJUST, "Adjustment"),
    ]

    item = models.ForeignKey(
        StockItem,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
    )

    quantity = models.PositiveIntegerField()

    previous_quantity = models.PositiveIntegerField()

    new_quantity = models.PositiveIntegerField()

    reference = models.CharField(
        max_length=120,
        blank=True,
    )
    new_location = models.CharField(
        max_length=120,
        blank=True,
    )

    note = models.TextField(blank=True)

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.get_action_display()} - "
            f"{self.item.sku} x {self.quantity}"
        )