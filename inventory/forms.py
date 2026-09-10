from django import forms

from .models import Contract, StockItem, StockTransaction, Supplier


class StockItemForm(forms.ModelForm):
    class Meta:
        model = StockItem
        fields = [
            "name",
            "sku",
            "category",
            "supplier",
            "quantity",
            "reorder_level",
            "unit",
            "unit_cost",
            "location",
            "contract_number",
            "contract",
            "image",
            "notes",
        ]
        widgets = {
 
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Notes",
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "contract": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        supplier = cleaned_data.get("supplier")
        contract = cleaned_data.get("contract")

        if contract and supplier and contract.supplier_id and contract.supplier_id != supplier.id:
            self.add_error(
                "contract",
                f"Contract '{contract.number}' belongs to {contract.supplier}, "
                f"not {supplier}. Choose a matching supplier or a different contract.",
            )

        if contract:
            cleaned_data["contract_number"] = contract.number

        return cleaned_data


class StockAdjustmentForm(forms.Form):
    action = forms.ChoiceField(
        choices=StockTransaction.ACTION_CHOICES
    )
    quantity = forms.IntegerField(min_value=0)
    reference = forms.CharField(
        max_length=120,
        required=False
    )
    new_location = forms.CharField(
            max_length=120,
            required=False
        )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3})
    )


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name",
            "contact_name",
            "phone",
            "email",
            "address",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Supplier name",
            }),
            "contact_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Contact person",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Phone number",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Email address",
            }),
            "address": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Supplier address",
            }),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = [
            "number",
            "supplier",
            "start_date",
            "end_date",
            "value",
            "status",
            "notes",
        ]
        widgets = {
            "number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Contract number",
            }),
            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "value": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
            }),
            "status": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Notes",
            }),
        }

    def clean_number(self):
        return self.cleaned_data["number"].strip()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be before the start date.")
        return cleaned_data