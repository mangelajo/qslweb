"""
Tests for EmailQSL model.
"""

import pytest
from django.utils import timezone

from eqsl.default_render import get_default_render_code
from eqsl.models import QSO, CardTemplate, EmailQSL, RenderTemplate


@pytest.fixture
def render_template(db):  # noqa: ARG001
    """Create a render template for testing."""
    return RenderTemplate.objects.create(
        name="test_render",
        description="Test render template",
        python_render_code=get_default_render_code()
    )


@pytest.fixture
def card_template(db, render_template):  # noqa: ARG001
    """Create a card template for testing."""
    return CardTemplate.objects.create(
        name="Test Template",
        description="A test QSL card template",
        render_template=render_template,
        is_active=True,
    )


@pytest.fixture
def qso(db):  # noqa: ARG001
    """Create a QSO for testing."""
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
class TestEmailQSL:
    """Test EmailQSL model."""

    def test_create_emailqsl(self, qso, card_template):
        """Test creating an EmailQSL record."""
        email_qsl = EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            sent_at=timezone.now(),
            recipient_email="john@example.com",
            sender_email="station@example.com",
            subject="Your QSL card from W1ABC",
            body="Thank you for the QSO! Here is your eQSL card.",
            delivery_status="sent",
        )

        assert email_qsl.qso == qso
        assert email_qsl.card_template == card_template
        assert email_qsl.recipient_email == "john@example.com"
        assert email_qsl.sender_email == "station@example.com"
        assert email_qsl.delivery_status == "sent"
        assert "K2XYZ" in str(email_qsl)

    def test_emailqsl_ordering(self, qso, card_template):
        """Test that EmailQSLs are ordered by sent_at (newest first)."""
        now = timezone.now()

        email1 = EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            sent_at=now - timezone.timedelta(hours=2),
            recipient_email="john@example.com",
            sender_email="station@example.com",
            subject="First email",
            body="First email body",
        )

        email2 = EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            sent_at=now,
            recipient_email="john@example.com",
            sender_email="station@example.com",
            subject="Second email",
            body="Second email body",
        )

        emails = list(EmailQSL.objects.all())
        assert emails[0] == email2
        assert emails[1] == email1

    def test_emailqsl_delivery_statuses(self, qso, card_template):
        """Test different delivery status values."""
        statuses = ["sent", "delivered", "failed", "bounced"]

        for status in statuses:
            email_qsl = EmailQSL.objects.create(
                qso=qso,
                card_template=card_template,
                recipient_email="test@example.com",
                sender_email="station@example.com",
                subject=f"Email with status {status}",
                body="Test body",
                delivery_status=status,
            )
            assert email_qsl.delivery_status == status

    def test_emailqsl_relationship_with_qso(self, qso, card_template):
        """Test that EmailQSL is properly related to QSO."""
        email_qsl = EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            recipient_email="john@example.com",
            sender_email="station@example.com",
            subject="Test",
            body="Test body",
        )

        # Test forward relationship
        assert email_qsl.qso == qso

        # Test reverse relationship
        assert email_qsl in qso.email_qsls.all()
        assert qso.email_qsls.count() == 1

    def test_emailqsl_cascade_delete(self, qso, card_template):
        """Test that EmailQSL is deleted when QSO is deleted."""
        email_qsl = EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            recipient_email="john@example.com",
            sender_email="station@example.com",
            subject="Test",
            body="Test body",
        )

        email_qsl_id = email_qsl.id

        qso.delete()

        # EmailQSL should be deleted due to CASCADE
        assert not EmailQSL.objects.filter(id=email_qsl_id).exists()

    def test_emailqsl_protect_card_template(self, qso, card_template):
        """Test that CardTemplate cannot be deleted if EmailQSL references it."""
        EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            recipient_email="john@example.com",
            sender_email="station@example.com",
            subject="Test",
            body="Test body",
        )

        # Attempting to delete the card template should raise ProtectedError
        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError):
            card_template.delete()

    def test_emailqsl_multiple_sends_same_qso(self, qso, card_template):
        """Test that multiple emails can be sent for the same QSO."""
        email1 = EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            sent_at=timezone.now(),
            recipient_email="john@example.com",
            sender_email="station@example.com",
            subject="First send",
            body="First send body",
        )

        email2 = EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            sent_at=timezone.now() + timezone.timedelta(days=1),
            recipient_email="john@example.com",
            sender_email="station@example.com",
            subject="Resend",
            body="Resend body",
        )

        assert qso.email_qsls.count() == 2
        assert email1 in qso.email_qsls.all()
        assert email2 in qso.email_qsls.all()

    def test_emailqsl_body_content_storage(self, qso, card_template):
        """Test that email body content is properly stored for replay."""
        long_body = """
Dear K2XYZ,

Thank you for the QSO on 20m SSB!

QSO Details:
- Date/Time: 2025-10-21 14:30 UTC
- Frequency: 14.250 MHz
- Mode: SSB
- RST: 59/57

73,
W1ABC
        """.strip()

        email_qsl = EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            recipient_email="john@example.com",
            sender_email="station@example.com",
            subject="Your QSL card from W1ABC",
            body=long_body,
        )

        # Retrieve from database and verify content is preserved
        retrieved = EmailQSL.objects.get(id=email_qsl.id)
        assert retrieved.body == long_body
        assert "QSO Details:" in retrieved.body
        assert "14.250 MHz" in retrieved.body

    def test_emailqsl_timestamps(self, qso, card_template):
        """Test that created_at and updated_at are set correctly."""
        email_qsl = EmailQSL.objects.create(
            qso=qso,
            card_template=card_template,
            recipient_email="john@example.com",
            sender_email="station@example.com",
            subject="Test",
            body="Test body",
        )

        assert email_qsl.created_at is not None
        assert email_qsl.updated_at is not None
        assert email_qsl.created_at <= email_qsl.updated_at
