from django.db import models
from ingredients.models import Ingredient


class DealSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Store(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=150, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ("name", "location", "postal_code")

    def __str__(self):
        parts = [self.name]
        if self.location:
            parts.append(self.location)
        if self.postal_code:
            parts.append(self.postal_code)
        return " - ".join(parts)


class Deal(models.Model):
    source = models.ForeignKey(
        DealSource,
        on_delete=models.CASCADE,
        related_name="deals",
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="deals",
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    original_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    deal_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    discount_text = models.CharField(max_length=100, blank=True)
    product_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)

    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    matched_ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
    )

    external_id = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["store__name", "title"]
        unique_together = ("source", "external_id")

    def __str__(self):
        return f"{self.title} bei {self.store.name}"

    @property
    def savings(self):
        if self.original_price is None or self.deal_price is None:
            return None
        return self.original_price - self.deal_price