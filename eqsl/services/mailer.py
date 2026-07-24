"""
eQSL email composition and sending.

Composes a multipart/related HTML email with the rendered QSL card
attached inline (referenced by Content-ID), and records the result
as an EmailQSL.
"""

import io
import logging
import os
import uuid

from django.core.mail import EmailMultiAlternatives, get_connection
from django.template import Context, Template
from django.utils.html import strip_tags

from eqsl.models import CardTemplate, EmailQSL, EmailTemplate, SendingSettings
from eqsl.render import RenderError, execute_render_code

logger = logging.getLogger(__name__)


class EQSLSendError(Exception):
    """Exception raised when an eQSL cannot be composed or sent."""

    pass


# Maps lowercase country names (as they appear on QSO.country) to a
# template language code. Countries not listed use the default English
# template. Ported from the legacy CLI tool's `languages` config.
SPANISH_COUNTRIES = {
    "argentina",
    "bolivia",
    "chile",
    "colombia",
    "costa rica",
    "cuba",
    "dominican republic",
    "ecuador",
    "el salvador",
    "equatorial guinea",
    "guatemala",
    "honduras",
    "mexico",
    "nicaragua",
    "panama",
    "paraguay",
    "peru",
    "puerto rico",
    "spain",
    "uruguay",
    "venezuela",
}

FRENCH_COUNTRIES = {
    "benin",
    "burundi",
    "cameroon",
    "chad",
    "djibouti",
    "france",
    "french polynesia",
    "gabon",
    "guinea",
    "haiti",
    "luxembourg",
    "madagascar",
    "mali",
    "monaco",
    "new caledonia",
    "niger",
    "reunion",
    "senegal",
    "seychelles",
    "switzerland",
    "togo",
    "vanuatu",
}

COUNTRY_LANGUAGES = dict.fromkeys(SPANISH_COUNTRIES, "es")
COUNTRY_LANGUAGES.update(dict.fromkeys(FRENCH_COUNTRIES, "fr"))


def language_for_qso(qso):
    """
    Determine the email template language for a QSO.

    Uses the QSO's explicit lang field if set to a non-default value,
    otherwise maps the QSO country to a language.
    """
    if qso.lang and qso.lang != "en":
        return qso.lang
    return COUNTRY_LANGUAGES.get((qso.country or "").strip().lower(), "en")


def _render_template_string(template_string, context):
    """Render a Django template string with the given context dict."""
    return Template(template_string).render(Context(context))


def compose_eqsl(qso, card_template, email_template):
    """
    Compose the eQSL email parts for a QSO.

    Args:
        qso: QSO instance
        card_template: CardTemplate to render the card with
        email_template: EmailTemplate for subject/body

    Returns:
        tuple: (subject, html_body, image_bytes, cid)

    Raises:
        EQSLSendError: If the card cannot be rendered
    """
    try:
        image = execute_render_code(card_template, qso)
    except RenderError as e:
        raise EQSLSendError(f"Failed to render QSL card: {e}") from e

    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=80, optimize=True)
    image_bytes = buffer.getvalue()

    cid = f"eqsl-{uuid.uuid4().hex}"
    context = {
        "qso": qso,
        "cid": cid,
        "qso_date": qso.timestamp.strftime("%B %d, %Y at %H:%M UTC"),
    }
    subject = _render_template_string(email_template.subject, context).strip()
    html_body = _render_template_string(email_template.body, context)

    return subject, html_body, image_bytes, cid


def send_eqsl(qso, card_template=None, email_template=None):
    """
    Render, send, and record an eQSL email for a QSO.

    Args:
        qso: QSO instance (must have an email address unless DEBUG_EMAIL is set)
        card_template: CardTemplate to use (defaults to SendingSettings default,
            then any active template matching the QSO language)
        email_template: EmailTemplate to use (defaults to the default template
            for the QSO's language)

    Returns:
        EmailQSL: The created record (delivery_status "sent" or "failed")

    Raises:
        EQSLSendError: If no recipient, card template, or email template is available
    """
    sending_settings = SendingSettings.get_settings()
    smtp = sending_settings.effective_smtp()

    if not smtp["from_email"]:
        raise EQSLSendError("No sender address configured — set it on the Settings page or via SMTP_FROM_EMAIL in .env")

    recipient = os.getenv("DEBUG_EMAIL") or qso.email
    if not recipient:
        raise EQSLSendError(f"QSO {qso} has no email address")

    if card_template is None:
        card_template = sending_settings.default_card_template
    if card_template is None:
        card_template = CardTemplate.objects.filter(is_active=True).first()
    if card_template is None:
        raise EQSLSendError("No card template available")

    if email_template is None:
        email_template = EmailTemplate.default_for_language(language_for_qso(qso))
    if email_template is None:
        raise EQSLSendError("No email template available")

    subject, html_body, image_bytes, cid = compose_eqsl(qso, card_template, email_template)

    from_email = smtp["from_email"]
    if sending_settings.from_name:
        from_email = f"{sending_settings.from_name} <{smtp['from_email']}>"

    email_qsl = EmailQSL.objects.create(
        qso=qso,
        card_template=card_template,
        email_template=email_template,
        recipient_email=recipient,
        sender_email=smtp["from_email"],
        subject=subject,
        body=html_body,
        delivery_status="pending",
    )

    connection = get_connection(
        host=smtp["host"],
        port=smtp["port"],
        username=smtp["username"],
        password=smtp["password"],
        use_tls=smtp["use_tls"],
    )
    message = EmailMultiAlternatives(
        subject=subject,
        body=strip_tags(html_body),
        from_email=from_email,
        to=[recipient],
        reply_to=[sending_settings.reply_to_email] if sending_settings.reply_to_email else None,
        connection=connection,
    )
    message.attach_alternative(html_body, "text/html")
    message.mixed_subtype = "related"

    from email.mime.image import MIMEImage

    image_part = MIMEImage(image_bytes, _subtype="jpeg")
    image_part.add_header("Content-ID", f"<{cid}>")
    image_part.add_header("Content-Disposition", "inline", filename=f"eqsl-{qso.call}.jpg")
    message.attach(image_part)

    try:
        message.send(fail_silently=False)
    except Exception as e:
        logger.error(f"Failed to send eQSL for QSO {qso.pk} ({qso.call}): {e}")
        email_qsl.delivery_status = "failed"
        email_qsl.error_message = str(e)
        email_qsl.save(update_fields=["delivery_status", "error_message", "updated_at"])
        return email_qsl

    logger.info(f"Sent eQSL for QSO {qso.pk} ({qso.call}) to {recipient}")
    email_qsl.delivery_status = "sent"
    email_qsl.save(update_fields=["delivery_status", "updated_at"])
    return email_qsl
