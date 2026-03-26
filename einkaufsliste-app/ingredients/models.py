from django.db import models


class Unit(models.TextChoices):
    GRAM = "g", "Gramm"
    KILOGRAM = "kg", "Kilogramm"
    MILLILITER = "ml", "Milliliter"
    LITER = "l", "Liter"
    PIECE = "pcs", "Stück"
    TABLESPOON = "el", "Esslöffel"
    TEASPOON = "tl", "Teelöffel"


class IngredientCategory(models.TextChoices):
    SPICES = "spices", "Gewürze"
    FRIDGE = "fridge", "Kühlschrank"
    DRINKS = "drinks", "Getränke"
    PANTRY = "pantry", "Vorrat"
    FREEZER = "freezer", "Tiefkühl"
    BAKING = "baking", "Backzutaten"
    OTHER = "other", "Sonstiges"


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    default_unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
        default=Unit.GRAM,
    )
    category = models.CharField(
        max_length=20,
        choices=IngredientCategory.choices,
        default=IngredientCategory.OTHER,
    )

    def __str__(self):
        return self.name