import pytest
from rest_framework import status


@pytest.mark.django_db
class TestErrorEnvelopeShape:
    """
    Verifies that all API error responses conform to the uniform envelope:
    {
      "error": {
        "code": "<error_code>",
        "message": "<human-readable message>",
        "details": { ... }
      }
    }
    across 400, 401, 403, 404, and 405.
    """

    def _assert_envelope(self, data, expected_code):
        assert "error" in data, f"Missing 'error' key in response data: {data}"
        err = data["error"]
        assert isinstance(err, dict), f"'error' must be an object: {err}"
        assert "code" in err, f"Missing 'code' in error object: {err}"
        assert "message" in err, f"Missing 'message' in error object: {err}"
        assert "details" in err, f"Missing 'details' in error object: {err}"
        assert err["code"] == expected_code, f"Expected code '{expected_code}', got '{err['code']}'"
        assert isinstance(err["message"], str) and len(err["message"]) > 0
        assert isinstance(err["details"], dict)

    def test_400_validation_error_envelope(self, client1):
        # Empty payload to patients create endpoint triggers validation error
        response = client1.post("/api/patients/", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self._assert_envelope(response.data, "validation_error")
        # details should contain field error details
        assert len(response.data["error"]["details"]) > 0

    def test_400_duplicate_mapping_error_envelope(self, client1):
        # Create a patient and doctor
        p_res = client1.post(
            "/api/patients/",
            {"name": "P1", "age": 30, "gender": "Male", "phone": "123", "address": "Addr"},
            format="json",
        )
        d_res = client1.post(
            "/api/doctors/",
            {"name": "D1", "specialization": "General", "email": "d1@err.com", "phone": "123", "years_of_experience": 5},
            format="json",
        )
        payload = {"patient_id": p_res.data["id"], "doctor_id": d_res.data["id"]}
        res1 = client1.post("/api/mappings/", payload, format="json")
        assert res1.status_code == status.HTTP_201_CREATED

        # Second assignment should trigger duplicate_mapping
        res2 = client1.post("/api/mappings/", payload, format="json")
        assert res2.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]
        self._assert_envelope(res2.data, "duplicate_mapping")

    def test_401_authentication_failed_envelope_missing_token(self, api_client):
        response = api_client.get("/api/patients/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        self._assert_envelope(response.data, "authentication_failed")

    def test_401_authentication_failed_envelope_invalid_token(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.payload")
        response = api_client.get("/api/patients/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        self._assert_envelope(response.data, "authentication_failed")

    def test_401_authentication_failed_envelope_bad_credentials(self, api_client):
        response = api_client.post(
            "/api/auth/login/",
            {"email": "nobody@example.com", "password": "WrongPassword123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        self._assert_envelope(response.data, "authentication_failed")

    def test_403_permission_denied_envelope(self, client1, client2):
        # User 1 creates doctor
        doc = client1.post(
            "/api/doctors/",
            {"name": "Dr. Owner", "specialization": "Ortho", "email": "ortho@err.com", "phone": "123", "years_of_experience": 8},
            format="json",
        ).data

        # User 2 tries to delete user 1's doctor -> 403
        response = client2.delete(f"/api/doctors/{doc['id']}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_envelope(response.data, "permission_denied")

    def test_404_not_found_envelope_nonexistent_resource(self, client1):
        response = client1.get("/api/patients/999999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self._assert_envelope(response.data, "not_found")

    def test_404_not_found_envelope_other_user_resource(self, client1, client2):
        # User 1 creates patient
        patient = client1.post(
            "/api/patients/",
            {"name": "Private Patient", "age": 28, "gender": "Female", "phone": "123", "address": "Addr"},
            format="json",
        ).data

        # User 2 tries to access user 1's patient -> 404
        response = client2.get(f"/api/patients/{patient['id']}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self._assert_envelope(response.data, "not_found")

    def test_405_method_not_allowed_envelope(self, client1):
        # PUT on /api/mappings/ is not allowed (only GET and POST)
        response = client1.put("/api/mappings/", {}, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        self._assert_envelope(response.data, "method_not_allowed")
