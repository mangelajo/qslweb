"""Tests for batch eQSL sending."""

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from eqsl.models import QSO, SendingSettings
from eqsl.services import EQSLSendError
from eqsl.tasks import send_batch


def make_qso(call, email="op@example.com"):
    return QSO.objects.create(
        my_call="EA4IPW",
        call=call,
        email=email,
        frequency=14.25,
        band="20m",
        mode="SSB",
        rst_sent="59",
        rst_rcvd="59",
        tx_pwr=100,
        timestamp=timezone.now(),
    )


def mock_sent_eqsl(status="sent", error=""):
    email_qsl = MagicMock()
    email_qsl.delivery_status = status
    email_qsl.error_message = error
    return email_qsl


@pytest.mark.django_db
class TestSendBatch:
    """Tests for the send_batch task."""

    def test_sends_queue_up_to_batch_size(self):
        for i in range(5):
            make_qso(f"CALL{i}")
        settings_obj = SendingSettings.get_settings()
        settings_obj.batch_size = 3
        settings_obj.delay_between_emails_s = 0
        settings_obj.save()

        with patch("eqsl.tasks.send_eqsl", return_value=mock_sent_eqsl()) as mock_send:
            summary = send_batch()

        assert summary == {"attempted": 3, "sent": 3, "failed": 0, "errors": []}
        assert mock_send.call_count == 3

    def test_sleeps_between_emails(self):
        make_qso("CALL1")
        make_qso("CALL2")
        settings_obj = SendingSettings.get_settings()
        settings_obj.delay_between_emails_s = 7
        settings_obj.save()

        with (
            patch("eqsl.tasks.send_eqsl", return_value=mock_sent_eqsl()),
            patch("eqsl.tasks.time.sleep") as mock_sleep,
        ):
            send_batch()

        # One pause for two emails (no pause before the first)
        mock_sleep.assert_called_once_with(7)

    def test_records_failures_and_continues(self):
        make_qso("GOOD1")
        make_qso("BAD2")
        make_qso("GOOD3")
        settings_obj = SendingSettings.get_settings()
        settings_obj.delay_between_emails_s = 0
        settings_obj.save()

        def flaky_send(qso):
            if qso.call == "BAD2":
                raise EQSLSendError("render exploded")
            return mock_sent_eqsl()

        with patch("eqsl.tasks.send_eqsl", side_effect=flaky_send):
            summary = send_batch()

        assert summary["attempted"] == 3
        assert summary["sent"] == 2
        assert summary["failed"] == 1
        assert "BAD2: render exploded" in summary["errors"]

    def test_explicit_qso_ids(self):
        qso1 = make_qso("CALL1")
        make_qso("CALL2")

        with patch("eqsl.tasks.send_eqsl", return_value=mock_sent_eqsl()) as mock_send:
            summary = send_batch(qso_ids=[qso1.pk])

        assert summary["attempted"] == 1
        assert mock_send.call_args[0][0] == qso1

    def test_empty_queue(self):
        with patch("eqsl.tasks.send_eqsl") as mock_send:
            summary = send_batch()

        assert summary == {"attempted": 0, "sent": 0, "failed": 0, "errors": []}
        mock_send.assert_not_called()


@pytest.mark.django_db
class TestBatchSendView:
    """Tests for the batch confirmation/launch view."""

    def test_confirm_page_shows_counts(self, client):
        for i in range(4):
            make_qso(f"CALL{i}")
        settings_obj = SendingSettings.get_settings()
        settings_obj.batch_size = 3
        settings_obj.save()

        response = client.get("/eqsls/send-batch/")

        assert response.status_code == 200
        assert response.context["queue_count"] == 4
        assert response.context["will_send"] == 3
        assert response.context["remaining"] == 1
        assert b"You are about to email 3" in response.content

    def test_post_enqueues_task(self, client):
        make_qso("CALL1")

        with patch("django_q.tasks.async_task") as mock_async:
            response = client.post("/eqsls/send-batch/")

        assert response.status_code == 302
        mock_async.assert_called_once_with("eqsl.tasks.send_batch")

    def test_post_falls_back_to_sync_without_broker(self, client):
        make_qso("CALL1")
        summary = {"attempted": 1, "sent": 1, "failed": 0, "errors": []}

        with (
            patch("django_q.tasks.async_task", side_effect=ConnectionError("redis down")),
            patch("eqsl.views.send_batch", return_value=summary) as mock_batch,
        ):
            response = client.post("/eqsls/send-batch/", follow=True)

        assert response.status_code == 200
        mock_batch.assert_called_once()
        assert b"1 sent" in response.content

    def test_post_empty_queue_redirects_home(self, client):
        response = client.post("/eqsls/send-batch/")

        assert response.status_code == 302
        assert response.url == "/"
