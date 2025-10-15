"""
Tests for CardTemplate model.
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from eqsl.models import CardTemplate


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    img = Image.new("RGB", (100, 100), color="red")
    img_io = io.BytesIO()
    img.save(img_io, format="PNG")
    img_io.seek(0)
    return SimpleUploadedFile("test_card.png", img_io.read(), content_type="image/png")


@pytest.mark.django_db
class TestCardTemplate:
    """Test CardTemplate model."""

    def test_create_card_template(self, sample_image):
        """Test creating a card template."""
        template = CardTemplate.objects.create(
            name="Test Template", description="A test QSL card template", image=sample_image, is_active=True
        )

        assert template.name == "Test Template"
        assert template.description == "A test QSL card template"
        assert template.is_active is True
        assert template.image.name.startswith("card_templates/")
        assert str(template) == "Test Template"

    def test_card_template_ordering(self, sample_image):
        """Test that templates are ordered by creation date (newest first)."""
        CardTemplate.objects.create(name="Template 1", image=sample_image)
        CardTemplate.objects.create(name="Template 2", image=sample_image)

        templates = list(CardTemplate.objects.all())
        assert templates[0].name == "Template 2"
        assert templates[1].name == "Template 1"

    def test_card_template_unique_name(self, sample_image):
        """Test that template names must be unique."""
        CardTemplate.objects.create(name="Unique Template", image=sample_image)

        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            CardTemplate.objects.create(name="Unique Template", image=sample_image)
