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

    def __str__(self):
        return f"Einstellungen von {self.user.username}"