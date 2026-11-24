import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestAuthRegister:
    REGISTER_URL = "/api/auth/register/"

    def test_register_success(self, api_client):
        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert "id" in data
        assert "password" not in data

        # Verify persisted user in DB
        user = User.objects.get(email="john@example.com")
        assert user.name == "John Doe"
        assert user.check_password("SecureP@ss123")

    def test_register_email_stored_lowercase(self, api_client):
        payload = {
            "name": "Jane Doe",
            "email": "JANE.DOE@EXAMPLE.COM",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "jane.doe@example.com"
        assert User.objects.filter(email="jane.doe@example.com").exists()

    def test_register_missing_name(self, api_client):
        payload = {
            "email": "test@example.com",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "name" in response.data["error"]["details"]

    def test_register_blank_name(self, api_client):
        payload = {
            "name": "   ",
            "email": "test@example.com",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"

    def test_register_missing_email(self, api_client):
        payload = {
            "name": "Test User",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "email" in response.data["error"]["details"]

    def test_register_invalid_email_format(self, api_client):
        payload = {
            "name": "Test User",
            "email": "not-an-email",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "email" in response.data["error"]["details"]

    def test_register_missing_password(self, api_client):
        payload = {
            "name": "Test User",
            "email": "test@example.com",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "password" in response.data["error"]["details"]

    def test_register_duplicate_email(self, api_client, create_user):
        create_user(email="existing@example.com", password="Password123!")
        payload = {
            "name": "Another User",
            "email": "existing@example.com",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "email" in response.data["error"]["details"]

    def test_register_duplicate_email_case_insensitive(self, api_client, create_user):
        create_user(email="existing@example.com", password="Password123!")
        payload = {
            "name": "Another User",
            "email": "EXISTING@EXAMPLE.COM",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "email" in response.data["error"]["details"]

    def test_register_password_too_short(self, api_client):
        payload = {
            "name": "Short Password",
            "email": "short@example.com",
            "password": "pass",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "password" in response.data["error"]["details"]

    def test_register_password_common(self, api_client):
        payload = {
            "name": "Common Password",
            "email": "common@example.com",
            "password": "password",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "password" in response.data["error"]["details"]

    def test_register_password_entirely_numeric(self, api_client):
        payload = {
            "name": "Numeric Password",
            "email": "numeric@example.com",
            "password": "1234567890",
        }
        response = api_client.post(self.REGISTER_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "password" in response.data["error"]["details"]


@pytest.mark.django_db
class TestAuthLogin:
    LOGIN_URL = "/api/auth/login/"

    def test_login_success(self, api_client, create_user):
        create_user(email="john@example.com", password="SecureP@ss123", name="John Doe")
        payload = {
            "email": "john@example.com",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.LOGIN_URL, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "access" in data
        assert "refresh" in data
        assert "user" in data
        assert data["user"]["email"] == "john@example.com"
        assert data["user"]["name"] == "John Doe"
        assert "id" in data["user"]

    def test_login_case_insensitive_email(self, api_client, create_user):
        create_user(email="john@example.com", password="SecureP@ss123", name="John Doe")
        payload = {
            "email": "JOHN@EXAMPLE.COM",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.LOGIN_URL, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["email"] == "john@example.com"

    def test_login_wrong_password(self, api_client, create_user):
        create_user(email="john@example.com", password="SecureP@ss123", name="John Doe")
        payload = {
            "email": "john@example.com",
            "password": "WrongPassword123!",
        }
        response = api_client.post(self.LOGIN_URL, payload, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"]["code"] == "authentication_failed"

    def test_login_nonexistent_email(self, api_client):
        payload = {
            "email": "ghost@example.com",
            "password": "SecureP@ss123",
        }
        response = api_client.post(self.LOGIN_URL, payload, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"]["code"] == "authentication_failed"

    def test_login_missing_email(self, api_client):
        payload = {"password": "SecureP@ss123"}
        response = api_client.post(self.LOGIN_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"

    def test_login_missing_password(self, api_client):
        payload = {"email": "john@example.com"}
        response = api_client.post(self.LOGIN_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"


@pytest.mark.django_db
class TestTokenRefresh:
    REFRESH_URL = "/api/auth/token/refresh/"
    LOGIN_URL = "/api/auth/login/"

    def test_token_refresh_success(self, api_client, create_user):
        create_user(email="john@example.com", password="SecureP@ss123", name="John Doe")
        login_res = api_client.post(
            self.LOGIN_URL,
            {"email": "john@example.com", "password": "SecureP@ss123"},
            format="json",
        )
        refresh_token = login_res.data["refresh"]

        refresh_res = api_client.post(
            self.REFRESH_URL,
            {"refresh": refresh_token},
            format="json",
        )
        assert refresh_res.status_code == status.HTTP_200_OK
        assert "access" in refresh_res.data

    def test_token_refresh_invalid_token(self, api_client):
        response = api_client.post(
            self.REFRESH_URL,
            {"refresh": "invalid.jwt.token"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"]["code"] == "authentication_failed"

    def test_token_refresh_missing_token(self, api_client):
        response = api_client.post(self.REFRESH_URL, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
