import pytest
from rest_framework import status


@pytest.fixture
def patient_payload():
    return {
        "name": "Jane Smith",
        "age": 45,
        "gender": "Female",
        "phone": "+1234567890",
        "address": "123 Main St, City",
        "medical_history": "Diabetes Type 2",
    }


@pytest.mark.django_db
class TestPatientCRUD:
    PATIENTS_URL = "/api/patients/"

    def test_create_patient_success(self, client1, user1, patient_payload):
        response = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert data["name"] == patient_payload["name"]
        assert data["age"] == patient_payload["age"]
        assert data["gender"] == patient_payload["gender"]
        assert data["phone"] == patient_payload["phone"]
        assert data["address"] == patient_payload["address"]
        assert data["medical_history"] == patient_payload["medical_history"]
        assert data["created_by"] == user1.id
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_patient_without_optional_medical_history(self, client1, patient_payload):
        del patient_payload["medical_history"]
        response = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data.get("medical_history") in ["", None]

    def test_list_patients_returns_array(self, client1, patient_payload):
        client1.post(self.PATIENTS_URL, patient_payload, format="json")
        response = client1.get(self.PATIENTS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 1
        assert response.data[0]["name"] == patient_payload["name"]

    def test_retrieve_patient_success(self, client1, patient_payload):
        created = client1.post(self.PATIENTS_URL, patient_payload, format="json").data
        patient_id = created["id"]

        response = client1.get(f"/api/patients/{patient_id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == patient_id
        assert response.data["name"] == patient_payload["name"]

    def test_retrieve_nonexistent_patient_returns_404(self, client1):
        response = client1.get("/api/patients/999999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"]["code"] == "not_found"

    def test_update_patient_put_success(self, client1, patient_payload):
        created = client1.post(self.PATIENTS_URL, patient_payload, format="json").data
        patient_id = created["id"]

        updated_payload = {
            "name": "Jane Updated",
            "age": 46,
            "gender": "Female",
            "phone": "+1987654321",
            "address": "456 New St, City",
            "medical_history": "Hypertension",
        }
        response = client1.put(f"/api/patients/{patient_id}/", updated_payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Jane Updated"
        assert response.data["age"] == 46
        assert response.data["phone"] == "+1987654321"

    def test_partial_update_patient_patch_success(self, client1, patient_payload):
        created = client1.post(self.PATIENTS_URL, patient_payload, format="json").data
        patient_id = created["id"]

        response = client1.patch(
            f"/api/patients/{patient_id}/",
            {"address": "789 Refurbished Ave"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["address"] == "789 Refurbished Ave"
        assert response.data["name"] == patient_payload["name"]

    def test_delete_patient_success(self, client1, patient_payload):
        created = client1.post(self.PATIENTS_URL, patient_payload, format="json").data
        patient_id = created["id"]

        del_res = client1.delete(f"/api/patients/{patient_id}/")
        assert del_res.status_code == status.HTTP_204_NO_CONTENT

        # Confirm 404 after deletion
        get_res = client1.get(f"/api/patients/{patient_id}/")
        assert get_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestPatientOwnershipIsolation:
    PATIENTS_URL = "/api/patients/"

    def test_user_cannot_see_other_user_patients_in_list(self, client1, client2, patient_payload):
        # user1 creates a patient
        res1 = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        assert res1.status_code == status.HTTP_201_CREATED

        # user2 list should be empty
        res2 = client2.get(self.PATIENTS_URL)
        assert res2.status_code == status.HTTP_200_OK
        assert len(res2.data) == 0

    def test_user_cannot_retrieve_other_user_patient_returns_404(self, client1, client2, patient_payload):
        res1 = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        patient_id = res1.data["id"]

        # user2 attempts to get user1's patient -> must return 404 (not 403)
        res2 = client2.get(f"/api/patients/{patient_id}/")
        assert res2.status_code == status.HTTP_404_NOT_FOUND
        assert res2.data["error"]["code"] == "not_found"

    def test_user_cannot_update_other_user_patient_returns_404(self, client1, client2, patient_payload):
        res1 = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        patient_id = res1.data["id"]

        update_data = {
            "name": "Hacked Name",
            "age": 30,
            "gender": "Male",
            "phone": "+1000000000",
            "address": "Nowhere",
            "medical_history": "None",
        }
        res2 = client2.put(f"/api/patients/{patient_id}/", update_data, format="json")
        assert res2.status_code == status.HTTP_404_NOT_FOUND
        assert res2.data["error"]["code"] == "not_found"

    def test_user_cannot_patch_other_user_patient_returns_404(self, client1, client2, patient_payload):
        res1 = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        patient_id = res1.data["id"]

        res2 = client2.patch(f"/api/patients/{patient_id}/", {"name": "Hacked"}, format="json")
        assert res2.status_code == status.HTTP_404_NOT_FOUND
        assert res2.data["error"]["code"] == "not_found"

    def test_user_cannot_delete_other_user_patient_returns_404(self, client1, client2, patient_payload):
        res1 = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        patient_id = res1.data["id"]

        res2 = client2.delete(f"/api/patients/{patient_id}/")
        assert res2.status_code == status.HTTP_404_NOT_FOUND
        assert res2.data["error"]["code"] == "not_found"

        # user1 still has the patient
        assert client1.get(f"/api/patients/{patient_id}/").status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPatientValidation:
    PATIENTS_URL = "/api/patients/"

    @pytest.mark.parametrize("missing_field", ["name", "age", "gender", "phone", "address"])
    def test_create_patient_missing_required_fields(self, client1, patient_payload, missing_field):
        del patient_payload[missing_field]
        response = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert missing_field in response.data["error"]["details"]

    def test_create_patient_invalid_age_negative(self, client1, patient_payload):
        patient_payload["age"] = -5
        response = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "age" in response.data["error"]["details"]

    def test_create_patient_invalid_age_above_150(self, client1, patient_payload):
        patient_payload["age"] = 151
        response = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "age" in response.data["error"]["details"]

    def test_create_patient_invalid_gender(self, client1, patient_payload):
        patient_payload["gender"] = "InvalidGender"
        response = client1.post(self.PATIENTS_URL, patient_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "gender" in response.data["error"]["details"]

    def test_unauthenticated_patient_requests_return_401(self, api_client, patient_payload):
        assert api_client.get(self.PATIENTS_URL).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(self.PATIENTS_URL, patient_payload, format="json").status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.get(f"{self.PATIENTS_URL}1/").status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.delete(f"{self.PATIENTS_URL}1/").status_code == status.HTTP_401_UNAUTHORIZED
