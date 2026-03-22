from django.db import models


class Unit(models.TextChoices):
    GRAM = "g", "Gramm"
    KILOGRAM = "kg", "Kilogramm"
    MILLILITER = "ml", "Milliliter"
    LITER = "l", "Liter"
    PIECE = "pcs", "Stück"
    TABLESPOON = "el", "Esslöffel"
    TEASPOON = "tl", "Teelöffel"


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    default_unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
        default=Unit.GRAM,
    )

    def __str__(self):
        return self.name