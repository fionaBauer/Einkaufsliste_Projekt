import uuid

from decimal import Decimal
from django.db import models
from ingredients.models import Ingredient, Unit


def recipe_image_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    unique = uuid.uuid4().hex[:8]
    return f"recipe_images/household_{instance.household_id}/{unique}.{ext}"

class Tag(models.TextChoices):
    BREAKFAST = "breakfast", "Frühstück"
    LUNCH = "lunch", "Mittagessen"
    DINNER = "dinner", "Abendessen"
    SNACK = "snack", "Snack"

    MAIN = "main", "Hauptgericht"
    SIDE = "side", "Beilage"
    SOUP = "soup", "Suppe"
    SALAD = "salad", "Salat"
    CASSEROLE = "casserole", "Auflauf"
    SAUCE = "sauce", "Sauce & Dip"
    BREAD = "bread", "Brot & Gebäck"
    CAKE = "cake", "Kuchen"
    DESSERT = "dessert", "Dessert"
    DRINK = "drink", "Getränk"

    MEAT = "meat", "Fleisch"
    FISH = "fish", "Fisch"
    VEGETARIAN = "vegetarian", "Vegetarisch"
    VEGAN = "vegan", "Vegan"

    GLUTEN_FREE = "gluten_free", "Glutenfrei"
    LACTOSE_FREE = "lactose_free", "Laktosefrei"
    LOW_CARB = "low_carb", "Low Carb"
    HIGH_PROTEIN = "high_protein", "High Protein"
    QUICK = "quick", "Schnell"


# Innerhalb einer Gruppe reicht beim Filtern eine Kategorie ("Fleisch" oder "Fisch").
# match_all: alle gewählten müssen zutreffen ("glutenfrei" und "laktosefrei").
TAG_GROUPS = [
    {
        "key": "meal",
        "label": "Mahlzeit",
        "tags": [Tag.BREAKFAST, Tag.LUNCH, Tag.DINNER, Tag.SNACK],
    },
    {
        "key": "course",
        "label": "Art",
        "tags": [
            Tag.MAIN, Tag.SIDE, Tag.SOUP, Tag.SALAD, Tag.CASSEROLE,
            Tag.SAUCE, Tag.BREAD, Tag.CAKE, Tag.DESSERT, Tag.DRINK,
        ],
    },
    {
        "key": "content",
        "label": "Inhalt",
        "tags": [Tag.MEAT, Tag.FISH, Tag.VEGETARIAN, Tag.VEGAN],
    },
    {
        "key": "special",
        "label": "Besonderheiten",
        "tags": [Tag.GLUTEN_FREE, Tag.LACTOSE_FREE, Tag.LOW_CARB, Tag.HIGH_PROTEIN, Tag.QUICK],
        "match_all": True,
    },
]


class Recipe(models.Model):
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="recipes",
    )
    name = models.CharField(max_length=150)
    servings = models.PositiveIntegerField(default=1)
    instructions = models.TextField(blank=True)
    image = models.ImageField(upload_to=recipe_image_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name="recipes",
    )

    def __str__(self):
        return f"{self.name} ({self.servings} Portion(en))"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            from .images import optimize_recipe_image

            new_name = optimize_recipe_image(self.image)
            if new_name and new_name != self.image.name:
                # Bild wurde z.B. von PNG nach JPEG umgewandelt → Pfad ohne erneutes save() nachziehen
                Recipe.objects.filter(pk=self.pk).update(image=new_name)
                self.image.name = new_name

    @property
    def thumbnail_url(self):
        """Kleines Vorschaubild für Karten/Listen; fällt aufs Original zurück, falls noch keins existiert."""
        if not self.image:
            return ""
        from .images import thumbnail_name

        thumb = thumbnail_name(self.image.name)
        if self.image.storage.exists(thumb):
            return self.image.storage.url(thumb)
        return self.image.url

    @property
    def tag_labels(self):
        saved = {recipe_tag.tag for recipe_tag in self.tags.all()}
        return [tag.label for tag in Tag if tag.value in saved]

    def set_tags(self, tags):
        self.tags.exclude(tag__in=tags).delete()
        RecipeTag.objects.bulk_create(
            [RecipeTag(recipe=self, tag=tag) for tag in tags],
            ignore_conflicts=True,
        )

    def scale_factor(self, target_servings: int) -> Decimal:
        if self.servings <= 0:
            return Decimal("1")
        return Decimal(target_servings) / Decimal(self.servings)


class RecipeTag(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="tags",
    )
    tag = models.CharField(max_length=20, choices=Tag.choices)

    class Meta:
        unique_together = ("recipe", "tag")

    def __str__(self):
        return f"{self.get_tag_display()} ({self.recipe.name})"


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