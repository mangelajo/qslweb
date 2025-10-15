"""
Pytest configuration for qslweb project.
"""

import pytest
from django.conf import settings


@pytest.fixture(scope="session")
def django_db_setup():
    """Configure test database."""
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "OPTIONS": {},
        "TIME_ZONE": None,
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }


@pytest.fixture
def admin_user(django_user_model):
    """Create an admin user for testing."""
    return django_user_model.objects.create_superuser(username="admin", email="admin@example.com", password="admin123")
