from decimal import Decimal
from django.db import models
from ingredients.models import Ingredient, Unit


class Recipe(models.Model):
    name = models.CharField(max_length=150)
    servings = models.PositiveIntegerField(default=1)
    instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name="recipes",
    )

    def __str__(self):
        return f"{self.name} ({self.servings} Portion(en))"

    def scale_factor(self, target_servings: int) -> Decimal:
        if self.servings <= 0:
            return Decimal("1")
        return Decimal(target_servings) / Decimal(self.servings)


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="ingredient_recipes",
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
    )
    notes = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional, z. B. gehackt, fein gewürfelt",
    )

    class Meta:
        unique_together = ("recipe", "ingredient")
        ordering = ["recipe", "ingredient__name"]

    def __str__(self):
        notes_part = f" ({self.notes})" if self.notes else ""
        return f"{self.quantity} {self.unit} {self.ingredient.name}{notes_part} für {self.recipe.name}"

    def scaled_quantity(self, target_servings: int):
        factor = self.recipe.scale_factor(target_servings)
        return self.quantity * factor