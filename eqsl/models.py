from django.db import models
from django.utils import timezone

from eqsl.default_render import get_default_render_code


class CardTemplate(models.Model):
    """QSL card template with design image."""

    name = models.CharField(max_length=100, unique=True, help_text="Template name")
    description = models.TextField(blank=True, help_text="Description of this template")
    image = models.ImageField(upload_to="card_templates/", help_text="QSL card template image")
    language = models.CharField(max_length=10, blank=True, default="en", help_text="Language code for this template")
    html_template = models.TextField(blank=True, help_text="Jinja2 template for email body")
    python_render_code = models.TextField(
        blank=True,
        default=get_default_render_code,
        help_text="Python code defining a render(card_template, qso) function that returns a PIL Image"
    )
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


class EmailQSL(models.Model):
    """Record of an eQSL card sent via email for a QSO."""

    qso = models.ForeignKey(QSO, on_delete=models.CASCADE, related_name="email_qsls", help_text="QSO this eQSL is for")
    card_template = models.ForeignKey(
        CardTemplate, on_delete=models.PROTECT, related_name="email_qsls", help_text="Card template used"
    )

    # Email details
    sent_at = models.DateTimeField(default=timezone.now, db_index=True, help_text="When the email was sent")
    recipient_email = models.EmailField(help_text="Email address the eQSL was sent to")
    sender_email = models.EmailField(help_text="Email address the eQSL was sent from")
    subject = models.CharField(max_length=255, help_text="Email subject line")
    body = models.TextField(help_text="Email body content")

    # Status tracking
    delivery_status = models.CharField(
        max_length=20,
        default="sent",
        choices=[
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("failed", "Failed"),
            ("bounced", "Bounced"),
        ],
        help_text="Email delivery status",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = "Email QSL"
        verbose_name_plural = "Email QSLs"
        indexes = [
            models.Index(fields=["-sent_at"]),
            models.Index(fields=["qso", "sent_at"]),
        ]

    def __str__(self):
        return f"eQSL to {self.qso.call} sent at {self.sent_at.strftime('%Y-%m-%d %H:%M')}"
