from django.db import models
from django.utils import timezone
from django.core.cache import cache
import io
import base64


def create_example_qso():
    """Create an example QSO for preview/testing purposes."""
    return QSO(
        my_call="N0CALL",
        my_gridsquare="FN31pr",
        my_rig="Icom IC-7300",
        call="W1AW",
        name="Hiram Percy Maxim",
        email="example@arrl.org",
        frequency=14.250,
        band="20m",
        mode="SSB",
        rst_sent="59",
        rst_rcvd="59",
        tx_pwr=100,
        timestamp=timezone.now(),
        sota_ref="W7W/LC-001",
        pota_ref="",
        country="United States",
        lang="en",
    )


class RenderTemplate(models.Model):
    """Python render template for generating QSL card images."""

    name = models.CharField(max_length=100, unique=True, help_text="Template name (e.g., 'default', 'simple')")
    description = models.TextField(blank=True, help_text="Description of this render template")
    python_render_code = models.TextField(
        help_text="Python code defining a render(card_template, qso) function that returns a PIL Image"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Render Template"
        verbose_name_plural = "Render Templates"

    def __str__(self):
        return self.name


class CardTemplate(models.Model):
    """QSL card template with design image."""

    name = models.CharField(max_length=100, unique=True, help_text="Template name")
    description = models.TextField(blank=True, help_text="Description of this template")
    image = models.ImageField(upload_to="card_templates/", help_text="QSL card template image")
    language = models.CharField(max_length=10, blank=True, default="en", help_text="Language code for this template")
    html_template = models.TextField(blank=True, help_text="Jinja2 template for email body")
    render_template = models.ForeignKey(
        RenderTemplate,
        on_delete=models.PROTECT,
        related_name="card_templates",
        null=True,  # Temporarily nullable for migration
        blank=True,
        help_text="Render template used to generate QSL card images"
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

    def render_example(self):
        """
        Render an example QSL card using this template.

        Returns:
            PIL.Image.Image: The rendered card image, or None if rendering fails
        """
        from eqsl.render import execute_render_code, RenderError

        try:
            example_qso = create_example_qso()
            result = execute_render_code(self, example_qso)
            return result
        except RenderError as e:
            # Log the error but don't crash the admin
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to render example for CardTemplate {self.name}: {e}")
            return None

    def get_example_preview_data_url(self, max_width=400):
        """
        Get a data URL for the example render preview (suitable for <img src="">).

        Args:
            max_width: Maximum width for the preview image

        Returns:
            str: Data URL of the preview image, or None if rendering fails
        """
        # Include image name and render_template info in cache key so it invalidates
        # when the image or render template changes
        render_version = ""
        if self.render_template:
            render_version = f"{self.render_template.pk}_{self.render_template.updated_at.timestamp()}"

        cache_key = f"card_template_preview_{self.pk}_{max_width}_{self.image.name}_{render_version}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        img = self.render_example()
        if img is None:
            return None

        # Resize if needed
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), resample=1)  # LANCZOS

        # Convert to base64 data URL
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        data_url = f"data:image/png;base64,{img_str}"

        # Cache for 5 minutes
        cache.set(cache_key, data_url, 300)

        return data_url


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
