"""Tests for eQSL email composition and sending."""

import pytest
from django.core import mail
from django.utils import timezone
from PIL import Image

from eqsl.models import QSO, CardTemplate, EmailQSL, EmailTemplate, RenderTemplate, SendingSettings
from eqsl.services import EQSLSendError, compose_eqsl, language_for_qso, send_eqsl

SIMPLE_RENDER_CODE = """
def render(card_template, qso):
    from PIL import Image
    return Image.new("RGB", (400, 300), color="blue")
"""


@pytest.fixture
def render_template(db):  # noqa: ARG001
    """Create a render template that produces a simple image."""
    return RenderTemplate.objects.create(
        name="test_render", description="Test render template", python_render_code=SIMPLE_RENDER_CODE
    )


@pytest.fixture
def card_template(db, tmp_path, render_template):  # noqa: ARG001
    """Create a card template with a real image file."""
    img = Image.new("RGB", (800, 600), color="white")
    img_path = tmp_path / "test_card.png"
    img.save(img_path)

    template = CardTemplate.objects.create(
        name="Test Template",
        description="Test description",
        render_template=render_template,
        is_active=True,
    )
    template.image.name = str(img_path)
    template.save()
    return template


@pytest.fixture
def email_template(db):  # noqa: ARG001
    """Create a default English email template (removing the migration-seeded ones)."""
    EmailTemplate.objects.all().delete()
    return EmailTemplate.objects.create(
        name="test-default",
        language="en",
        subject="Digital QSL from {{ qso.my_call }} to {{ qso.call }}",
        body='<p>Hello {{ qso.name }}</p><img src="cid:{{ cid }}">',
        is_active=True,
        is_default=True,
    )


@pytest.fixture
def qso(db):  # noqa: ARG001
    """Create a QSO with an email address."""
    return QSO.objects.create(
        my_call="W1ABC",
        my_gridsquare="FN31pr",
        call="K2XYZ",
        name="John Smith",
        email="john@example.com",
        frequency=14.250,
        band="20m",
        mode="SSB",
        rst_sent="59",
        rst_rcvd="57",
        tx_pwr=100,
        timestamp=timezone.now(),
        country="United States",
    )


@pytest.mark.django_db
class TestLanguageSelection:
    """Tests for language_for_qso."""

    def test_default_english(self, qso):
        assert language_for_qso(qso) == "en"

    def test_spanish_country(self, qso):
        qso.country = "Spain"
        assert language_for_qso(qso) == "es"

    def test_french_country_case_insensitive(self, qso):
        qso.country = "FRANCE"
        assert language_for_qso(qso) == "fr"

    def test_explicit_lang_wins(self, qso):
        qso.lang = "fr"
        qso.country = "Spain"
        assert language_for_qso(qso) == "fr"

    def test_default_template_fallback_to_english(self, email_template, qso):
        qso.country = "Spain"
        template = EmailTemplate.default_for_language(language_for_qso(qso))
        assert template == email_template  # no Spanish template exists


@pytest.mark.django_db
class TestComposeEQSL:
    """Tests for compose_eqsl."""

    def test_compose_parts(self, qso, card_template, email_template):
        subject, html_body, image_bytes, cid = compose_eqsl(qso, card_template, email_template)

        assert subject == "Digital QSL from W1ABC to K2XYZ"
        assert "Hello John Smith" in html_body
        assert f'src="cid:{cid}"' in html_body
        assert image_bytes[:2] == b"\xff\xd8"  # JPEG magic bytes


@pytest.mark.django_db
class TestSendEQSL:
    """Tests for send_eqsl."""

    def test_send_success(self, qso, card_template, email_template, settings):
        settings.DEFAULT_FROM_EMAIL = "station@example.com"

        email_qsl = send_eqsl(qso, card_template=card_template, email_template=email_template)

        assert email_qsl.delivery_status == "sent"
        assert email_qsl.recipient_email == "john@example.com"
        assert email_qsl.card_template == card_template
        assert email_qsl.email_template == email_template

        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.subject == "Digital QSL from W1ABC to K2XYZ"
        assert message.to == ["john@example.com"]
        # HTML alternative present
        assert len(message.alternatives) == 1
        assert message.alternatives[0][1] == "text/html"
        # Inline image with Content-ID
        assert len(message.attachments) == 1
        image_part = message.attachments[0]
        assert image_part["Content-ID"].startswith("<eqsl-")
        assert "inline" in image_part["Content-Disposition"]

    def test_send_uses_defaults(self, qso, card_template, email_template, settings):
        settings.DEFAULT_FROM_EMAIL = "station@example.com"
        sending_settings = SendingSettings.get_settings()
        sending_settings.default_card_template = card_template
        sending_settings.save()

        email_qsl = send_eqsl(qso)

        assert email_qsl.delivery_status == "sent"
        assert email_qsl.card_template == card_template
        assert email_qsl.email_template == email_template

    def test_send_no_email(self, qso, card_template, email_template, settings, monkeypatch):
        settings.DEFAULT_FROM_EMAIL = "station@example.com"
        monkeypatch.delenv("DEBUG_EMAIL", raising=False)
        qso.email = ""
        qso.save()

        with pytest.raises(EQSLSendError, match="no email address"):
            send_eqsl(qso, card_template=card_template, email_template=email_template)

    def test_send_debug_email_override(self, qso, card_template, email_template, settings, monkeypatch):
        settings.DEFAULT_FROM_EMAIL = "station@example.com"
        monkeypatch.setenv("DEBUG_EMAIL", "debug@example.com")

        email_qsl = send_eqsl(qso, card_template=card_template, email_template=email_template)

        assert email_qsl.recipient_email == "debug@example.com"
        assert mail.outbox[0].to == ["debug@example.com"]

    def test_send_no_from_email_configured(self, qso, card_template, email_template, settings):
        settings.DEFAULT_FROM_EMAIL = ""

        with pytest.raises(EQSLSendError, match="SMTP_FROM_EMAIL"):
            send_eqsl(qso, card_template=card_template, email_template=email_template)

    def test_send_no_email_template(self, qso, card_template, settings):
        settings.DEFAULT_FROM_EMAIL = "station@example.com"
        EmailTemplate.objects.all().delete()
        with pytest.raises(EQSLSendError, match="No email template"):
            send_eqsl(qso, card_template=card_template)

    def test_send_failure_records_error(self, qso, card_template, email_template, settings, monkeypatch):
        settings.DEFAULT_FROM_EMAIL = "station@example.com"

        from django.core.mail import EmailMultiAlternatives

        def broken_send(self, fail_silently=False):  # noqa: ARG001
            raise ConnectionError("SMTP connection refused")

        monkeypatch.setattr(EmailMultiAlternatives, "send", broken_send)

        email_qsl = send_eqsl(qso, card_template=card_template, email_template=email_template)

        assert email_qsl.delivery_status == "failed"
        assert "SMTP connection refused" in email_qsl.error_message


