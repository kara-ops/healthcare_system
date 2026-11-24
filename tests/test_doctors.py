import pytest
from rest_framework import status


@pytest.fixture
def doctor_payload():
    return {
        "name": "Dr. Alice",
        "specialization": "Cardiology",
        "email": "alice@hospital.com",
        "phone": "+9876543210",
        "years_of_experience": 15,
    }


@pytest.mark.django_db
class TestDoctorCRUD:
    DOCTORS_URL = "/api/doctors/"

    def test_create_doctor_success(self, client1, user1, doctor_payload):
        response = client1.post(self.DOCTORS_URL, doctor_payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert data["name"] == doctor_payload["name"]
        assert data["specialization"] == doctor_payload["specialization"]
        assert data["email"] == doctor_payload["email"]
        assert data["phone"] == doctor_payload["phone"]
        assert data["years_of_experience"] == doctor_payload["years_of_experience"]
        assert data["created_by"] == user1.id
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_retrieve_doctor_success(self, client1, doctor_payload):
        created = client1.post(self.DOCTORS_URL, doctor_payload, format="json").data
        doc_id = created["id"]

        response = client1.get(f"/api/doctors/{doc_id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == doc_id
        assert response.data["name"] == doctor_payload["name"]

    def test_retrieve_nonexistent_doctor_returns_404(self, client1):
        response = client1.get("/api/doctors/999999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"]["code"] == "not_found"

    def test_update_doctor_put_by_creator_success(self, client1, doctor_payload):
        created = client1.post(self.DOCTORS_URL, doctor_payload, format="json").data
        doc_id = created["id"]

        updated_payload = {
            "name": "Dr. Alice Smith",
            "specialization": "Neurology",
            "email": "alice.smith@hospital.com",
            "phone": "+9876543211",
            "years_of_experience": 16,
        }
        response = client1.put(f"/api/doctors/{doc_id}/", updated_payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Dr. Alice Smith"
        assert response.data["specialization"] == "Neurology"
        assert response.data["years_of_experience"] == 16

    def test_update_doctor_patch_by_creator_success(self, client1, doctor_payload):
        created = client1.post(self.DOCTORS_URL, doctor_payload, format="json").data
        doc_id = created["id"]

        response = client1.patch(
            f"/api/doctors/{doc_id}/",
            {"years_of_experience": 20},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["years_of_experience"] == 20
        assert response.data["name"] == doctor_payload["name"]

    def test_delete_doctor_by_creator_success(self, client1, doctor_payload):
        created = client1.post(self.DOCTORS_URL, doctor_payload, format="json").data
        doc_id = created["id"]

        del_res = client1.delete(f"/api/doctors/{doc_id}/")
        assert del_res.status_code == status.HTTP_204_NO_CONTENT

        get_res = client1.get(f"/api/doctors/{doc_id}/")
        assert get_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestDoctorSharedDirectoryAndPermissions:
    DOCTORS_URL = "/api/doctors/"

    def test_doctors_directory_is_shared_across_users(self, client1, client2, doctor_payload):
        # user1 creates a doctor
        created = client1.post(self.DOCTORS_URL, doctor_payload, format="json").data
        doc_id = created["id"]

        # user2 lists doctors and sees doctor created by user1
        list_res = client2.get(self.DOCTORS_URL)
        assert list_res.status_code == status.HTTP_200_OK
        assert isinstance(list_res.data, list)
        doctor_ids = [d["id"] for d in list_res.data]
        assert doc_id in doctor_ids

        # user2 can retrieve user1's doctor
        get_res = client2.get(f"/api/doctors/{doc_id}/")
        assert get_res.status_code == status.HTTP_200_OK
        assert get_res.data["id"] == doc_id
        assert get_res.data["name"] == doctor_payload["name"]

    def test_non_creator_cannot_put_update_doctor_returns_403(self, client1, client2, doctor_payload):
        created = client1.post(self.DOCTORS_URL, doctor_payload, format="json").data
        doc_id = created["id"]

        update_payload = {
            "name": "Hacked Doctor",
            "specialization": "None",
            "email": "hacked@hospital.com",
            "phone": "+1111111111",
            "years_of_experience": 1,
        }
        res2 = client2.put(f"/api/doctors/{doc_id}/", update_payload, format="json")
        assert res2.status_code == status.HTTP_403_FORBIDDEN
        assert res2.data["error"]["code"] == "permission_denied"

    def test_non_creator_cannot_patch_doctor_returns_403(self, client1, client2, doctor_payload):
        created = client1.post(self.DOCTORS_URL, doctor_payload, format="json").data
        doc_id = created["id"]

        res2 = client2.patch(f"/api/doctors/{doc_id}/", {"name": "Hacked"}, format="json")
        assert res2.status_code == status.HTTP_403_FORBIDDEN
        assert res2.data["error"]["code"] == "permission_denied"

    def test_non_creator_cannot_delete_doctor_returns_403(self, client1, client2, doctor_payload):
        created = client1.post(self.DOCTORS_URL, doctor_payload, format="json").data
        doc_id = created["id"]

        res2 = client2.delete(f"/api/doctors/{doc_id}/")
        assert res2.status_code == status.HTTP_403_FORBIDDEN
        assert res2.data["error"]["code"] == "permission_denied"

        # Verify doctor still exists
        assert client1.get(f"/api/doctors/{doc_id}/").status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestDoctorValidation:
    DOCTORS_URL = "/api/doctors/"

    @pytest.mark.parametrize("missing_field", ["name", "specialization", "email", "phone"])
    def test_create_doctor_missing_required_fields(self, client1, doctor_payload, missing_field):
        del doctor_payload[missing_field]
        response = client1.post(self.DOCTORS_URL, doctor_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert missing_field in response.data["error"]["details"]

    def test_create_doctor_omitted_years_of_experience_defaults_to_zero(self, client1, doctor_payload):
        del doctor_payload["years_of_experience"]
        response = client1.post(self.DOCTORS_URL, doctor_payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["years_of_experience"] == 0

    def test_create_doctor_duplicate_email_rejected(self, client1, doctor_payload):
        res1 = client1.post(self.DOCTORS_URL, doctor_payload, format="json")
        assert res1.status_code == status.HTTP_201_CREATED

        res2 = client1.post(self.DOCTORS_URL, doctor_payload, format="json")
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert res2.data["error"]["code"] == "validation_error"
        assert "email" in res2.data["error"]["details"]

    def test_create_doctor_duplicate_email_case_insensitive(self, client1, doctor_payload):
        res1 = client1.post(self.DOCTORS_URL, doctor_payload, format="json")
        assert res1.status_code == status.HTTP_201_CREATED

        doctor_payload["email"] = doctor_payload["email"].upper()
        res2 = client1.post(self.DOCTORS_URL, doctor_payload, format="json")
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert res2.data["error"]["code"] == "validation_error"

    def test_create_doctor_negative_years_of_experience(self, client1, doctor_payload):
        doctor_payload["years_of_experience"] = -1
        response = client1.post(self.DOCTORS_URL, doctor_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"
        assert "years_of_experience" in response.data["error"]["details"]

    def test_unauthenticated_doctor_requests_return_401(self, api_client, doctor_payload):
        assert api_client.get(self.DOCTORS_URL).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(self.DOCTORS_URL, doctor_payload, format="json").status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.get(f"{self.DOCTORS_URL}1/").status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.put(f"{self.DOCTORS_URL}1/", doctor_payload, format="json").status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.delete(f"{self.DOCTORS_URL}1/").status_code == status.HTTP_401_UNAUTHORIZED
