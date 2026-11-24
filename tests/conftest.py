import os
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connections
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture(scope="session")
def django_db_modify_db_settings():
    """Default to sqlite in-memory database for tests unless postgresql is explicitly requested."""
    if os.environ.get("DB_ENGINE") != "django.db.backends.postgresql":
        db_conf = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
            "ATOMIC_REQUESTS": False,
            "AUTOCOMMIT": True,
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False,
            "OPTIONS": {},
            "TIME_ZONE": None,
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
            "TEST": {
                "CHARSET": None,
                "COLLATION": None,
                "MIGRATE": True,
                "MIRROR": None,
                "NAME": ":memory:",
            },
        }
        settings.DATABASES["default"] = db_conf
        connections.databases["default"] = db_conf
        if hasattr(connections._connections, "default"):
            delattr(connections._connections, "default")


@pytest.fixture
def api_client():
    """Unauthenticated DRF APIClient."""
    return APIClient()


@pytest.fixture
def create_user(db):
    """Factory helper to create active users."""
    def _create_user(email="user@example.com", password="SecureP@ss123", name="Test User"):
        User = get_user_model()
        return User.objects.create_user(email=email, password=password, name=name)
    return _create_user


@pytest.fixture
def user1(create_user):
    """First test user."""
    return create_user(email="user1@example.com", password="SecureP@ss123!", name="User One")


@pytest.fixture
def user2(create_user):
    """Second test user for isolation testing."""
    return create_user(email="user2@example.com", password="SecureP@ss123!", name="User Two")


@pytest.fixture
def auth_client():
    """Helper that creates an authenticated APIClient with a valid JWT Bearer header."""
    def _auth_client(user):
        client = APIClient()
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client
    return _auth_client


@pytest.fixture
def client1(user1, auth_client):
    """Authenticated client for user1."""
    return auth_client(user1)


@pytest.fixture
def client2(user2, auth_client):
    """Authenticated client for user2."""
    return auth_client(user2)
