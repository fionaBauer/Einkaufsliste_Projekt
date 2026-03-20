from django import forms
from .models import Ingredient


class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ["name", "default_unit"]
        labels = {
            "name": "Name",
            "default_unit": "Standard-Einheit",
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Ingredient.objects.filter(name__iexact=name)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Diese Zutat existiert bereits.")

        return name