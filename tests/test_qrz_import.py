"""
Tests for QRZ import functionality.
"""

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from eqsl.models import QSO
from eqsl.services import QRZAPIError, QRZLogbookAPI
from tests.fixtures.qrz_responses import (
    FAIL_ADIF_RESPONSE,
    SAMPLE_ADIF_RESPONSE,
)


class TestQRZLogbookAPI:
    """Test QRZ Logbook API client."""

    def test_init_without_api_key(self):
        """Test initialization without API key raises error."""
        with patch("eqsl.services.settings") as mock_settings:
            mock_settings.QRZ_API_KEY = None
            with pytest.raises(QRZAPIError, match="QRZ API key is required"):
                QRZLogbookAPI()

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        api = QRZLogbookAPI(api_key="test_key")
        assert api.api_key == "test_key"

    @patch("eqsl.services.requests.get")
    def test_fetch_qsos_success(self, mock_get):
        """Test successful QSO fetch."""
        mock_response = MagicMock()
        mock_response.text = SAMPLE_ADIF_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        api = QRZLogbookAPI(api_key="test_key")
        qsos = api.fetch_qsos()

        assert len(qsos) == 3
        assert qsos[0]["call"] == "K2TEST"
        assert qsos[1]["call"] == "N3TEST"
        assert qsos[2]["call"] == "K4TST"

    @patch("eqsl.services.requests.get")
    def test_fetch_qsos_api_error(self, mock_get):
        """Test QSO fetch with API error."""
        mock_response = MagicMock()
        mock_response.text = FAIL_ADIF_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        api = QRZLogbookAPI(api_key="test_key")
        with pytest.raises(QRZAPIError, match="Invalid API key"):
            api.fetch_qsos()

    @patch("eqsl.services.requests.get")
    def test_fetch_qsos_network_error(self, mock_get):
        """Test QSO fetch with network error."""
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        api = QRZLogbookAPI(api_key="test_key")
        with pytest.raises(QRZAPIError, match="Failed to fetch QSOs"):
            api.fetch_qsos()

    def test_map_qso_to_model(self):
        """Test mapping QRZ QSO data to model fields."""
        qrz_qso = {
            "station_callsign": "W1TEST",
            "call": "K2TEST",
            "qso_date": "20250730",
            "time_on": "2100",
            "band": "70cm",
            "mode": "FM",
            "freq": "438.95",
            "rst_sent": "",
            "rst_rcvd": "",
            "tx_pwr": "8",
            "name": "Jane Smith",
            "email": "test@example.com",
            "country": "United States",
        }

        api = QRZLogbookAPI(api_key="test_key")
        mapped = api.map_qso_to_model(qrz_qso)

        assert mapped["my_call"] == "W1TEST"
        assert mapped["call"] == "K2TEST"
        assert mapped["band"] == "70cm"
        assert mapped["mode"] == "FM"
        assert mapped["frequency"] == 438.95
        assert mapped["rst_sent"] == ""
        assert mapped["rst_rcvd"] == ""
        assert mapped["tx_pwr"] == 8
        assert mapped["name"] == "Jane Smith"
        assert mapped["email"] == "test@example.com"
        assert mapped["country"] == "United States"


@pytest.mark.django_db
class TestImportQSOsCommand:
    """Test import_qsos management command."""

    @pytest.fixture(autouse=True)
    def clear_qsos(self):
        """Clear QSO table before each test."""
        QSO.objects.all().delete()

    @patch("eqsl.services.requests.get")
    def test_import_qsos_success(self, mock_get):
        """Test successful QSO import."""
        mock_response = MagicMock()
        mock_response.text = SAMPLE_ADIF_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        out = StringIO()
        call_command("import_qsos", "--api-key=test_key", stdout=out)

        output = out.getvalue()
        assert "Imported: 3" in output
        assert QSO.objects.count() == 3

        # Check first QSO
        qso1 = QSO.objects.get(call="K2TEST")
        assert qso1.my_call == "W1TEST"
        assert qso1.band == "70cm"
        assert qso1.mode == "FM"

    @patch("eqsl.services.requests.get")
    def test_import_qsos_dry_run(self, mock_get):
        """Test dry run mode doesn't save QSOs."""
        mock_response = MagicMock()
        mock_response.text = SAMPLE_ADIF_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        out = StringIO()
        call_command("import_qsos", "--api-key=test_key", "--dry-run", stdout=out)

        output = out.getvalue()
        assert "DRY RUN MODE" in output
        assert "Would import" in output
        assert QSO.objects.count() == 0

    @patch("eqsl.services.requests.get")
    def test_import_qsos_skip_duplicates(self, mock_get):
        """Test that duplicate QSOs are skipped."""
        # Create existing QSO matching first one in SAMPLE_ADIF_RESPONSE
        QSO.objects.create(
            my_call="W1TEST",
            call="K2TEST",
            frequency=438.95,
            band="70cm",
            mode="FM",
            rst_sent="",
            rst_rcvd="",
            tx_pwr=8,
            timestamp="2025-07-30T21:00:00Z",
        )

        mock_response = MagicMock()
        mock_response.text = SAMPLE_ADIF_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        out = StringIO()
        call_command("import_qsos", "--api-key=test_key", stdout=out)

        output = out.getvalue()
        assert "Skipped (duplicates): 1" in output
        assert "Imported: 2" in output
        assert QSO.objects.count() == 3  # 1 existing + 2 new

    @patch("eqsl.services.requests.get")
    def test_import_qsos_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_response = MagicMock()
        mock_response.text = FAIL_ADIF_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        out = StringIO()
        call_command("import_qsos", "--api-key=test_key", stdout=out)

        output = out.getvalue()
        assert "QRZ API Error" in output
