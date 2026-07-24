"""Tests for LoTW import."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from eqsl.models import QSO, SendingSettings
from eqsl.services import LOTWAPIError, fetch_lotw_adif
from eqsl.services.importer import map_adif_record
from eqsl.tasks import sync_lotw

LOTW_ADIF = """
ARRL Logbook of the World Status Report
<PROGRAMID:4>LoTW
<APP_LoTW_NUMREC:1>2
<eoh>

<CALL:5>EA1AA
<BAND:3>20M
<MODE:3>FT8
<QSO_DATE:8>20250310
<TIME_ON:6>181500
<QSL_RCVD:1>Y
<eor>

<CALL:5>EA2BB
<BAND:3>40M
<FREQ:7>7.07400
<MODE:3>FT8
<QSO_DATE:8>20250311
<TIME_ON:6>092200
<eor>
"""

LOTW_AUTH_FAILURE = """
<html><head><title>LoTW</title></head>
<body>Username/password incorrect</body></html>
"""


def mock_response(text):
    response = MagicMock()
    response.text = text
    response.raise_for_status = MagicMock()
    return response


@pytest.mark.django_db
class TestFetchLoTW:
    """Tests for the LoTW download client."""

    def test_fetch_success(self):
        with patch("eqsl.services.lotw.requests.get", return_value=mock_response(LOTW_ADIF)) as mock_get:
            content = fetch_lotw_adif(username="ea4ipw", password="secret")

        assert "<eoh>" in content
        params = mock_get.call_args.kwargs["params"]
        assert params["login"] == "ea4ipw"
        assert params["qso_qsl"] == "no"
        assert "qso_qsorxsince" not in params

    def test_fetch_with_since(self):
        since = timezone.now() - timedelta(days=10)
        with patch("eqsl.services.lotw.requests.get", return_value=mock_response(LOTW_ADIF)) as mock_get:
            fetch_lotw_adif(username="ea4ipw", password="secret", since=since)

        assert mock_get.call_args.kwargs["params"]["qso_qsorxsince"] == since.strftime("%Y-%m-%d")

    def test_auth_failure(self):
        with (
            patch("eqsl.services.lotw.requests.get", return_value=mock_response(LOTW_AUTH_FAILURE)),
            pytest.raises(LOTWAPIError, match="rejected"),
        ):
            fetch_lotw_adif(username="ea4ipw", password="wrong")

    def test_missing_credentials(self, settings):
        settings.LOTW_USERNAME = ""
        settings.LOTW_PASSWORD = ""

        with pytest.raises(LOTWAPIError, match="not configured"):
            fetch_lotw_adif()

    def test_credentials_from_settings(self, settings):
        settings.LOTW_USERNAME = ""
        obj = SendingSettings.get_settings()
        obj.lotw_username = "dbuser"
        obj.lotw_password = "dbpass"
        obj.save()

        with patch("eqsl.services.lotw.requests.get", return_value=mock_response(LOTW_ADIF)) as mock_get:
            fetch_lotw_adif()

        assert mock_get.call_args.kwargs["params"]["login"] == "dbuser"


class TestLoTWRecordMapping:
    """LoTW records often lack FREQ — band fallback applies."""

    def test_band_fallback_frequency(self):
        record = {"CALL": "EA1AA", "BAND": "20M", "MODE": "FT8", "QSO_DATE": "20250310", "TIME_ON": "181500"}

        data = map_adif_record(record, default_my_call="EA4IPW")

        assert data["frequency"] == 14.0
        assert data["my_call"] == "EA4IPW"

    def test_unknown_band_without_freq_raises(self):
        record = {"CALL": "EA1AA", "BAND": "3cm", "MODE": "FT8", "QSO_DATE": "20250310"}

        with pytest.raises(KeyError):
            map_adif_record(record)


@pytest.mark.django_db
class TestSyncLoTW:
    """Tests for the sync task."""

    def _settings_with_creds(self):
        obj = SendingSettings.get_settings()
        obj.lotw_username = "ea4ipw"
        obj.lotw_password = "secret"
        obj.save()
        return obj

    def test_sync_imports_and_stamps(self):
        self._settings_with_creds()

        with patch("eqsl.tasks.fetch_lotw_adif", return_value=LOTW_ADIF) as mock_fetch:
            summary = sync_lotw()

        assert summary["imported"] == 2
        assert QSO.objects.filter(call="EA1AA", my_call="EA4IPW").exists()
        assert SendingSettings.get_settings().lotw_last_sync is not None
        assert mock_fetch.call_args.kwargs["since"] is None  # first sync fetches everything

    def test_incremental_sync_uses_last_sync(self):
        obj = self._settings_with_creds()
        obj.lotw_last_sync = timezone.now() - timedelta(days=5)
        obj.save()

        with patch("eqsl.tasks.fetch_lotw_adif", return_value=LOTW_ADIF) as mock_fetch:
            sync_lotw()

        since = mock_fetch.call_args.kwargs["since"]
        assert since is not None
        # One-day overlap before the recorded last sync
        assert since < timezone.now() - timedelta(days=5)

    def test_full_sync_ignores_last_sync(self):
        obj = self._settings_with_creds()
        obj.lotw_last_sync = timezone.now()
        obj.save()

        with patch("eqsl.tasks.fetch_lotw_adif", return_value=LOTW_ADIF) as mock_fetch:
            sync_lotw(full=True)

        assert mock_fetch.call_args.kwargs["since"] is None

    def test_dry_run_saves_nothing(self):
        self._settings_with_creds()

        with patch("eqsl.tasks.fetch_lotw_adif", return_value=LOTW_ADIF):
            summary = sync_lotw(dry_run=True)

        assert summary["imported"] == 2
        assert QSO.objects.count() == 0
        assert SendingSettings.get_settings().lotw_last_sync is None


@pytest.mark.django_db
class TestLoTWSyncView:
    """Tests for the sync view."""

    def test_sync_view_success(self, client):
        obj = SendingSettings.get_settings()
        obj.lotw_username = "ea4ipw"
        obj.lotw_password = "secret"
        obj.save()

        with patch("eqsl.tasks.fetch_lotw_adif", return_value=LOTW_ADIF):
            response = client.post("/import/lotw/", follow=True)

        assert response.status_code == 200
        assert b"LoTW sync: 2 imported" in response.content

    def test_sync_view_error(self, client):
        with patch("eqsl.tasks.fetch_lotw_adif", side_effect=LOTWAPIError("LoTW rejected the username/password")):
            response = client.post("/import/lotw/", follow=True)

        assert b"LoTW sync failed" in response.content
