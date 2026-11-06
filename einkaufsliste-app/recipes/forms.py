from django import forms
from .models import Recipe, RecipeIngredient, TAG_GROUPS
from ingredients.models import Ingredient


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ["name", "servings", "instructions", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "servings": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "instructions": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "image": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        saved_tags = set(self.instance.tags.values_list("tag", flat=True)) if self.instance.pk else set()

        for group in TAG_GROUPS:
            self.fields[f"tags_{group['key']}"] = forms.MultipleChoiceField(
                label=group["label"],
                required=False,
                choices=[(tag.value, tag.label) for tag in group["tags"]],
                initial=[tag.value for tag in group["tags"] if tag.value in saved_tags],
                widget=forms.CheckboxSelectMultiple,
            )

    def regular_fields(self):
        return [field for field in self if not field.name.startswith("tags_")]

    def tag_fields(self):
        return [field for field in self if field.name.startswith("tags_")]

    def save(self, commit=True):
        recipe = super().save(commit=commit)
        if commit:
            recipe.set_tags([tag for field in self.tag_fields() for tag in self.cleaned_data[field.name]])
        return recipe


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