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
    class Meta:
        model = RecipeIngredient
        fields = ["ingredient", "quantity", "unit", "notes"]
        widgets = {
            "ingredient": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "unit": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ingredient"].queryset = Ingredient.objects.all().order_by("name")