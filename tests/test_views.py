"""
Tests for QSO views.
"""

import pytest
from django.urls import reverse

from eqsl.models import QSO


@pytest.mark.django_db
class TestQSOListView:
    """Test QSO list view."""

    @pytest.fixture(autouse=True)
    def clear_qsos(self):
        """Clear QSO table before each test."""
        QSO.objects.all().delete()

    def test_qso_list_view(self, client):
        """Test QSO list view displays QSOs."""
        # Create test QSOs
        QSO.objects.create(
            my_call="W1ABC",
            call="K2XYZ",
            frequency=14.250,
            band="20m",
            mode="SSB",
            rst_sent="59",
            rst_rcvd="57",
            tx_pwr=100,
            name="John Doe",
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
            name="Jane Smith",
        )

        url = reverse("eqsl:qso_list")
        response = client.get(url)

        assert response.status_code == 200
        assert "K2XYZ" in response.content.decode()
        assert "K3DEF" in response.content.decode()
        assert "John Doe" in response.content.decode()

    def test_qso_list_search(self, client):
        """Test QSO list search functionality."""
        QSO.objects.create(
            my_call="W1ABC",
            call="K2XYZ",
            frequency=14.250,
            band="20m",
            mode="SSB",
            rst_sent="59",
            rst_rcvd="57",
            tx_pwr=100,
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
        )

        url = reverse("eqsl:qso_list")
        response = client.get(url, {"q": "K2XYZ"})

        assert response.status_code == 200
        content = response.content.decode()
        assert "K2XYZ" in content
        assert "K3DEF" not in content

    def test_qso_list_filter_by_band(self, client):
        """Test QSO list filtering by band."""
        QSO.objects.create(
            my_call="W1ABC",
            call="K2XYZ",
            frequency=14.250,
            band="20m",
            mode="SSB",
            rst_sent="59",
            rst_rcvd="57",
            tx_pwr=100,
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
        )

        url = reverse("eqsl:qso_list")
        response = client.get(url, {"band": "20m"})

        assert response.status_code == 200
        content = response.content.decode()
        assert "K2XYZ" in content
        assert "K3DEF" not in content

    def test_qso_list_filter_by_mode(self, client):
        """Test QSO list filtering by mode."""
        QSO.objects.create(
            my_call="W1ABC",
            call="K2XYZ",
            frequency=14.250,
            band="20m",
            mode="SSB",
            rst_sent="59",
            rst_rcvd="57",
            tx_pwr=100,
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
        )

        url = reverse("eqsl:qso_list")
        response = client.get(url, {"mode": "CW"})

        assert response.status_code == 200
        content = response.content.decode()
        assert "K3DEF" in content
        assert "K2XYZ" not in content

    def test_qso_list_pagination(self, client):
        """Test QSO list pagination."""
        # Create 30 QSOs (more than the 25 per page limit)
        for i in range(30):
            QSO.objects.create(
                my_call="W1ABC",
                call=f"K{i}XYZ",
                frequency=14.250,
                band="20m",
                mode="SSB",
                rst_sent="59",
                rst_rcvd="57",
                tx_pwr=100,
            )

        url = reverse("eqsl:qso_list")
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        # Check for pagination controls
        assert "Page" in content
        assert "Next" in content or "next" in content

    def test_qso_list_empty(self, client):
        """Test QSO list view with no QSOs."""
        url = reverse("eqsl:qso_list")
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "No QSOs found" in content


@pytest.mark.django_db
class TestQSODetailView:
    """Test QSO detail view."""

    @pytest.fixture(autouse=True)
    def clear_qsos(self):
        """Clear QSO table before each test."""
        QSO.objects.all().delete()

    def test_qso_detail_view(self, client):
        """Test QSO detail view displays QSO information."""
        qso = QSO.objects.create(
            my_call="W1ABC",
            my_gridsquare="FN31pr",
            my_rig="Yaesu FT-891",
            call="K2XYZ",
            name="John Doe",
            email="john@example.com",
            frequency=14.250,
            band="20m",
            mode="SSB",
            rst_sent="59",
            rst_rcvd="57",
            tx_pwr=100,
            country="United States",
            sota_ref="W1/GC-001",
            pota_ref="K-1234",
        )

        url = reverse("eqsl:qso_detail", kwargs={"pk": qso.pk})
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "K2XYZ" in content
        assert "John Doe" in content
        assert "john@example.com" in content
        assert "14.25" in content  # Frequency displayed
        assert "20m" in content
        assert "SSB" in content
        assert "Yaesu FT-891" in content
        assert "W1/GC-001" in content
        assert "K-1234" in content

    def test_qso_detail_not_found(self, client):
        """Test QSO detail view with non-existent QSO."""
        url = reverse("eqsl:qso_detail", kwargs={"pk": 9999})
        response = client.get(url)

        assert response.status_code == 404
