from django import forms

from ingredients.models import Ingredient
from .models import ShoppingListItem


class ShoppingListItemForm(forms.ModelForm):
    ingredient_search = forms.CharField(
        label="Lebensmittel",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control ingredient-search-input",
                "placeholder": "Zutat suchen...",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = ShoppingListItem
        fields = ["ingredient", "quantity", "unit"]
        labels = {
            "ingredient": "Lebensmittel",
            "quantity": "Menge",
            "unit": "Einheit",
        }
        widgets = {
            "ingredient": forms.HiddenInput(),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "unit": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ingredient"].queryset = Ingredient.objects.all().order_by("name")
        self.fields["quantity"].required = False
        self.fields["unit"].required = False

        if self.instance and self.instance.pk and self.instance.ingredient:
            self.fields["ingredient_search"].initial = self.instance.ingredient.name

    def clean(self):
        cleaned_data = super().clean()

        ingredient = cleaned_data.get("ingredient")
        ingredient_search = (cleaned_data.get("ingredient_search") or "").strip()
        quantity = cleaned_data.get("quantity")
        unit = cleaned_data.get("unit")

        if not ingredient and ingredient_search:
            ingredient = Ingredient.objects.filter(name__iexact=ingredient_search).first()
            if ingredient:
                cleaned_data["ingredient"] = ingredient

        if not cleaned_data.get("ingredient"):
            self.add_error(
                "ingredient_search",
                "Bitte wähle eine vorhandene Zutat aus oder lege eine neue an.",
            )

        if quantity is not None and not unit:
            self.add_error("unit", "Bitte wähle eine Einheit, wenn du eine Menge angibst.")

        if quantity is None and unit:
            self.add_error("quantity", "Bitte gib eine Menge an oder entferne die Einheit.")

        return cleaned_data