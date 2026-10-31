from django.db import models


class Unit(models.TextChoices):
    GRAM = "g", "Gramm"
    KILOGRAM = "kg", "Kilogramm"
    MILLILITER = "ml", "Milliliter"
    LITER = "l", "Liter"
    PIECE = "pcs", "Stück"
    PACKAGE = "pkg", "Packung"
    TABLESPOON = "el", "Esslöffel"
    TEASPOON = "tl", "Teelöffel"


class IngredientCategory(models.TextChoices):
    # Reihenfolge = Anzeige-Reihenfolge (grob wie die Gänge im Supermarkt)
    FRUIT_VEG = "fruit_veg", "Obst & Gemüse"
    BREAD = "bread", "Brot & Backwaren"
    MEAT_FISH = "meat_fish", "Fleisch & Fisch"
    DAIRY = "dairy", "Milchprodukte & Eier"
    GRAINS = "grains", "Nudeln, Reis & Getreide"
    CANNED = "canned", "Konserven & Hülsenfrüchte"
    SPICES = "spices", "Gewürze, Öle & Saucen"
    BAKING = "baking", "Backen & Süßen"
    SNACKS = "snacks", "Süßes & Snacks"
    FREEZER = "freezer", "Tiefkühl"
    DRINKS = "drinks", "Getränke"
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