"""End-to-end UI tests with Playwright.

Run with: pytest -m ui
Requires browsers: uv run playwright install chromium
"""

import pytest
from django.utils import timezone
from PIL import Image
from playwright.sync_api import expect

from eqsl.models import QSO, CardTemplate, EmailTemplate, RenderTemplate

pytestmark = [pytest.mark.ui, pytest.mark.slow]

SIMPLE_RENDER_CODE = """
def render(card_template, qso):
    from PIL import Image
    return Image.new("RGB", (400, 300), color="blue")
"""

MINIMAL_ADIF = """
<EOH>
<QSO_DATE:8>20250101<TIME_ON:4>1200<CALL:5>EA1AA<BAND:3>40m<MODE:2>CW<FREQ:5>7.030<EOR>
<QSO_DATE:8>20250101<TIME_ON:4>1230<CALL:5>EA2BB<BAND:3>40m<MODE:2>CW<FREQ:5>7.030<EOR>
"""


@pytest.fixture(autouse=True)
def email_settings(settings):
    """Use the in-memory email backend and a configured sender."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "station@example.com"
    return settings


@pytest.fixture
def ui_data(db, tmp_path):  # noqa: ARG001
    """Cards, email template, and a couple of QSOs for browsing."""
    render_template = RenderTemplate.objects.create(
        name="ui_render", description="", python_render_code=SIMPLE_RENDER_CODE
    )
    img_path = tmp_path / "card.png"
    Image.new("RGB", (800, 600), color="white").save(img_path)
    card = CardTemplate.objects.create(name="UI Card", render_template=render_template, is_active=True)
    card.image.name = str(img_path)
    card.save()

    EmailTemplate.objects.all().delete()
    email_template = EmailTemplate.objects.create(
        name="ui-default",
        language="en",
        subject="QSL from {{ qso.my_call }}",
        body='<p>Hi {{ qso.name }}</p><img src="cid:{{ cid }}">',
        is_default=True,
    )

    qso_with_email = QSO.objects.create(
        my_call="EA4IPW",
        call="W1AW",
        name="Hiram",
        email="w1aw@arrl.org",
        frequency=14.25,
        band="20m",
        mode="SSB",
        rst_sent="59",
        rst_rcvd="59",
        tx_pwr=100,
        timestamp=timezone.now(),
        country="United States",
    )
    qso_no_email = QSO.objects.create(
        my_call="EA4IPW",
        call="DL1XYZ",
        frequency=7.03,
        band="40m",
        mode="CW",
        rst_sent="599",
        rst_rcvd="599",
        tx_pwr=100,
        timestamp=timezone.now(),
        country="Germany",
    )
    return {
        "card": card,
        "email_template": email_template,
        "qso_with_email": qso_with_email,
        "qso_no_email": qso_no_email,
    }


class TestDashboard:
    def test_dashboard_stats_and_navigation(self, live_server, page, ui_data):  # noqa: ARG002
        page.goto(live_server.url)

        expect(page).to_have_title("Dashboard - QSL Web")
        expect(page.get_by_text("Total QSOs")).to_be_visible()
        expect(page.get_by_text("Need eQSL")).to_be_visible()

        # Needs-eQSL card links into the filtered queue
        page.get_by_role("link", name="Open queue").click()
        expect(page).to_have_url(f"{live_server.url}/qsos/?eqsl_status=needs")
        expect(page.get_by_text("W1AW")).to_be_visible()


class TestSendFlow:
    def test_send_eqsl_from_qso_list(self, live_server, page, ui_data):  # noqa: ARG002
        from django.core import mail

        page.goto(f"{live_server.url}/qsos/?eqsl_status=needs")

        row = page.get_by_role("row", name="W1AW")
        row.get_by_role("button", name="Send").click()

        expect(page.get_by_text("eQSL sent to W1AW")).to_be_visible()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["w1aw@arrl.org"]

        # The row is out of the needs queue now
        expect(page.get_by_role("row", name="W1AW")).to_have_count(0)

    def test_qso_detail_send_panel(self, live_server, page, ui_data):
        qso = ui_data["qso_with_email"]
        page.goto(f"{live_server.url}/qsos/{qso.pk}/")

        expect(page.get_by_role("img", name="QSL card preview")).to_be_visible()
        page.get_by_role("button", name="Send eQSL to w1aw@arrl.org").click()

        expect(page.get_by_text("eQSL sent to W1AW")).to_be_visible()
        expect(page.get_by_role("heading", name="eQSL History")).to_be_visible()

    def test_no_email_qso_shows_qrz_lookup(self, live_server, page, ui_data):  # noqa: ARG002
        page.goto(f"{live_server.url}/qsos/")

        row = page.get_by_role("row", name="DL1XYZ")
        expect(row.get_by_role("button", name="QRZ lookup")).to_be_visible()


class TestBatchConfirm:
    def test_batch_confirm_shows_count(self, live_server, page, ui_data):  # noqa: ARG002
        page.goto(f"{live_server.url}/eqsls/send-batch/")

        expect(page.get_by_text("You are about to email 1 station")).to_be_visible()
        expect(page.get_by_role("button", name="Send 1 eQSL now")).to_be_visible()


class TestADIFImport:
    def test_upload_adif_file(self, live_server, page, ui_data, tmp_path):  # noqa: ARG002
        adif_file = tmp_path / "log.adi"
        adif_file.write_text(MINIMAL_ADIF)

        page.goto(f"{live_server.url}/import/")
        page.set_input_files("#adif_file", str(adif_file))
        page.get_by_role("button", name="Import").click()

        expect(page.get_by_text("Imported 2 of 2")).to_be_visible()
        # Redirected to the QSO list with the new contacts
        expect(page.get_by_text("EA1AA")).to_be_visible()
        expect(page.get_by_text("EA2BB")).to_be_visible()


class TestSettings:
    def test_save_settings(self, live_server, page, ui_data):  # noqa: ARG002
        page.goto(f"{live_server.url}/settings/")

        page.fill("#id_from_name", "EA4IPW QSL Service")
        page.get_by_role("button", name="Save settings").click()

        expect(page.get_by_text("Settings saved.")).to_be_visible()
        expect(page.locator("#id_from_name")).to_have_value("EA4IPW QSL Service")
