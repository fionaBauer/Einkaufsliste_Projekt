from django import forms
from .models import InventoryItem
from ingredients.models import Ingredient


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ["ingredient", "quantity", "unit"]
        labels = {
            "ingredient": "Zutat",
            "quantity": "Menge",
            "unit": "Einheit",
        }
        widgets = {
            "ingredient": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "unit": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        exclude_used_ingredients = kwargs.pop("exclude_used_ingredients", False)
        super().__init__(*args, **kwargs)

        self.fields["unit"].required = False
        self.fields["quantity"].required = False

        ingredient_queryset = Ingredient.objects.all().order_by("name")

        if exclude_used_ingredients:
            used_ingredient_ids = list(
                InventoryItem.objects.values_list("ingredient_id", flat=True)
            )

            if self.instance and self.instance.pk and self.instance.ingredient_id in used_ingredient_ids:
                used_ingredient_ids.remove(self.instance.ingredient_id)

            ingredient_queryset = ingredient_queryset.exclude(id__in=used_ingredient_ids)

        self.fields["ingredient"].queryset = ingredient_queryset

    def clean_ingredient(self):
        ingredient = self.cleaned_data.get("ingredient")
        if not ingredient:
            return ingredient

        existing_item = InventoryItem.objects.filter(ingredient=ingredient)

        if self.instance.pk:
            existing_item = existing_item.exclude(pk=self.instance.pk)

        if existing_item.exists():
            raise forms.ValidationError("Diese Zutat ist bereits im Inventar vorhanden.")

        return ingredient

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get("quantity")
        unit = cleaned_data.get("unit")

        if quantity is not None and not unit:
            self.add_error("unit", "Bitte wähle eine Einheit, wenn du eine Menge angibst.")

        if quantity is None and unit:
            self.add_error("quantity", "Bitte gib eine Menge an oder entferne die Einheit.")

        return cleaned_data