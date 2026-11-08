from django.db import models
from ingredients.models import Ingredient


class DealSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    # Verhindert zwei gleichzeitig laufende Syncs derselben Quelle (z.B. durch Doppelklick
    # oder zwei Requests, die auf unterschiedlichen Gunicorn-Workern landen).
    is_syncing = models.BooleanField(default=False)
    sync_started_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(blank=True)
    # Fortschritt für die Ladeanzeige ("12 von 40 Suchbegriffen")
    sync_total = models.PositiveIntegerField(default=0)
    sync_done = models.PositiveIntegerField(default=0)
    last_sync_count = models.PositiveIntegerField(default=0)

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


# Angebotsseiten der Händler – auf dem Handy öffnen viele davon direkt die Händler-App.
# Schlüssel: Namensanfang des Markts in Kleinbuchstaben (Marktguru: "ALDI SÜD", "Netto Marken-Discount" …)
STORE_OFFER_URLS = {
    "aldi süd": "https://www.aldi-sued.de/",
    "aldi nord": "https://www.aldi-nord.de/angebote.html",
    "lidl": "https://www.lidl.de/",
    "kaufland": "https://filiale.kaufland.de/angebote.html",
    "rewe": "https://www.rewe.de/angebote/",
    "penny": "https://www.penny.de/angebote",
    "netto": "https://www.netto-online.de/angebote",
    "edeka": "https://www.edeka.de/",
    "marktkauf": "https://www.marktkauf.de/",
    "norma": "https://www.norma-online.de/de/angebote/",
    "globus": "https://www.globus.de/",
}


def store_offer_url(store_name):
    name = (store_name or "").lower()
    for prefix, url in STORE_OFFER_URLS.items():
        if name.startswith(prefix):
            return url
    return ""


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
    # Nur der Produktname ohne Marke – darauf läuft der Abgleich mit Zutaten
    product_name = models.CharField(max_length=255, blank=True)
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

    # Grundpreis (z.B. 5.96 €/kg) – fehlt der "statt"-Preis, ist das die beste Vergleichsgröße
    reference_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    reference_unit = models.CharField(max_length=20, blank=True)
    package_size = models.CharField(max_length=60, blank=True)
    requires_loyalty = models.BooleanField(default=False)
    # Kategorien laut Marktguru (z.B. "Joghurt|Veganes") – zum Aussortieren falscher Treffer
    source_categories = models.CharField(max_length=255, blank=True)

    discount_text = models.CharField(max_length=100, blank=True)
    product_url = models.URLField(max_length=500, blank=True)
    image_url = models.URLField(max_length=500, blank=True)

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

    @property
    def offer_url(self):
        """Direkter Link zum Angebot, sonst die Angebotsseite des Händlers."""
        return self.product_url or store_offer_url(self.store.name)

    @property
    def reference_label(self):
        if self.reference_price is None or not self.reference_unit:
            return ""
        return f"{self.reference_price:.2f} €/{self.reference_unit}"

    @property
    def valid_until_label(self):
        if not self.valid_until:
            return ""
        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        d = self.valid_until
        return f"bis {weekdays[d.weekday()]}., {d.day}.{d.month}."