"""Tests for ADIF file import."""

from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from eqsl.models import QSO
from eqsl.services import ADIFImportError, import_adif_content, map_adif_record

FIXTURE = Path(__file__).parent / "fixtures" / "sample.adi"

MINIMAL_ADIF = """
<ADIF_VER:5>3.1.4
<EOH>
<QSO_DATE:8>20250101<TIME_ON:4>1200<CALL:5>EA1AA<BAND:3>40m<MODE:2>CW<FREQ:5>7.030<EOR>
<QSO_DATE:8>20250101<TIME_ON:4>1230<CALL:5>EA2BB<BAND:3>40m<MODE:2>CW<FREQ:5>7.030<EOR>
"""

BROKEN_RECORD_ADIF = """
<EOH>
<QSO_DATE:8>20250101<TIME_ON:4>1200<CALL:5>EA1AA<BAND:3>40m<MODE:2>CW<FREQ:5>7.030<EOR>
<QSO_DATE:8>20250101<TIME_ON:4>1300<CALL:5>EA3CC<MODE:2>CW<FREQ:5>7.030<EOR>
"""


class TestMapADIFRecord:
    """Tests for ADIF record mapping (no DB needed)."""

    def test_maps_full_record(self):
        record = {
            "QSO_DATE": "20241012",
            "TIME_ON": "2230",
            "TIME_OFF": "2235",
            "CALL": "TEST",
            "BAND": "20m",
            "MODE": "SSB",
            "FREQ": "14.230",
            "RST_SENT": "59",
            "RST_RCVD": "57",
            "TX_PWR": "100",
            "OPERATOR": "W6BSD",
            "NAME": "Test OM",
            "EMAIL": "test@example.com",
            "COUNTRY": "USA",
        }

        data = map_adif_record(record)

        assert data["call"] == "TEST"
        assert data["my_call"] == "W6BSD"
        assert data["frequency"] == 14.230
        assert data["email"] == "test@example.com"
        assert data["timestamp"].strftime("%Y%m%d %H%M") == "20241012 2230"  # TIME_ON preferred (matches QRZ import)
        assert data["timestamp"].tzinfo is not None

    def test_defaults(self):
        record = {"QSO_DATE": "20250101", "CALL": "X1X", "BAND": "20m", "MODE": "FT8", "FREQ": "14.074"}

        data = map_adif_record(record, default_my_call="EA4IPW")

        assert data["my_call"] == "EA4IPW"
        assert data["rst_sent"] == "599"
        assert data["tx_pwr"] == 100
        assert data["timestamp"].strftime("%H%M") == "0000"

    def test_missing_required_field_raises(self):
        with pytest.raises(KeyError):
            map_adif_record({"QSO_DATE": "20250101", "CALL": "X1X", "MODE": "CW", "FREQ": "7.0"})  # no BAND


@pytest.mark.django_db
class TestImportADIFContent:
    """Tests for full-content import."""

    def test_imports_records(self):
        summary = import_adif_content(MINIMAL_ADIF)

        assert summary == {"total": 2, "imported": 2, "skipped": 0, "errors": []}
        assert QSO.objects.count() == 2
        assert QSO.objects.filter(call="EA1AA").exists()

    def test_reimport_skips_duplicates(self):
        import_adif_content(MINIMAL_ADIF)
        summary = import_adif_content(MINIMAL_ADIF)

        assert summary["imported"] == 0
        assert summary["skipped"] == 2
        assert QSO.objects.count() == 2

    def test_dry_run_saves_nothing(self):
        summary = import_adif_content(MINIMAL_ADIF, dry_run=True)

        assert summary["imported"] == 2
        assert QSO.objects.count() == 0

    def test_broken_record_reported_others_imported(self):
        summary = import_adif_content(BROKEN_RECORD_ADIF)

        assert summary["imported"] == 1
        assert len(summary["errors"]) == 1
        assert "EA3CC" in summary["errors"][0]

    def test_unparseable_content_raises(self):
        with pytest.raises(ADIFImportError):
            import_adif_content("\x00\x01 not adif at all")

    def test_fixture_file(self):
        summary = import_adif_content(FIXTURE.read_text())

        assert summary["imported"] == 1
        qso = QSO.objects.get(call="TEST")
        assert qso.my_call == "W6BSD"
        assert qso.email == "test@example.com"


@pytest.mark.django_db
class TestImportADIFCommand:
    """Tests for the import_adif management command."""

    def test_command_imports(self):
        out = StringIO()
        call_command("import_adif", str(FIXTURE), stdout=out)

        assert "Imported: 1" in out.getvalue()
        assert QSO.objects.filter(call="TEST").exists()

    def test_command_dry_run(self):
        out = StringIO()
        call_command("import_adif", str(FIXTURE), "--dry-run", stdout=out)

        assert QSO.objects.count() == 0

    def test_command_missing_file(self):
        with pytest.raises(CommandError, match="File not found"):
            call_command("import_adif", "/nonexistent/file.adi")


@pytest.mark.django_db
class TestADIFImportView:
    """Tests for the upload view."""

    def test_get_page(self, client):
        response = client.get("/import/")

        assert response.status_code == 200
        assert b"ADIF file" in response.content

    def test_upload_imports(self, client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile("log.adi", MINIMAL_ADIF.encode(), content_type="text/plain")
        response = client.post("/import/", {"adif_file": upload}, follow=True)

        assert response.status_code == 200
        assert b"Imported 2 of 2" in response.content
        assert QSO.objects.count() == 2

    def test_upload_dry_run(self, client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile("log.adi", MINIMAL_ADIF.encode(), content_type="text/plain")
        response = client.post("/import/", {"adif_file": upload, "dry_run": "1"}, follow=True)

        assert b"Dry run" in response.content
        assert QSO.objects.count() == 0

    def test_upload_without_file(self, client):
        response = client.post("/import/", follow=True)

        assert b"Choose an ADIF file" in response.content
