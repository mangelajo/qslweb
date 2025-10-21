"""
Tests for admin interface.
"""

import pytest
from django.contrib.admin.sites import site
from django.urls import reverse

from eqsl.models import QSO, CardTemplate


@pytest.mark.django_db
class TestQSOAdmin:
    """Test QSO admin interface."""

    def test_qso_admin_registered(self):
        """Test that QSO model is registered in admin."""
        assert QSO in site._registry

    def test_qso_list_display(self, admin_client):
        """Test QSO list view in admin."""
        # Create test QSO
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
            email="john@example.com",
        )

        url = reverse("admin:eqsl_qso_changelist")
        response = admin_client.get(url)

        assert response.status_code == 200
        assert "K2XYZ" in str(response.content)
        assert "20m" in str(response.content)

    def test_qso_admin_search(self, admin_client):
        """Test QSO admin search functionality."""
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

        url = reverse("admin:eqsl_qso_changelist")
        response = admin_client.get(url, {"q": "K2XYZ"})

        assert response.status_code == 200
        assert "K2XYZ" in str(response.content)
        assert "K3DEF" not in str(response.content)

    def test_qso_admin_pagination(self, admin_client):
        """Test QSO admin pagination."""
        # Create multiple QSOs
        for i in range(55):
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

        url = reverse("admin:eqsl_qso_changelist")
        response = admin_client.get(url)

        assert response.status_code == 200
        # Check pagination is working (list_per_page = 50)
        assert "page" in str(response.content).lower() or "next" in str(response.content).lower()


@pytest.mark.django_db
class TestCardTemplateAdmin:
    """Test CardTemplate admin interface."""

    def test_cardtemplate_admin_registered(self):
        """Test that CardTemplate model is registered in admin."""
        assert CardTemplate in site._registry

    def test_cardtemplate_list_display(self, admin_client, sample_card):
        """Test CardTemplate list view in admin."""
        url = reverse("admin:eqsl_cardtemplate_changelist")
        response = admin_client.get(url)

        assert response.status_code == 200
        assert sample_card.name in str(response.content)


@pytest.fixture
def admin_client(django_user_model, client):
    """Create an admin user and return authenticated client."""
    admin_user = django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="password123"
    )
    client.force_login(admin_user)
    return client


@pytest.fixture
def sample_card():
    """Create a sample card template."""
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    from eqsl.default_render import get_default_render_code
    from eqsl.models import RenderTemplate

    # Create render template
    render_template = RenderTemplate.objects.create(
        name="test_render_admin",
        description="Test render template for admin",
        python_render_code=get_default_render_code(),
    )

    img = Image.new("RGB", (100, 100), color="blue")
    img_io = io.BytesIO()
    img.save(img_io, format="PNG")
    img_io.seek(0)
    image = SimpleUploadedFile("test.png", img_io.read(), content_type="image/png")

    return CardTemplate.objects.create(
        name="Test Card", description="A test card", image=image, render_template=render_template, is_active=True
    )
