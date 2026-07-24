import base64
import io

from django.core.cache import cache
from django.db import models
from django.utils import timezone


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
        help_text="Render template used to generate QSL card images",
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
        from eqsl.render import RenderError, execute_render_code

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
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        data_url = f"data:image/png;base64,{img_str}"

        # Cache for 5 minutes
        cache.set(cache_key, data_url, 300)

        return data_url


class EmailTemplate(models.Model):
    """Email template for eQSL messages, one per language."""

    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
    ]

    name = models.CharField(max_length=100, help_text="Template name")
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default="en", help_text="Template language")
    subject = models.CharField(max_length=255, help_text="Email subject (Django template syntax)")
    body = models.TextField(help_text="Email HTML body (Django template syntax, {{ cid }} for the inline card image)")
    is_active = models.BooleanField(default=True, help_text="Whether this template can be used")
    is_default = models.BooleanField(default=False, help_text="Default template for this language")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["language", "name"]
        unique_together = [["language", "name"]]
        verbose_name = "Email Template"
        verbose_name_plural = "Email Templates"

    def __str__(self):
        return f"{self.name} ({self.get_language_display()})"

    def save(self, *args, **kwargs):
        """Ensure only one default template per language."""
        if self.is_default:
            EmailTemplate.objects.filter(language=self.language, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    @classmethod
    def default_for_language(cls, language):
        """Get the default active template for a language, falling back to English."""
        template = cls.objects.filter(language=language, is_default=True, is_active=True).first()
        if template is None and language != "en":
            template = cls.objects.filter(language="en", is_default=True, is_active=True).first()
        return template


class SendingSettings(models.Model):
    """Singleton settings for eQSL sending and external service credentials.

    Credential fields left blank fall back to the environment-based Django
    settings (.env). Values are stored in plaintext in the database, which
    is acceptable for this single-user, self-hosted application.
    """

    from_name = models.CharField(max_length=100, default="Your Friendly Ham", help_text="Sender display name")
    reply_to_email = models.EmailField(blank=True, help_text="Reply-To address (optional)")

    # SMTP configuration (blank = use .env)
    smtp_host = models.CharField(max_length=255, blank=True, help_text="SMTP server (blank = use .env)")
    smtp_port = models.PositiveIntegerField(null=True, blank=True, help_text="SMTP port (blank = use .env)")
    smtp_use_tls = models.BooleanField(default=True, help_text="Use STARTTLS")
    smtp_username = models.CharField(max_length=255, blank=True, help_text="SMTP username (blank = use .env)")
    smtp_password = models.CharField(max_length=255, blank=True, help_text="SMTP password (blank = use .env)")
    smtp_from_email = models.EmailField(blank=True, help_text="Sender email address (blank = use .env)")

    # QRZ.com credentials (blank = use .env)
    qrz_username = models.CharField(max_length=100, blank=True, help_text="QRZ.com username (blank = use .env)")
    qrz_password = models.CharField(max_length=255, blank=True, help_text="QRZ.com password (blank = use .env)")
    qrz_api_key = models.CharField(max_length=100, blank=True, help_text="QRZ Logbook API key (blank = use .env)")

    # LoTW credentials (blank = use .env)
    lotw_username = models.CharField(max_length=100, blank=True, help_text="LoTW username (blank = use .env)")
    lotw_password = models.CharField(max_length=255, blank=True, help_text="LoTW password (blank = use .env)")
    lotw_last_sync = models.DateTimeField(null=True, blank=True, help_text="Last successful LoTW sync")
    default_card_template = models.ForeignKey(
        CardTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Card template used when none is specified",
    )
    batch_size = models.PositiveIntegerField(default=10, help_text="Maximum emails per batch")
    delay_between_emails_s = models.PositiveIntegerField(default=5, help_text="Delay between emails in seconds")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sending Settings"
        verbose_name_plural = "Sending Settings"

    def __str__(self):
        return "eQSL Sending Settings"

    def save(self, *args, **kwargs):
        """Enforce singleton."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings

    def effective_smtp(self):
        """SMTP parameters with .env fallback for blank fields."""
        from django.conf import settings as django_settings

        return {
            "host": self.smtp_host or django_settings.EMAIL_HOST,
            "port": self.smtp_port or django_settings.EMAIL_PORT,
            "use_tls": self.smtp_use_tls,
            "username": self.smtp_username or django_settings.EMAIL_HOST_USER,
            "password": self.smtp_password or django_settings.EMAIL_HOST_PASSWORD,
            "from_email": self.smtp_from_email or django_settings.DEFAULT_FROM_EMAIL,
        }

    def effective_qrz(self):
        """QRZ credentials with .env fallback for blank fields."""
        from django.conf import settings as django_settings

        return {
            "username": self.qrz_username or django_settings.QRZ_USERNAME,
            "password": self.qrz_password or django_settings.QRZ_PASSWORD,
            "api_key": self.qrz_api_key or django_settings.QRZ_API_KEY,
        }

    def effective_lotw(self):
        """LoTW credentials with .env fallback for blank fields."""
        from django.conf import settings as django_settings

        return {
            "username": self.lotw_username or django_settings.LOTW_USERNAME,
            "password": self.lotw_password or django_settings.LOTW_PASSWORD,
        }


class QSOQuerySet(models.QuerySet):
    """QuerySet with eQSL status helpers."""

    SENT_STATUSES = ("sent", "delivered")

    def needs_eqsl(self):
        """QSOs with an email address and no successfully sent eQSL."""
        return self.exclude(email="").exclude(email_qsls__delivery_status__in=self.SENT_STATUSES)

    def eqsl_sent(self):
        """QSOs with at least one successfully sent eQSL."""
        return self.filter(email_qsls__delivery_status__in=self.SENT_STATUSES).distinct()


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
    qrz_lookup_at = models.DateTimeField(
        null=True, blank=True, help_text="When contact info was last looked up on QRZ.com"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = QSOQuerySet.as_manager()

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

    @property
    def eqsl_sent(self):
        """Whether an eQSL has been successfully sent for this QSO."""
        return self.email_qsls.filter(delivery_status__in=QSOQuerySet.SENT_STATUSES).exists()


class EmailQSL(models.Model):
    """Record of an eQSL card sent via email for a QSO."""

    qso = models.ForeignKey(QSO, on_delete=models.CASCADE, related_name="email_qsls", help_text="QSO this eQSL is for")
    card_template = models.ForeignKey(
        CardTemplate, on_delete=models.PROTECT, related_name="email_qsls", help_text="Card template used"
    )
    email_template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_qsls",
        help_text="Email template used",
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
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("failed", "Failed"),
            ("bounced", "Bounced"),
        ],
        help_text="Email delivery status",
    )
    error_message = models.TextField(blank=True, help_text="Error details if sending failed")

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
