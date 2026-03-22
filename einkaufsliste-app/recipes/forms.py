from django import forms
from .models import Recipe, RecipeIngredient
from ingredients.models import Ingredient


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ["name", "servings", "instructions"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "servings": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "instructions": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }


class RecipeIngredientForm(forms.ModelForm):
    ingredient_search = forms.CharField(
        label="Zutat",
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
        model = RecipeIngredient
        fields = ["ingredient", "quantity", "unit", "notes"]
        widgets = {
            "ingredient": forms.HiddenInput(),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "unit": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["ingredient"].queryset = Ingredient.objects.all().order_by("name")

        if self.instance and self.instance.pk and self.instance.ingredient:
            self.fields["ingredient_search"].initial = self.instance.ingredient.name

    def clean(self):
        cleaned_data = super().clean()
        ingredient = cleaned_data.get("ingredient")
        ingredient_search = (cleaned_data.get("ingredient_search") or "").strip()

        if not ingredient and ingredient_search:
            ingredient = Ingredient.objects.filter(name__iexact=ingredient_search).first()
            if ingredient:
                cleaned_data["ingredient"] = ingredient

        if not cleaned_data.get("ingredient"):
            self.add_error("ingredient_search", "Bitte wähle eine vorhandene Zutat aus oder lege eine neue an.")

        return cleaned_data