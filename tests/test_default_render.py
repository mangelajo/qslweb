"""Tests for the default render code implementations."""

import pytest
from PIL import Image

from eqsl.default_render import create_simple_render_code, get_default_render_code
from eqsl.models import QSO, CardTemplate
from eqsl.render import execute_render_code


@pytest.fixture
def sample_qso():
    """Create a sample QSO for testing."""
    return QSO(
        call="W1AW",
        name="Hiram Percy Maxim",
        email="test@example.com",
        frequency=14.250,
        band="20m",
        mode="SSB",
        rst_sent="59",
        rst_rcvd="59",
        tx_pwr=100,
        my_call="N0CALL",
        my_gridsquare="FN31pr",
        my_rig="Icom IC-7300",
        sota_ref="W7W/LC-001",
    )


@pytest.fixture
def sample_card_template(tmp_path):
    """Create a sample card template with an image."""
    # Create a test image (1024x576 minimum size)
    img = Image.new("RGB", (1024, 576), color=(100, 150, 200))
    img_path = tmp_path / "test_card.png"
    img.save(img_path)

    template = CardTemplate(
        name="Default Template",
        description="Default QSL card template",
        language="en",
    )
    template.image.name = str(img_path)
    return template


class TestDefaultRenderCode:
    """Tests for the default render code."""

    def test_default_render_code_executes(self, sample_card_template, sample_qso):
        """Test that the default render code executes successfully."""
        sample_card_template.python_render_code = get_default_render_code()

        result = execute_render_code(sample_card_template, sample_qso)

        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"
        # Should maintain standard width
        assert result.width == 1024

    def test_default_render_code_with_pota(self, sample_card_template, sample_qso):
        """Test default render code with POTA reference instead of SOTA."""
        sample_qso.sota_ref = ""
        sample_qso.pota_ref = "K-4566"
        sample_card_template.python_render_code = get_default_render_code()

        result = execute_render_code(sample_card_template, sample_qso)

        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"

    def test_simple_render_code_executes(self, sample_card_template, sample_qso):
        """Test that the simple render code executes successfully."""
        sample_card_template.python_render_code = create_simple_render_code()

        result = execute_render_code(sample_card_template, sample_qso)

        assert isinstance(result, Image.Image)
        assert result.size == (1024, 576)  # Should maintain original size

    def test_default_render_handles_missing_optional_fields(self, sample_card_template, sample_qso):
        """Test that default render handles missing optional fields."""
        sample_qso.sota_ref = ""
        sample_qso.pota_ref = ""
        sample_qso.name = ""
        sample_card_template.python_render_code = get_default_render_code()

        result = execute_render_code(sample_card_template, sample_qso)

        assert isinstance(result, Image.Image)

    def test_default_render_validates_minimum_size(self, tmp_path, sample_qso):
        """Test that default render validates minimum image size."""
        # Create a too-small image
        img = Image.new("RGB", (500, 300), color=(100, 150, 200))
        img_path = tmp_path / "small_card.png"
        img.save(img_path)

        template = CardTemplate(
            name="Small Template",
            python_render_code=get_default_render_code(),
        )
        template.image.name = str(img_path)

        # Should raise an error for too-small image
        from eqsl.render import RenderExecutionError

        with pytest.raises(RenderExecutionError, match="resolution"):
            execute_render_code(template, sample_qso)

    def test_render_code_is_valid_python(self):
        """Test that the default render code is valid Python."""
        default_code = get_default_render_code()
        simple_code = create_simple_render_code()

        # Should compile without errors
        compile(default_code, "<string>", "exec")
        compile(simple_code, "<string>", "exec")

    def test_render_code_has_render_function(self):
        """Test that render code defines the required render function."""
        from eqsl.render import validate_render_code

        default_code = get_default_render_code()
        simple_code = create_simple_render_code()

        # Should validate successfully
        validate_render_code(default_code)
        validate_render_code(simple_code)
