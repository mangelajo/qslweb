"""Tests for the safe render code execution module."""

import pytest
from PIL import Image

from eqsl.models import QSO, CardTemplate, RenderTemplate
from eqsl.render import (
    RenderCompilationError,
    RenderExecutionError,
    RenderTimeoutError,
    RenderValidationError,
    execute_render_code,
    validate_render_code,
)


@pytest.fixture
def sample_qso():
    """Create a sample QSO for testing."""
    return QSO(
        call="W1AW",
        name="Test Operator",
        email="test@example.com",
        frequency=14.250,
        band="20m",
        mode="SSB",
        rst_sent="59",
        rst_rcvd="59",
        tx_pwr=100,
        my_call="N0CALL",
        my_gridsquare="FN31pr",
    )


@pytest.fixture
def sample_render_template():
    """Create a sample render template for testing."""
    return RenderTemplate(
        name="test_render",
        description="Test render template",
        python_render_code="def render(card_template, qso):\n    return card_template.image",
    )


@pytest.fixture
def sample_card_template(tmp_path, sample_render_template):
    """Create a sample card template for testing."""
    # Create a simple test image
    img = Image.new("RGB", (800, 600), color="white")
    img_path = tmp_path / "test_card.png"
    img.save(img_path)

    template = CardTemplate(
        name="Test Template",
        description="Test description",
        language="en",
        render_template=sample_render_template,
    )
    template.image.name = str(img_path)
    return template


class TestValidateRenderCode:
    """Tests for validate_render_code function."""

    def test_validate_empty_code(self):
        """Test that empty code raises validation error."""
        with pytest.raises(RenderValidationError, match="cannot be empty"):
            validate_render_code("")

    def test_validate_whitespace_only(self):
        """Test that whitespace-only code raises validation error."""
        with pytest.raises(RenderValidationError, match="cannot be empty"):
            validate_render_code("   \n  \n  ")

    def test_validate_missing_render_function(self):
        """Test that code without render function raises validation error."""
        code = """
def some_other_function():
    pass
"""
        with pytest.raises(RenderValidationError, match="must define a render"):
            validate_render_code(code)

    def test_validate_render_not_callable(self):
        """Test that non-callable render raises validation error."""
        code = """
render = "not a function"
"""
        with pytest.raises(RenderValidationError, match="must be a callable"):
            validate_render_code(code)

    def test_validate_syntax_error(self):
        """Test that code with syntax errors raises validation error."""
        code = """
def render(card_template, qso)
    return None  # Missing colon
"""
        with pytest.raises(RenderValidationError, match="compilation errors"):
            validate_render_code(code)

    def test_validate_restricted_import(self):
        """Test that restricted imports are caught during validation."""
        code = """
import os

def render(card_template, qso):
    return None
"""
        # RestrictedPython should catch the import statement
        with pytest.raises(RenderValidationError):
            validate_render_code(code)

    def test_validate_valid_simple_code(self):
        """Test that valid simple code passes validation."""
        code = """
def render(card_template, qso):
    from PIL import Image
    img = Image.new('RGB', (800, 600), color='white')
    return img
"""
        # Should not raise any exception
        validate_render_code(code)

    def test_validate_valid_complex_code(self):
        """Test that valid complex code passes validation."""
        code = """
def render(card_template, qso):
    from PIL import Image, ImageDraw, ImageFont

    # Create base image
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)

    # Draw some text
    draw.text((100, 100), f"To: {qso.call}", fill='black')

    return img
"""
        # Should not raise any exception
        validate_render_code(code)


