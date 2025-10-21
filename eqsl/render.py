"""Safe execution of card template render code with sandboxing and resource limits."""

import contextlib
import io
import resource
import signal
from collections.abc import Callable
from functools import wraps
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import (
    guarded_iter_unpack_sequence,
    guarded_unpack_sequence,
    safer_getattr,
)


class RenderError(Exception):
    """Base exception for render code execution errors."""

    pass


class RenderCompilationError(RenderError):
    """Raised when render code fails to compile."""

    pass


class RenderExecutionError(RenderError):
    """Raised when render code fails during execution."""

    pass


class RenderTimeoutError(RenderError):
    """Raised when render code execution exceeds time limit."""

    pass


class RenderValidationError(RenderError):
    """Raised when render code fails validation."""

    pass


def with_resource_limits(max_memory_mb: int = 200, max_time_seconds: int = 10) -> Callable:
    """
    Decorator to limit memory and execution time for render code.

    Args:
        max_memory_mb: Maximum memory in megabytes
        max_time_seconds: Maximum execution time in seconds

    Returns:
        Decorated function with resource limits
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Store original limits to restore later
            original_memory_limit = resource.getrlimit(resource.RLIMIT_AS)

            # Set memory limit (virtual memory)
            with contextlib.suppress(ValueError):
                # Some systems don't support setting memory limits
                resource.setrlimit(
                    resource.RLIMIT_AS, (max_memory_mb * 1024 * 1024, max_memory_mb * 1024 * 1024)
                )

            # Try to set CPU time limit with signal (only works in main thread)
            signal_available = False
            old_handler = None
            try:
                def timeout_handler(_signum: int, _frame: Any) -> None:
                    raise RenderTimeoutError(f"Render execution exceeded {max_time_seconds} seconds")

                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(max_time_seconds)
                signal_available = True
            except (ValueError, AttributeError):
                # signal.signal() raises ValueError if not in main thread
                # AttributeError if signal.SIGALRM is not available on the platform
                pass

            try:
                result = func(*args, **kwargs)
            except MemoryError as e:
                raise RenderExecutionError(f"Render code exceeded memory limit: {e}") from e
            finally:
                # Cancel alarm and restore if signal was set
                if signal_available:
                    signal.alarm(0)
                    if old_handler is not None:
                        signal.signal(signal.SIGALRM, old_handler)

                # Restore original memory limit
                with contextlib.suppress(ValueError):
                    resource.setrlimit(resource.RLIMIT_AS, original_memory_limit)

            return result

        return wrapper

    return decorator


def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    """
    Safe import function that only allows whitelisted modules.

    Args:
        name: Module name to import
        globals: Global namespace (unused)
        locals: Local namespace (unused)
        fromlist: List of names to import from module
        level: Relative import level

    Returns:
        Imported module

    Raises:
        ImportError: If module is not in whitelist
    """
    # Whitelist of allowed modules
    allowed_modules = {
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "io",
        "datetime",
        "time",
    }

    # Check if the module or its parent is allowed
    if name not in allowed_modules and not any(name.startswith(m + ".") for m in allowed_modules):
        raise ImportError(f"Import of module '{name}' is not allowed")

    # Use the real __import__ for allowed modules
    return __import__(name, globals, locals, fromlist, level)


def safe_getitem(obj, key):
    """
    Safe getitem function for RestrictedPython.

    Args:
        obj: Object to get item from
        key: Key/index to access

    Returns:
        The item at the specified key/index
    """
    return obj[key]


class ImageFileProxy:
    """Proxy for Django ImageField that provides safe access to image path in sandbox."""

    def __init__(self, image_field):
        self._name = image_field.name
        # Pre-compute the full path outside the sandbox
        try:
            self._path = image_field.path
        except (ValueError, NotImplementedError, Exception):
            # Fallback for test fixtures or storages without path support
            # Also catches SuspiciousFileOperation from Django when path is outside MEDIA_ROOT
            self._path = image_field.name

    @property
    def name(self):
        """Return the full filesystem path (not the relative name)."""
        return self._path

    @property
    def path(self):
        """Return the full filesystem path."""
        return self._path


class CardTemplateProxy:
    """Proxy for CardTemplate that provides safe access to attributes in sandbox."""

    def __init__(self, card_template):
        self.image = ImageFileProxy(card_template.image)
        self.name = card_template.name
        self.description = card_template.description
        self.language = card_template.language
        # Store reference to original for any other attributes that might be needed
        self._original = card_template

    def __getattr__(self, name):
        """Fallback to original object for any other attributes."""
        return getattr(self._original, name)


def get_restricted_globals() -> dict:
    """
    Get the restricted global namespace for render code execution.

    Returns:
        Dictionary of allowed globals including PIL and safe built-ins
    """
    # Create a copy of safe_globals and add our safe_import to __builtins__
    restricted_builtins = safe_globals["__builtins__"].copy()
    restricted_builtins["__import__"] = safe_import

    return {
        "__builtins__": restricted_builtins,
        "_getiter_": iter,
        "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
        "_getattr_": safer_getattr,
        "_getitem_": safe_getitem,
        "_unpack_sequence_": guarded_unpack_sequence,
        # PIL/Pillow modules - pre-imported for convenience
        "Image": Image,
        "ImageDraw": ImageDraw,
        "ImageFont": ImageFont,
        "io": io,
    }


def validate_render_code(render_code: str) -> None:
    """
    Validate render code by compiling it and checking for the render function.

    Args:
        render_code: Python code string to validate

    Raises:
        RenderValidationError: If code is invalid or missing render function
    """
    if not render_code or not render_code.strip():
        raise RenderValidationError("Render code cannot be empty")

    # Compile with RestrictedPython
    try:
        byte_code = compile_restricted(render_code, filename="<render_validation>", mode="exec")
    except SyntaxError as e:
        raise RenderValidationError(f"Code compilation errors: {e}") from e

    # Execute to check for render function
    restricted_globals = get_restricted_globals()
    restricted_locals: dict = {}

    try:
        exec(byte_code, restricted_globals, restricted_locals)
    except Exception as e:
        raise RenderValidationError(f"Error during code validation: {type(e).__name__}: {e}") from e

    # Check that render function exists
    if "render" not in restricted_locals:
        raise RenderValidationError("Code must define a render(card_template, qso) function")

    # Check that it's callable
    if not callable(restricted_locals["render"]):
        raise RenderValidationError("render must be a callable function")


@with_resource_limits(max_memory_mb=200, max_time_seconds=10)
def execute_render_code(card_template: Any, qso: Any) -> Image.Image:
    """
    Execute the card template's render code in a restricted, resource-limited environment.

    Args:
        card_template: CardTemplate instance with python_render_code
        qso: QSO instance to render

    Returns:
        PIL Image object

    Raises:
        RenderError: If code compilation, execution, or validation fails
        RenderTimeoutError: If execution exceeds time limit
        RenderExecutionError: If execution fails or exceeds memory limit
    """
    if not card_template.render_template or not card_template.render_template.python_render_code:
        raise RenderValidationError("No render template or render code defined in card template")

    python_render_code = card_template.render_template.python_render_code

    # Compile with RestrictedPython
    try:
        byte_code = compile_restricted(
            python_render_code, filename="<card_template_render>", mode="exec"
        )
    except SyntaxError as e:
        raise RenderCompilationError(f"Code compilation errors: {e}") from e

    # Get restricted global namespace
    restricted_globals = get_restricted_globals()
    restricted_locals: dict = {}

    # Execute the code to define the render function
    try:
        exec(byte_code, restricted_globals, restricted_locals)
    except Exception as e:
        raise RenderExecutionError(f"Error executing render code: {type(e).__name__}: {e}") from e

    # Verify render function exists
    if "render" not in restricted_locals:
        raise RenderValidationError("render() function not defined in python_render_code")

    render_func = restricted_locals["render"]

    # Wrap card_template in proxy to provide safe access to image paths
    card_template_proxy = CardTemplateProxy(card_template)

    # Call the render function
    try:
        result = render_func(card_template_proxy, qso)
    except RenderTimeoutError:
        # Re-raise timeout errors without wrapping
        raise
    except Exception as e:
        raise RenderExecutionError(f"Error in render function: {type(e).__name__}: {e}") from e

    # Validate result is a PIL Image
    if not isinstance(result, Image.Image):
        raise RenderExecutionError(
            f"render() must return a PIL Image, got {type(result).__name__}"
        )

    return result
