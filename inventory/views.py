import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import DecimalField, F, Q, Sum, Count
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ContractForm, StockAdjustmentForm, StockItemForm, SupplierForm
from .models import Contract, StockItem, StockTransaction, Supplier



def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "includes/home.html")


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your account is ready. Welcome to HAMRA Stock.")
            return redirect("dashboard")
    else:
        form = UserCreationForm()
    return render(request, "includes/register.html", {"form": form})


@login_required
def dashboard(request):
    items = StockItem.objects.select_related("category", "supplier")
    total_items = items.count()
    total_units = items.aggregate(total=Sum("quantity"))["total"] or 0
    low_stock = items.filter(quantity__lte=F("reorder_level"))
    low_stock_count = low_stock.count()
    recent_transactions = StockTransaction.objects.select_related("item")[:8]
    total_value = sum(item.stock_value for item in items)

    # --- Stock value by category (doughnut chart) ---
    category_rows = (
        items.values("category__name")
        .annotate(
            total=Sum(
                F("quantity") * F("unit_cost"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .order_by("-total")
    )
    category_labels = [row["category__name"] or "Uncategorized" for row in category_rows]
    category_values = [float(row["total"] or 0) for row in category_rows]

    # --- Stock status (low vs healthy) ---
    stock_status_labels = ["Low stock", "Healthy"]
    stock_status_values = [low_stock_count, max(total_items - low_stock_count, 0)]

    # --- Stock movements over the last 14 days (stock in vs stock out) ---
    since = timezone.now() - timedelta(days=13)
    since_date = since.date()
    movement_rows = (
        StockTransaction.objects.filter(
            created_at__gte=since,
            action__in=[StockTransaction.ACTION_IN, StockTransaction.ACTION_OUT],
        )
        .annotate(day=TruncDate("created_at"))
        .values("day", "action")
        .annotate(total=Sum("quantity"))
    )
    in_by_day = {}
    out_by_day = {}
    for row in movement_rows:
        if row["action"] == StockTransaction.ACTION_IN:
            in_by_day[row["day"]] = row["total"]
        else:
            out_by_day[row["day"]] = row["total"]

    day_range = [since_date + timedelta(days=i) for i in range(14)]
    movement_day_labels = [d.strftime("%b %d") for d in day_range]
    stock_in_series = [in_by_day.get(d, 0) for d in day_range]
    stock_out_series = [out_by_day.get(d, 0) for d in day_range]

    context = {
        "total_items": total_items,
        "total_units": total_units,
        "low_stock_count": low_stock_count,
        "total_value": total_value,
        "low_stock_items": low_stock[:6],
        "recent_transactions": recent_transactions,
        "category_labels": category_labels,
        "category_values": category_values,
        "stock_status_labels": stock_status_labels,
        "stock_status_values": stock_status_values,
        "movement_day_labels": movement_day_labels,
        "stock_in_series": stock_in_series,
        "stock_out_series": stock_out_series,
    }
    return render(request, "includes/dashboard.html", context)


@login_required
def view_stock(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    items = StockItem.objects.select_related("category", "supplier")

    if query:
        for word in query.split():
            items = items.filter(
                Q(name__icontains=word)
                | Q(sku__icontains=word)
                | Q(location__icontains=word)
                | Q(category__name__icontains=word)
                | Q(supplier__name__icontains=word)
                | Q(contract_number__icontains=word)
            )

    if status == "low":
        items = items.filter(quantity__lte=F("reorder_level"))

    items = items.distinct()

    return render(request, "includes/view_stock.html", {"items": items, "query": query, "status": status})


@login_required
def stock_detail(request, pk):
    item = get_object_or_404(StockItem.objects.select_related("category", "supplier"), pk=pk)
    transactions = item.transactions.all()[:12]
    adjustment_form = StockAdjustmentForm()
    return render(
        request,
        "includes/stock_detail.html",
        {"item": item, "transactions": transactions, "adjustment_form": adjustment_form},
    )


@login_required
def stock_create(request):
    if request.method == "POST":

        form = StockItemForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            item = form.save()

            StockTransaction.objects.create(
                item=item,
                action=StockTransaction.ACTION_ADJUST,
                quantity=item.quantity,
                previous_quantity=0,
                new_quantity=item.quantity,
                reference="Opening balance",
                new_location="In warehouse",
            )

            messages.success(
                request,
                f"{item.name} was added to stock."
            )

            return redirect(item)

    else:
        form = StockItemForm()

    return render(
        request,
        "includes/stock_form.html",
        {
            "form": form,
            "title": "Add stock item"
        }
    )

@login_required
def stock_update(request, pk):
    item = get_object_or_404(StockItem, pk=pk)

    if request.method == "POST":

        form = StockItemForm(
            request.POST,
            request.FILES,
            instance=item
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f"{item.name} was updated."
            )

            return redirect(item)

    else:
        form = StockItemForm(instance=item)

    return render(
        request,
        "includes/stock_form.html",
        {
            "form": form,
            "title": "Edit stock item",
            "item": item
        }
    )

@login_required
@require_POST
def stock_adjust(request, pk):
    item = get_object_or_404(StockItem, pk=pk)
    form = StockAdjustmentForm(request.POST)
    if form.is_valid():
        action = form.cleaned_data["action"]
        quantity = form.cleaned_data["quantity"]
        new_location = form.cleaned_data["new_location"].strip()
        previous_quantity = item.quantity
        if action == StockTransaction.ACTION_IN:
            item.quantity += quantity
        elif action in (StockTransaction.ACTION_OUT, StockTransaction.ACTION_INSER):
            if quantity > item.quantity:
                if action == StockTransaction.ACTION_OUT:
                    messages.error(request, "Stock out quantity cannot exceed the current quantity.")
                else:
                    messages.error(request, "Quantity sent to service cannot exceed the current quantity.")
                return redirect(item)
            item.quantity -= quantity
        else:
            item.quantity = quantity

        update_fields = ["quantity", "updated_at"]
        if new_location:
            item.location = new_location
            update_fields.append("location")

        item.save(update_fields=update_fields)
        StockTransaction.objects.create(
            item=item,
            action=action,
            quantity=quantity,
            previous_quantity=previous_quantity,
            new_quantity=item.quantity,
            reference=form.cleaned_data["reference"],
            new_location=new_location,
            note=form.cleaned_data["note"],
        )
        if action == StockTransaction.ACTION_INSER:
            messages.success(request, f"{quantity} {item.get_unit_display()} of {item.name} sent to service.")
        elif new_location:
            messages.success(request, f"Stock movement recorded and location updated to '{new_location}'.")
        else:
            messages.success(request, "Stock movement recorded.")
    else:
        messages.error(request, "Please check the stock movement form.")
    return redirect(item)


@login_required
@require_POST
def stock_delete(request, pk):
    item = get_object_or_404(StockItem, pk=pk)
    item.delete()
    messages.success(request, f"{item.name} was deleted.")
    return redirect("view_stock")


@login_required
def view_history(request):
    transactions = StockTransaction.objects.select_related("item")
    return render(request, "includes/view_history.html", {"transactions": transactions})


@login_required
def contacts(request):
    query = request.GET.get("q", "").strip()
    suppliers = Supplier.objects.all()

    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query)
            | Q(contact_name__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
            | Q(address__icontains=query)
        )

    suppliers = suppliers.annotate(
        stock_item_count=Sum("stockitem__quantity"),
        contract_count=Count("contracts", distinct=True),
    )

    return render(
        request,
        "includes/contacts.html",
        {"suppliers": suppliers, "query": query},
    )


@login_required
def supplier_create(request):
    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(
                request,
                f"Supplier '{supplier.name}' was added successfully.",
            )
            return redirect("contacts")
    else:
        form = SupplierForm()

    return render(
        request,
        "includes/supplier_form.html",
        {"form": form, "title": "Add supplier"},
    )


@login_required
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == "POST":
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(
                request,
                f"Supplier '{supplier.name}' was updated successfully.",
            )
            return redirect("contacts")
    else:
        form = SupplierForm(instance=supplier)

    return render(
        request,
        "includes/supplier_form.html",
        {
            "form": form,
            "title": "Edit supplier",
            "supplier": supplier,
            "contract_count": supplier.contracts.count(),
        },
    )


@login_required
@require_POST
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier_name = supplier.name
    supplier.delete()
    messages.success(
        request,
        f"Supplier '{supplier_name}' was deleted successfully.",
    )
    return redirect("contacts")    

@login_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier_contracts = supplier.contracts.all()

    return render(
        request,
        "includes/supplier_detail.html",
        {
            "supplier": supplier,
            "contracts": supplier_contracts,
            "contract_count": supplier_contracts.count(),
        },
    )

@login_required
def items_in_service(request):

    search = request.GET.get("search", "").strip()

    # Toutes les transactions "Stock in service"
    transactions = (
        StockTransaction.objects
        .filter(action=StockTransaction.ACTION_INSER)
        .select_related("item", "item__supplier")
        .order_by("-created_at")
    )

    # Recherche
    if search:
        for word in search.split():
            transactions = transactions.filter(
                Q(item__name__icontains=word) | Q(item__sku__icontains=word)
            )

    # Statistiques
    total_movements = StockTransaction.objects.filter(
        action=StockTransaction.ACTION_INSER
    ).count()

    total_quantity = StockTransaction.objects.filter(
        action=StockTransaction.ACTION_INSER
    ).aggregate(
        total=Sum("quantity")
    )["total"] or 0

    context = {
        "transactions": transactions,
        "total_movements": total_movements,
        "total_quantity": total_quantity,
        "search": search,
        "current": "service",
    }

    return render(
        request,
        "includes/items_in_service.html",
        context
    )


@login_required
def contracts(request):
    query = request.GET.get("q", "").strip()
    contract_list = Contract.objects.select_related("supplier").annotate(
        item_count=Count("stock_items", distinct=True)
    )

    if query:
        for word in query.split():
            contract_list = contract_list.filter(
                Q(number__icontains=word)
                | Q(supplier__name__icontains=word)
                | Q(status__icontains=word)
            )

    return render(
        request,
        "includes/contracts.html",
        {"contracts": contract_list, "query": query},
    )


@login_required
def contract_create(request):
    if request.method == "POST":
        form = ContractForm(request.POST)
        if form.is_valid():
            contract = form.save()
            messages.success(
                request,
                f"Contract '{contract.number}' was added successfully.",
            )
            return redirect(contract)
    else:
        form = ContractForm()

    return render(
        request,
        "includes/contract_form.html",
        {"form": form, "title": "Add contract"},
    )


@login_required
def contract_update(request, pk):
    contract = get_object_or_404(Contract, pk=pk)

    if request.method == "POST":
        form = ContractForm(request.POST, instance=contract)
        if form.is_valid():
            contract = form.save()
            messages.success(
                request,
                f"Contract '{contract.number}' was updated successfully.",
            )
            return redirect(contract)
    else:
        form = ContractForm(instance=contract)

    return render(
        request,
        "includes/contract_form.html",
        {"form": form, "title": "Edit contract", "contract": contract},
    )


@login_required
@require_POST
def contract_delete(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    contract_number = contract.number
    contract.delete()
    messages.success(
        request,
        f"Contract '{contract_number}' was deleted successfully.",
    )
    return redirect("contracts")


@login_required
def contract_detail(request, pk):
    contract = get_object_or_404(Contract.objects.select_related("supplier"), pk=pk)
    linked_items = contract.stock_items.select_related("category", "supplier")

    return render(
        request,
        "includes/contract_detail.html",
        {"contract": contract, "linked_items": linked_items},
    )