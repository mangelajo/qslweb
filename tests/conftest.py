"""
Pytest configuration for qslweb project.
"""

import os

import pytest

# Allow Django ORM calls while Playwright's event loop is running (UI tests)
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture
def admin_user(django_user_model):
    """Create an admin user for testing."""
    return django_user_model.objects.create_superuser(username="admin", email="admin@example.com", password="admin123")
