"""
Tests for QSO model.
"""

import pytest
from django.utils import timezone

from eqsl.models import QSO


@pytest.mark.django_db
class TestQSO:
    """Test QSO model."""

    def test_create_qso(self):
        """Test creating a QSO record."""
        qso = QSO.objects.create(
            my_call="W1ABC",
            my_gridsquare="FN31pr",
            my_rig="Yaesu FT-891",
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
            lang="en",
        )

        assert qso.my_call == "W1ABC"
        assert qso.call == "K2XYZ"
        assert qso.frequency == 14.250
        assert qso.band == "20m"
        assert qso.mode == "SSB"
        assert qso.tx_pwr == 100
        assert "K2XYZ" in str(qso)
        assert "20m" in str(qso)

    def test_qso_ordering(self):
        """Test that QSOs are ordered by timestamp (newest first)."""
        now = timezone.now()
        QSO.objects.create(
            my_call="W1ABC",
            call="K2XYZ",
            frequency=14.250,
            band="20m",
            mode="SSB",
            rst_sent="59",
            rst_rcvd="57",
            tx_pwr=100,
            timestamp=now - timezone.timedelta(hours=2),
        )
        QSO.objects.create(
            my_call="W1ABC",
            call="K3DEF",
            frequency=7.125,
            band="40m",
            mode="CW",
            rst_sent="599",
            rst_rcvd="599",
            tx_pwr=100,
            timestamp=now,
        )

        qsos = list(QSO.objects.all())
        assert qsos[0].call == "K3DEF"
        assert qsos[1].call == "K2XYZ"

    def test_qso_with_optional_fields(self):
        """Test creating a QSO with optional fields."""
        qso = QSO.objects.create(
            my_call="W1ABC",
            call="K2XYZ",
            frequency=14.250,
            band="20m",
            mode="SSB",
            rst_sent="59",
            rst_rcvd="57",
            tx_pwr=100,
            sota_ref="W1/GC-001",
            pota_ref="K-1234",
        )

        assert qso.sota_ref == "W1/GC-001"
        assert qso.pota_ref == "K-1234"

    def test_qso_minimal_fields(self):
        """Test creating a QSO with only required fields."""
        qso = QSO.objects.create(
            my_call="W1ABC",
            call="K2XYZ",
            frequency=14.250,
            band="20m",
            mode="SSB",
            rst_sent="59",
            rst_rcvd="57",
            tx_pwr=100,
        )

        assert qso.my_call == "W1ABC"
        assert qso.call == "K2XYZ"
        assert qso.my_gridsquare == ""
        assert qso.email == ""
        assert qso.lang == "en"  # default value
