"""Tests for QRZ.com contact enrichment."""

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from eqsl.models import QSO
from eqsl.services import QRZAPIError
from eqsl.tasks import enrich_missing_emails, enrich_qso

W1AW_DATA = {
    "call": "W1AW",
    "fname": "Hiram",
    "name": "Percy Maxim",
    "email": "w1aw@arrl.org",
    "country": "United States",
    "grid": "FN31pr",
}


@pytest.fixture
def qso_no_email(db):  # noqa: ARG001
    """Create a QSO without contact info."""
    return QSO.objects.create(
        my_call="EA4IPW",
        call="W1AW",
        frequency=14.250,
        band="20m",
        mode="SSB",
        rst_sent="59",
        rst_rcvd="59",
        tx_pwr=100,
        timestamp=timezone.now(),
    )


def mock_api(data=None, error=None):
    """Build a mock QRZAPI whose lookup returns data or raises error."""
    api = MagicMock()
    if error is not None:
        api.lookup.side_effect = error
    else:
        api.lookup.return_value = data
    return api


@pytest.mark.django_db
class TestEnrichQSO:
    """Tests for enrich_qso."""

    def test_fills_blank_fields(self, qso_no_email):
        result = enrich_qso(qso_no_email.pk, api=mock_api(W1AW_DATA))

        qso_no_email.refresh_from_db()
        assert result["found"] is True
        assert sorted(result["updated"]) == ["country", "email", "name"]
        assert qso_no_email.name == "Hiram Percy Maxim"
        assert qso_no_email.email == "w1aw@arrl.org"
        assert qso_no_email.country == "United States"
        assert qso_no_email.qrz_lookup_at is not None

    def test_does_not_overwrite_existing(self, qso_no_email):
        qso_no_email.name = "Existing Name"
        qso_no_email.email = "existing@example.com"
        qso_no_email.save()

        result = enrich_qso(qso_no_email.pk, api=mock_api(W1AW_DATA))

        qso_no_email.refresh_from_db()
        assert result["updated"] == ["country"]
        assert qso_no_email.name == "Existing Name"
        assert qso_no_email.email == "existing@example.com"

    def test_not_found_stamps_lookup(self, qso_no_email):
        result = enrich_qso(qso_no_email.pk, api=mock_api(error=QRZAPIError("No data found for callsign: W1AW")))

        qso_no_email.refresh_from_db()
        assert result["found"] is False
        assert "not found" in result["error"]
        assert qso_no_email.qrz_lookup_at is not None
        assert qso_no_email.email == ""

    def test_qrz_not_found_message_stamps_lookup(self, qso_no_email):
        result = enrich_qso(qso_no_email.pk, api=mock_api(error=QRZAPIError("QRZ lookup error: Not found: W1AW")))

        qso_no_email.refresh_from_db()
        assert result["found"] is False
        assert qso_no_email.qrz_lookup_at is not None

    def test_auth_error_propagates(self, qso_no_email):
        with pytest.raises(QRZAPIError, match="password incorrect"):
            enrich_qso(qso_no_email.pk, api=mock_api(error=QRZAPIError("Username/password incorrect")))

        qso_no_email.refresh_from_db()
        assert qso_no_email.qrz_lookup_at is None


@pytest.mark.django_db
class TestEnrichMissingEmails:
    """Tests for bulk enrichment."""

    def test_bulk_enrich(self, qso_no_email):  # noqa: ARG002
        QSO.objects.create(
            my_call="EA4IPW",
            call="HASMAIL",
            email="already@example.com",
            frequency=7.1,
            band="40m",
            mode="CW",
            rst_sent="599",
            rst_rcvd="599",
            tx_pwr=100,
            timestamp=timezone.now(),
        )

        with patch("eqsl.tasks.QRZAPI", return_value=mock_api(W1AW_DATA)):
            summary = enrich_missing_emails()

        assert summary["processed"] == 1  # only the QSO without email
        assert summary["emails_found"] == 1
        assert summary["error"] is None

    def test_skips_recently_checked(self, qso_no_email):
        qso_no_email.qrz_lookup_at = timezone.now()
        qso_no_email.save()

        with patch("eqsl.tasks.QRZAPI", return_value=mock_api(W1AW_DATA)):
            summary = enrich_missing_emails()

        assert summary["processed"] == 0
        assert summary["skipped_recent"] == 1

    def test_aborts_on_auth_error(self, qso_no_email):  # noqa: ARG002
        with patch("eqsl.tasks.QRZAPI", return_value=mock_api(error=QRZAPIError("Username/password incorrect"))):
            summary = enrich_missing_emails()

        assert summary["processed"] == 0
        assert "password incorrect" in summary["error"]


@pytest.mark.django_db
class TestEnrichViews:
    """Tests for the enrichment views."""

    def test_enrich_view(self, client, qso_no_email):
        with patch(
            "eqsl.views.enrich_qso", return_value={"call": "W1AW", "found": True, "updated": ["email"], "error": None}
        ) as mock_enrich:
            response = client.post(f"/qsos/{qso_no_email.pk}/enrich/")

        assert response.status_code == 302
        mock_enrich.assert_called_once_with(qso_no_email.pk)

    def test_enrich_missing_view(self, client, qso_no_email):  # noqa: ARG002
        summary = {"processed": 1, "emails_found": 1, "not_found": 0, "skipped_recent": 0, "error": None}
        with patch("eqsl.views.enrich_missing_emails", return_value=summary):
            response = client.post("/qsos/enrich-missing/")

        assert response.status_code == 302
        assert response.url == "/"

    def test_enrich_view_api_error(self, client, qso_no_email):
        with patch("eqsl.views.enrich_qso", side_effect=QRZAPIError("Username/password incorrect")):
            response = client.post(f"/qsos/{qso_no_email.pk}/enrich/", follow=True)

        assert response.status_code == 200
        assert b"QRZ lookup failed" in response.content
