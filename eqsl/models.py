from django.db import models
from django.utils import timezone


class CardTemplate(models.Model):
    """QSL card template with design image."""

    name = models.CharField(max_length=100, unique=True, help_text="Template name")
    description = models.TextField(blank=True, help_text="Description of this template")
    image = models.ImageField(upload_to="card_templates/", help_text="QSL card template image")
    is_active = models.BooleanField(default=False, help_text="Whether this template is currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Card Template"
        verbose_name_plural = "Card Templates"

    def __str__(self):
        return self.name


class QSO(models.Model):
    """Amateur radio contact (QSO) record."""

    # Station information
    my_call = models.CharField(max_length=20, help_text="Your callsign")
    my_gridsquare = models.CharField(max_length=10, blank=True, help_text="Your grid square")
    my_rig = models.CharField(max_length=100, blank=True, help_text="Your radio equipment")

    # Contact information
    call = models.CharField(max_length=20, db_index=True, help_text="Contact's callsign")
    name = models.CharField(max_length=100, blank=True, help_text="Contact's name")
    email = models.EmailField(blank=True, help_text="Contact's email address")

    # QSO details
    frequency = models.FloatField(help_text="Frequency in MHz")
    band = models.CharField(max_length=10, help_text="Band (e.g., 20m, 2m)")
    mode = models.CharField(max_length=20, help_text="Mode (e.g., SSB, CW, FT8)")
    rst_sent = models.CharField(max_length=10, help_text="RST sent")
    rst_rcvd = models.CharField(max_length=10, help_text="RST received")
    tx_pwr = models.IntegerField(help_text="Transmit power in watts")

    # Timestamp
    timestamp = models.DateTimeField(default=timezone.now, db_index=True, help_text="QSO date and time")

    # Additional references
    sota_ref = models.CharField(max_length=20, blank=True, help_text="SOTA reference")
    pota_ref = models.CharField(max_length=20, blank=True, help_text="POTA reference")
    country = models.CharField(max_length=100, blank=True, help_text="Contact's country")
    lang = models.CharField(max_length=10, blank=True, default="en", help_text="Language code")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "QSO"
        verbose_name_plural = "QSOs"
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["call"]),
        ]

    def __str__(self):
        return f"{self.call} on {self.band} {self.mode} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