class TestExecuteRenderCode:
    """Tests for execute_render_code function."""

    def test_execute_empty_code(self, sample_card_template, sample_qso):
        """Test that empty code raises validation error."""
        sample_card_template.render_template.python_render_code = ""
        with pytest.raises(RenderValidationError, match="No render"):
            execute_render_code(sample_card_template, sample_qso)

    def test_execute_valid_simple_render(self, sample_card_template, sample_qso):
        """Test executing valid simple render code."""
        sample_card_template.render_template.python_render_code = """
def render(card_template, qso):
    from PIL import Image
    img = Image.new('RGB', (800, 600), color='white')
    return img
"""
        result = execute_render_code(sample_card_template, sample_qso)
        assert isinstance(result, Image.Image)
        assert result.size == (800, 600)

    def test_execute_render_with_qso_data(self, sample_card_template, sample_qso):
        """Test executing render code that uses QSO data."""
        sample_card_template.render_template.python_render_code = """
def render(card_template, qso):
    from PIL import Image, ImageDraw

    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)

    # Use QSO data
    text = f"QSO with {qso.call} on {qso.band} {qso.mode}"
    draw.text((100, 100), text, fill='black')

    return img
"""
        result = execute_render_code(sample_card_template, sample_qso)
        assert isinstance(result, Image.Image)

    def test_execute_missing_render_function(self, sample_card_template, sample_qso):
        """Test that code without render function raises error."""
        sample_card_template.render_template.python_render_code = """
def some_other_function():
    pass
"""
        with pytest.raises(RenderValidationError, match="render.*not defined"):
            execute_render_code(sample_card_template, sample_qso)

    def test_execute_render_returns_non_image(self, sample_card_template, sample_qso):
        """Test that render function returning non-Image raises error."""
        sample_card_template.render_template.python_render_code = """
def render(card_template, qso):
    return "not an image"
"""
        with pytest.raises(RenderExecutionError, match="must return a PIL Image"):
            execute_render_code(sample_card_template, sample_qso)

    def test_execute_render_with_exception(self, sample_card_template, sample_qso):
        """Test that exceptions in render function are caught."""
        sample_card_template.render_template.python_render_code = """
def render(card_template, qso):
    raise ValueError("Something went wrong")
"""
        with pytest.raises(RenderExecutionError, match="ValueError"):
            execute_render_code(sample_card_template, sample_qso)

    def test_execute_render_restricted_import(self, sample_card_template, sample_qso):
        """Test that restricted imports are blocked during execution."""
        sample_card_template.render_template.python_render_code = """
import os

def render(card_template, qso):
    from PIL import Image
    return Image.new('RGB', (800, 600), color='white')
"""
        with pytest.raises((RenderCompilationError, RenderExecutionError)):
            execute_render_code(sample_card_template, sample_qso)

    def test_execute_render_restricted_file_access(self, sample_card_template, sample_qso):
        """Test that file system access is restricted."""
        sample_card_template.render_template.python_render_code = """
def render(card_template, qso):
    with open('/etc/passwd', 'r') as f:
        data = f.read()

    from PIL import Image
    return Image.new('RGB', (800, 600), color='white')
"""
        # Should fail at execution due to restricted builtins
        with pytest.raises((RenderCompilationError, RenderExecutionError)):
            execute_render_code(sample_card_template, sample_qso)

    @pytest.mark.slow
    def test_execute_render_timeout(self, sample_card_template, sample_qso):
        """Test that long-running render code times out."""
        sample_card_template.render_template.python_render_code = """
def render(card_template, qso):
    # Infinite loop
    while True:
        pass
"""
        with pytest.raises(RenderTimeoutError, match="exceeded.*seconds"):
            execute_render_code(sample_card_template, sample_qso)

    def test_execute_render_syntax_error(self, sample_card_template, sample_qso):
        """Test that syntax errors are caught during compilation."""
        sample_card_template.render_template.python_render_code = """
def render(card_template, qso)
    return None
"""
        with pytest.raises(RenderCompilationError, match="compilation errors"):
            execute_render_code(sample_card_template, sample_qso)


class TestResourceLimits:
    """Tests for resource limit enforcement."""

    def test_memory_intensive_operation(self, sample_card_template, sample_qso):
        """Test that memory-intensive operations are handled."""
        sample_card_template.render_template.python_render_code = """
def render(card_template, qso):
    from PIL import Image

    # Try to create a very large image
    try:
        img = Image.new('RGB', (10000, 10000), color='white')
    except MemoryError:
        # If memory limit works, create smaller image
        img = Image.new('RGB', (800, 600), color='white')

    return img
"""
        result = execute_render_code(sample_card_template, sample_qso)
        assert isinstance(result, Image.Image)


@pytest.mark.django_db
class TestAdminValidation:
    """Tests for admin form validation."""

    def test_render_template_form_validates_code(self):
        """Test that RenderTemplateAdminForm validates render code on save."""
        from eqsl.admin import RenderTemplateAdminForm

        # Valid code should pass
        valid_code = """
def render(card_template, qso):
    from PIL import Image
    return Image.new('RGB', (800, 600), color='white')
"""
        form = RenderTemplateAdminForm(
            data={
                "name": "test_render",
                "description": "Test render template",
                "python_render_code": valid_code,
            }
        )
        assert form.is_valid(), form.errors

    def test_render_template_form_rejects_invalid_code(self):
        """Test that RenderTemplateAdminForm rejects invalid render code."""
        from eqsl.admin import RenderTemplateAdminForm

        # Invalid code (missing render function)
        invalid_code = """
def some_other_function():
    pass
"""
        form = RenderTemplateAdminForm(
            data={
                "name": "test_render",
                "description": "Test render template",
                "python_render_code": invalid_code,
            }
        )
        assert not form.is_valid()
        assert "python_render_code" in form.errors

    def test_render_template_form_requires_code(self):
        """Test that RenderTemplateAdminForm requires render code."""
        from eqsl.admin import RenderTemplateAdminForm

        form = RenderTemplateAdminForm(
            data={
                "name": "test_render",
                "description": "Test render template",
                "python_render_code": "",
            }
        )
        assert not form.is_valid()
        assert "python_render_code" in form.errors
