"""
Tests for CardTemplate and RenderTemplate models.
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from eqsl.default_render import get_default_render_code
from eqsl.models import CardTemplate, RenderTemplate


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    img = Image.new("RGB", (100, 100), color="red")
    img_io = io.BytesIO()
    img.save(img_io, format="PNG")
    img_io.seek(0)
    return SimpleUploadedFile("test_card.png", img_io.read(), content_type="image/png")


@pytest.fixture
def default_render_template():
    """Create a default render template for testing."""
    return RenderTemplate.objects.create(
        name="test_default", description="Test default render template", python_render_code=get_default_render_code()
    )


@pytest.mark.django_db
class TestRenderTemplate:
    """Test RenderTemplate model."""

    def test_create_render_template(self):
        """Test creating a render template."""
        render_template = RenderTemplate.objects.create(
            name="test_template", description="Test render template", python_render_code=get_default_render_code()
        )

        assert render_template.name == "test_template"
        assert render_template.description == "Test render template"
        assert "def render(card_template, qso):" in render_template.python_render_code
        assert str(render_template) == "test_template"

    def test_render_template_unique_name(self):
        """Test that render template names must be unique."""
        RenderTemplate.objects.create(name="unique_template", python_render_code=get_default_render_code())

        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            RenderTemplate.objects.create(name="unique_template", python_render_code=get_default_render_code())


@pytest.mark.django_db
class TestCardTemplate:
    """Test CardTemplate model."""

    def test_create_card_template(self, sample_image, default_render_template):
        """Test creating a card template."""
        template = CardTemplate.objects.create(
            name="Test Template",
            description="A test QSL card template",
            image=sample_image,
            render_template=default_render_template,
            is_active=True,
        )

        assert template.name == "Test Template"
        assert template.description == "A test QSL card template"
        assert template.is_active is True
        assert template.render_template == default_render_template
        assert template.image.name.startswith("card_templates/")
        assert str(template) == "Test Template"

    def test_card_template_ordering(self, sample_image, default_render_template):
        """Test that templates are ordered by creation date (newest first)."""
        CardTemplate.objects.create(name="Template 1", image=sample_image, render_template=default_render_template)
        CardTemplate.objects.create(name="Template 2", image=sample_image, render_template=default_render_template)

        templates = list(CardTemplate.objects.all())
        assert templates[0].name == "Template 2"
        assert templates[1].name == "Template 1"

    def test_card_template_unique_name(self, sample_image, default_render_template):
        """Test that template names must be unique."""
        CardTemplate.objects.create(name="Unique Template", image=sample_image, render_template=default_render_template)

        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            CardTemplate.objects.create(
                name="Unique Template", image=sample_image, render_template=default_render_template
            )

    def test_card_template_with_render_template(self, sample_image):
        """Test that CardTemplate links to RenderTemplate correctly."""
        render_template = RenderTemplate.objects.create(
            name="custom_render",
            description="Custom render template",
            python_render_code="def render(card_template, qso):\n    return card_template.image",
        )

        template = CardTemplate.objects.create(
            name="Template with Custom Render", image=sample_image, render_template=render_template
        )

        # Should have the custom render template
        assert template.render_template == render_template
        assert (
            template.render_template.python_render_code
            == "def render(card_template, qso):\n    return card_template.image"
        )
