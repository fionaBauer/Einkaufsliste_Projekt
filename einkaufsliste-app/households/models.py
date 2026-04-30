import uuid

from django.conf import settings
from django.db import models


class Household(models.Model):
    name = models.CharField(max_length=150)
    invite_token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_households",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="households",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def regenerate_invite_token(self):
        self.invite_token = uuid.uuid4()
        self.save(update_fields=["invite_token"])
