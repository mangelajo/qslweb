"""
Pytest configuration for qslweb project.
"""

import pytest


@pytest.fixture
def admin_user(django_user_model):
    """Create an admin user for testing."""
    return django_user_model.objects.create_superuser(username="admin", email="admin@example.com", password="admin123")
