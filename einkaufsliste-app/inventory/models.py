from django.core.exceptions import ValidationError
from django.db import models
from ingredients.models import Ingredient, Unit


class InventoryItem(models.Model):
    ingredient = models.OneToOneField(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="inventory_item",
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional. Leer lassen, wenn vorhanden, aber Menge unbekannt ist.",
    )
    unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
        blank=True,
        help_text="Optional. Wird vor allem genutzt, wenn eine Menge angegeben ist.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ingredient__name"]

    def clean(self):
        if self.quantity is not None and not self.unit:
            raise ValidationError({
                "unit": "Bitte wähle eine Einheit, wenn du eine Menge angibst."
            })

        if self.quantity is None and self.unit:
            raise ValidationError({
                "quantity": "Bitte gib eine Menge an oder entferne die Einheit."
            })

    def __str__(self):
        if self.quantity is not None and self.unit:
            return f"{self.ingredient.name}: {self.quantity} {self.unit}"
        return f"{self.ingredient.name}: vorhanden"