from django.conf import settings
from django.db import models


class UserSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="settings",
    )

    postal_code = models.CharField(
        max_length=10,
        blank=True,
        default="",
    )

    # Märkte, deren Angebote angezeigt werden (Namen wie bei Marktguru, z.B. "Lidl").
    # Leer = alle Märkte.
    preferred_stores = models.JSONField(default=list, blank=True)

    # Produkte, die regelmäßig gekauft werden ("Kaffee", "Butter") – sind sie im Angebot,
    # zeigt die Startseite das an.
    favorite_products = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Einstellungen von {self.user.username}"
