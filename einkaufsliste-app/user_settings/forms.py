from django import forms
from .models import UserSettings


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ["postal_code"]
        labels = {
            "postal_code": "Postleitzahl",
        }
        widgets = {
            "postal_code": forms.TextInput(attrs={
                "placeholder": "z.B. 89231",
                "class": "form-input",
            })
        }