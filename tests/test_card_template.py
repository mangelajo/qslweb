"""
Tests for CardTemplate model.
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from eqsl.default_render import get_default_render_code
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

    def test_card_template_default_render_code(self, sample_image):
        """Test that python_render_code defaults to get_default_render_code() when not specified."""
        template = CardTemplate.objects.create(
            name="Default Render Template",
            image=sample_image
        )

        # Should have the default render code
        assert template.python_render_code == get_default_render_code()
        assert "def render(card_template, qso):" in template.python_render_code

    def test_card_template_custom_render_code(self, sample_image):
        """Test that python_render_code can be overridden with custom code."""
        custom_code = "def render(card_template, qso):\n    return card_template.image"
        template = CardTemplate.objects.create(
            name="Custom Render Template",
            image=sample_image,
            python_render_code=custom_code
        )

        # Should have the custom code, not the default
        assert template.python_render_code == custom_code
        assert template.python_render_code != get_default_render_code()
