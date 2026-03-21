from django import forms
from .models import ShoppingListItem
from ingredients.models import Ingredient, Unit


class ShoppingListItemForm(forms.ModelForm):
    class Meta:
        model = ShoppingListItem
        fields = ["ingredient", "quantity", "unit"]
        labels = {
            "ingredient": "Lebensmittel",
            "quantity": "Menge",
            "unit": "Einheit",
        }
        widgets = {
            "ingredient": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "unit": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ingredient"].queryset = Ingredient.objects.all().order_by("name")
        self.fields["quantity"].required = False
        self.fields["unit"].required = False

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get("quantity")
        unit = cleaned_data.get("unit")

        if quantity is not None and not unit:
            self.add_error("unit", "Bitte wähle eine Einheit, wenn du eine Menge angibst.")

        if quantity is None and unit:
            self.add_error("quantity", "Bitte gib eine Menge an oder entferne die Einheit.")

        return cleaned_data