"""Tests for the in-app settings page and credential fallback."""

from unittest.mock import patch

import pytest

from eqsl.models import SendingSettings
from eqsl.services import QRZAPIError
from eqsl.services.qrzlogbook import QRZLogbookAPI


@pytest.mark.django_db
class TestEffectiveCredentials:
    """Tests for DB-over-env credential resolution."""

    def test_smtp_falls_back_to_env(self, settings):
        settings.EMAIL_HOST = "env.example.com"
        settings.DEFAULT_FROM_EMAIL = "env@example.com"

        smtp = SendingSettings.get_settings().effective_smtp()

        assert smtp["host"] == "env.example.com"
        assert smtp["from_email"] == "env@example.com"

    def test_db_values_override_env(self, settings):
        settings.EMAIL_HOST = "env.example.com"
        obj = SendingSettings.get_settings()
        obj.smtp_host = "db.example.com"
        obj.smtp_from_email = "db@example.com"
        obj.save()

        smtp = obj.effective_smtp()

        assert smtp["host"] == "db.example.com"
        assert smtp["from_email"] == "db@example.com"

    def test_qrz_db_override(self, settings):
        settings.QRZ_USERNAME = "envuser"
        obj = SendingSettings.get_settings()
        obj.qrz_username = "dbuser"
        obj.save()

        assert obj.effective_qrz()["username"] == "dbuser"
        assert obj.effective_qrz()["password"] == settings.QRZ_PASSWORD

    def test_logbook_api_uses_db_key(self, settings):
        settings.QRZ_API_KEY = ""
        obj = SendingSettings.get_settings()
        obj.qrz_api_key = "db-key-123"
        obj.save()

        api = QRZLogbookAPI()

        assert api.api_key == "db-key-123"


@pytest.mark.django_db
class TestSettingsViews:
    """Tests for the settings page and connection tests."""

    def test_settings_page_renders(self, client):
        response = client.get("/settings/")

        assert response.status_code == 200
        assert b"SMTP Email" in response.content
        assert b"QRZ.com" in response.content

    def test_settings_save(self, client):
        response = client.post(
            "/settings/",
            {
                "from_name": "EA4IPW",
                "reply_to_email": "",
                "default_card_template": "",
                "batch_size": 20,
                "delay_between_emails_s": 3,
                "smtp_host": "smtp.example.com",
                "smtp_port": 465,
                "smtp_username": "user",
                "smtp_password": "secret",
                "smtp_from_email": "me@example.com",
                "qrz_username": "quser",
                "qrz_password": "qpass",
                "qrz_api_key": "qkey",
            },
        )

        assert response.status_code == 302
        obj = SendingSettings.get_settings()
        assert obj.from_name == "EA4IPW"
        assert obj.batch_size == 20
        assert obj.smtp_host == "smtp.example.com"
        assert obj.smtp_use_tls is False  # unchecked checkbox
        assert obj.qrz_api_key == "qkey"

    def test_test_email_sends(self, client, settings):
        settings.DEFAULT_FROM_EMAIL = "me@example.com"
        settings.EMAIL_HOST = "smtp.example.com"

        from django.core import mail

        response = client.post("/settings/test-email/", {"recipient": "check@example.com"}, follow=True)

        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["check@example.com"]
        assert b"Test email sent" in response.content

    def test_test_email_without_sender(self, client, settings):
        settings.DEFAULT_FROM_EMAIL = ""

        response = client.post("/settings/test-email/", follow=True)

        assert b"No sender address configured" in response.content

    def test_test_qrz_success(self, client):
        with patch("eqsl.views.QRZAPI") as mock_api:
            mock_api.return_value.get_session_info.return_value = {"count": "42"}
            response = client.post("/settings/test-qrz/", follow=True)

        assert b"QRZ login OK" in response.content
        assert b"42 lookups" in response.content

    def test_test_qrz_failure(self, client):
        with patch("eqsl.views.QRZAPI", side_effect=QRZAPIError("Username/password incorrect")):
            response = client.post("/settings/test-qrz/", follow=True)

        assert b"QRZ login failed" in response.content