@pytest.mark.django_db
class TestNeedsEQSLQuerySet:
    """Tests for the needs_eqsl / eqsl_sent queryset helpers."""

    def test_needs_eqsl_excludes_no_email(self, qso, card_template):  # noqa: ARG002
        QSO.objects.create(
            my_call="W1ABC",
            call="NOEMAIL",
            frequency=7.1,
            band="40m",
            mode="CW",
            rst_sent="599",
            rst_rcvd="599",
            tx_pwr=100,
            timestamp=timezone.now(),
        )

        needing = QSO.objects.needs_eqsl()
        assert qso in needing
        assert needing.count() == 1

    def test_needs_eqsl_excludes_sent(self, qso, card_template):
        EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            recipient_email=qso.email,
            sender_email="station@example.com",
            subject="test",
            body="test",
            delivery_status="sent",
        )

        assert qso not in QSO.objects.needs_eqsl()
        assert qso in QSO.objects.eqsl_sent()
        assert qso.eqsl_sent is True

    def test_failed_send_still_needs_eqsl(self, qso, card_template):
        EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            recipient_email=qso.email,
            sender_email="station@example.com",
            subject="test",
            body="test",
            delivery_status="failed",
        )

        assert qso in QSO.objects.needs_eqsl()
        assert qso.eqsl_sent is False


@pytest.mark.django_db
class TestEmailTemplateModel:
    """Tests for EmailTemplate default handling."""

    def test_single_default_per_language(self, email_template):
        other = EmailTemplate.objects.create(
            name="other",
            language="en",
            subject="s",
            body="b",
            is_default=True,
        )
        email_template.refresh_from_db()

        assert other.is_default is True
        assert email_template.is_default is False

    def test_default_for_language_fallback(self, email_template):
        assert EmailTemplate.default_for_language("es") == email_template


@pytest.mark.django_db
class TestSendViews:
    """Tests for the send/list views."""

    def test_send_view_posts_email(self, client, qso, card_template, email_template, settings):  # noqa: ARG002
        settings.DEFAULT_FROM_EMAIL = "station@example.com"
        sending_settings = SendingSettings.get_settings()
        sending_settings.default_card_template = card_template
        sending_settings.save()

        response = client.post(f"/qsos/{qso.pk}/send/")

        assert response.status_code == 302
        assert len(mail.outbox) == 1
        assert qso.email_qsls.filter(delivery_status="sent").count() == 1

    def test_qso_list_eqsl_filter(self, client, qso, card_template):
        EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            recipient_email=qso.email,
            sender_email="station@example.com",
            subject="test",
            body="test",
            delivery_status="sent",
        )

        response = client.get("/qsos/?eqsl_status=needs")
        assert response.status_code == 200
        assert qso not in response.context["qsos"]

        response = client.get("/qsos/?eqsl_status=sent")
        assert qso in response.context["qsos"]

    def test_eqsl_list_view(self, client, qso, card_template):
        EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            recipient_email=qso.email,
            sender_email="station@example.com",
            subject="test subject",
            body="test",
            delivery_status="sent",
        )

        response = client.get("/eqsls/")
        assert response.status_code == 200
        assert b"test subject" in response.content

    def test_dashboard_view(self, client, qso, card_template):
        EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            recipient_email=qso.email,
            sender_email="station@example.com",
            subject="test",
            body="test",
            delivery_status="sent",
        )

        response = client.get("/")

        assert response.status_code == 200
        assert response.context["total_qsos"] == 1
        assert response.context["needs_eqsl_count"] == 0
        assert response.context["eqsl_sent_count"] == 1
        assert qso in response.context["recent_qsos"]

    def test_card_preview_view(self, client, qso, card_template):
        response = client.get(f"/qsos/{qso.pk}/card.png?card_template={card_template.pk}")

        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"
        assert response.content[:8] == b"\x89PNG\r\n\x1a\n"
