from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class Doctor(TimestampedModel):
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    years_of_experience = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctors'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Dr. {self.name}"
