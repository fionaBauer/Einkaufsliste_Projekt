from django.db import models
from recipes.models import Recipe
from households.models import Household


class MealSlot(models.Model):
    MEAL_CHOICES = [
        ("breakfast", "Frühstück"),
        ("lunch", "Mittagessen"),
        ("dinner", "Abendessen"),
    ]

    RECURRENCE_CHOICES = [
        ("none", "Einmalig"),
        ("weekly", "Wöchentlich"),
        ("monthly", "Monatlich"),
    ]

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="meal_slots",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="meal_slots",
    )
    date = models.DateField()
    meal = models.CharField(max_length=10, choices=MEAL_CHOICES)
    recurrence = models.CharField(
        max_length=10,
        choices=RECURRENCE_CHOICES,
        default="none",
    )
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["date", "meal"]

    def __str__(self):
        return f"{self.get_meal_display()} am {self.date}: {self.recipe.name}"

    @property
    def meal_order(self):
        order = {"breakfast": 0, "lunch": 1, "dinner": 2}
        return order.get(self.meal, 3)