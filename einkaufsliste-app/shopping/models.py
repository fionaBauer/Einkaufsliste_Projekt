from django.db import models
from ingredients.models import Ingredient, Unit


class ShoppingList(models.Model):
    name = models.CharField(max_length=150, default="Aktuelle Einkaufsliste")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class ShoppingListItem(models.Model):
    STATUS_TO_BUY = "to_buy"
    STATUS_HAVE = "have"
    STATUS_CHECK = "check"

    STATUS_CHOICES = [
        (STATUS_TO_BUY, "Noch kaufen"),
        (STATUS_HAVE, "Schon vorhanden"),
        (STATUS_CHECK, "Vorhanden, Menge prüfen"),
    ]

    shopping_list = models.ForeignKey(
        ShoppingList,
        on_delete=models.CASCADE,
        related_name="items",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="shopping_items",
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_TO_BUY,
    )
    is_checked = models.BooleanField(default=False)

    class Meta:
        ordering = ["ingredient__name"]

    def __str__(self):
        quantity_part = f"{self.quantity} {self.unit}" if self.quantity is not None and self.unit else "ohne Mengenangabe"
        return f"{self.ingredient.name} - {quantity_part}"