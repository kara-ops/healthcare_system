import pytest
from rest_framework import status


@pytest.fixture
def make_patient(client1):
    def _make(client=client1, name="Jane Patient"):
        payload = {
            "name": name,
            "age": 35,
            "gender": "Female",
            "phone": "+1234567890",
            "address": "123 Test Road",
            "medical_history": "None",
        }
        res = client.post("/api/patients/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        return res.data
    return _make


@pytest.fixture
def make_doctor(client1):
    def _make(client=client1, name="Dr. Bob", email="drbob@example.com"):
        payload = {
            "name": name,
            "specialization": "Pediatrics",
            "email": email,
            "phone": "+9876543210",
            "years_of_experience": 10,
        }
        res = client.post("/api/doctors/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        return res.data
    return _make


@pytest.mark.django_db
class TestMappingCreateAndValidation:
    MAPPINGS_URL = "/api/mappings/"

    def test_assign_doctor_to_patient_success(self, client1, make_patient, make_doctor):
        patient = make_patient()
        doctor = make_doctor()

        payload = {"patient_id": patient["id"], "doctor_id": doctor["id"]}
        response = client1.post(self.MAPPINGS_URL, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert "id" in data
        assert data["patient_id"] == patient["id"]
        assert data["doctor_id"] == doctor["id"]
        assert data["patient_name"] == patient["name"]
        assert data["doctor_name"] == doctor["name"]
        assert "assigned_at" in data

    def test_assign_doctor_to_nonexistent_patient_returns_404(self, client1, make_doctor):
        doctor = make_doctor()
        payload = {"patient_id": 999999, "doctor_id": doctor["id"]}
        response = client1.post(self.MAPPINGS_URL, payload, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"]["code"] == "not_found"

    def test_assign_doctor_to_other_user_patient_returns_404(self, client1, client2, make_patient, make_doctor):
        # user1 creates patient
        patient = make_patient(client=client1)
        # doctor can be created by anyone
        doctor = make_doctor(client=client2, email="doc2@example.com")

        # user2 attempts to assign doctor to user1's patient -> must return 404
        payload = {"patient_id": patient["id"], "doctor_id": doctor["id"]}
        response = client2.post(self.MAPPINGS_URL, payload, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"]["code"] == "not_found"

    def test_assign_nonexistent_doctor_returns_400(self, client1, make_patient):
        patient = make_patient()
        payload = {"patient_id": patient["id"], "doctor_id": 999999}
        response = client1.post(self.MAPPINGS_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "validation_error"

    def test_duplicate_mapping_returns_400_duplicate_mapping(self, client1, make_patient, make_doctor):
        patient = make_patient()
        doctor = make_doctor()
        payload = {"patient_id": patient["id"], "doctor_id": doctor["id"]}

        res1 = client1.post(self.MAPPINGS_URL, payload, format="json")
        assert res1.status_code == status.HTTP_201_CREATED

        # Duplicate assignment
        res2 = client1.post(self.MAPPINGS_URL, payload, format="json")
        assert res2.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]
        assert res2.data["error"]["code"] == "duplicate_mapping"

    def test_mapping_missing_required_fields(self, client1, make_patient, make_doctor):
        patient = make_patient()
        doctor = make_doctor()

        # Missing doctor_id
        res1 = client1.post(self.MAPPINGS_URL, {"patient_id": patient["id"]}, format="json")
        assert res1.status_code == status.HTTP_400_BAD_REQUEST
        assert res1.data["error"]["code"] == "validation_error"
        assert "doctor_id" in res1.data["error"]["details"]

        # Missing patient_id
        res2 = client1.post(self.MAPPINGS_URL, {"doctor_id": doctor["id"]}, format="json")
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert res2.data["error"]["code"] == "validation_error"
        assert "patient_id" in res2.data["error"]["details"]


@pytest.mark.django_db
class TestMappingDualSemanticsAndListing:
    MAPPINGS_URL = "/api/mappings/"

    def test_list_mappings_scoped_to_user(self, client1, client2, make_patient, make_doctor):
        p1 = make_patient(client=client1, name="User1 Patient")
        d1 = make_doctor(client=client1, email="doc1@example.com")
        client1.post(self.MAPPINGS_URL, {"patient_id": p1["id"], "doctor_id": d1["id"]}, format="json")

        p2 = make_patient(client=client2, name="User2 Patient")
        d2 = make_doctor(client=client2, email="doc2@example.com")
        client2.post(self.MAPPINGS_URL, {"patient_id": p2["id"], "doctor_id": d2["id"]}, format="json")

        # user1 list
        res1 = client1.get(self.MAPPINGS_URL)
        assert res1.status_code == status.HTTP_200_OK
        assert len(res1.data) == 1
        assert res1.data[0]["patient_id"] == p1["id"]

        # user2 list
        res2 = client2.get(self.MAPPINGS_URL)
        assert res2.status_code == status.HTTP_200_OK
        assert len(res2.data) == 1
        assert res2.data[0]["patient_id"] == p2["id"]

    def test_get_mappings_by_patient_id(self, client1, make_patient, make_doctor):
        p = make_patient()
        d1 = make_doctor(email="doc1@example.com", name="Doc One")
        d2 = make_doctor(email="doc2@example.com", name="Doc Two")

        client1.post(self.MAPPINGS_URL, {"patient_id": p["id"], "doctor_id": d1["id"]}, format="json")
        client1.post(self.MAPPINGS_URL, {"patient_id": p["id"], "doctor_id": d2["id"]}, format="json")

        response = client1.get(f"{self.MAPPINGS_URL}{p['id']}/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 2
        returned_doctor_ids = {m["doctor_id"] for m in response.data}
        assert returned_doctor_ids == {d1["id"], d2["id"]}

    def test_get_mappings_for_other_user_patient_returns_404(self, client1, client2, make_patient):
        p1 = make_patient(client=client1)
        res = client2.get(f"{self.MAPPINGS_URL}{p1['id']}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert res.data["error"]["code"] == "not_found"

    def test_delete_mapping_by_mapping_id(self, client1, make_patient, make_doctor):
        p = make_patient()
        d = make_doctor()
        created = client1.post(self.MAPPINGS_URL, {"patient_id": p["id"], "doctor_id": d["id"]}, format="json").data
        mapping_id = created["id"]

        # DELETE using mapping_id
        del_res = client1.delete(f"{self.MAPPINGS_URL}{mapping_id}/")
        assert del_res.status_code == status.HTTP_204_NO_CONTENT

        # Confirm mapping is gone
        list_res = client1.get(self.MAPPINGS_URL)
        assert len(list_res.data) == 0

    def test_delete_mapping_for_other_user_patient_returns_404(self, client1, client2, make_patient, make_doctor):
        p1 = make_patient(client=client1)
        d1 = make_doctor(client=client1)
        created = client1.post(self.MAPPINGS_URL, {"patient_id": p1["id"], "doctor_id": d1["id"]}, format="json").data
        mapping_id = created["id"]

        # user2 tries to delete user1's mapping -> must return 404
        del_res = client2.delete(f"{self.MAPPINGS_URL}{mapping_id}/")
        assert del_res.status_code == status.HTTP_404_NOT_FOUND
        assert del_res.data["error"]["code"] == "not_found"

        # Verify mapping still exists
        list_res = client1.get(self.MAPPINGS_URL)
        assert len(list_res.data) == 1

    def test_delete_nonexistent_mapping_returns_404(self, client1):
        del_res = client1.delete(f"{self.MAPPINGS_URL}999999/")
        assert del_res.status_code == status.HTTP_404_NOT_FOUND
        assert del_res.data["error"]["code"] == "not_found"


@pytest.mark.django_db
class TestMappingCascadeDeletes:
    MAPPINGS_URL = "/api/mappings/"

    def test_cascade_delete_when_patient_deleted(self, client1, make_patient, make_doctor):
        patient = make_patient()
        doctor = make_doctor()
        client1.post(self.MAPPINGS_URL, {"patient_id": patient["id"], "doctor_id": doctor["id"]}, format="json")

        assert len(client1.get(self.MAPPINGS_URL).data) == 1

        # Delete patient
        del_patient = client1.delete(f"/api/patients/{patient['id']}/")
        assert del_patient.status_code == status.HTTP_204_NO_CONTENT

        # Mappings should now be empty
        assert len(client1.get(self.MAPPINGS_URL).data) == 0

    def test_cascade_delete_when_doctor_deleted(self, client1, make_patient, make_doctor):
        patient = make_patient()
        doctor = make_doctor()
        client1.post(self.MAPPINGS_URL, {"patient_id": patient["id"], "doctor_id": doctor["id"]}, format="json")

        assert len(client1.get(self.MAPPINGS_URL).data) == 1

        # Delete doctor
        del_doctor = client1.delete(f"/api/doctors/{doctor['id']}/")
        assert del_doctor.status_code == status.HTTP_204_NO_CONTENT

        # Mappings should now be empty
        assert len(client1.get(self.MAPPINGS_URL).data) == 0

    def test_unauthenticated_mapping_requests_return_401(self, api_client):
        assert api_client.get(self.MAPPINGS_URL).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(self.MAPPINGS_URL, {"patient_id": 1, "doctor_id": 1}, format="json").status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.get(f"{self.MAPPINGS_URL}1/").status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.delete(f"{self.MAPPINGS_URL}1/").status_code == status.HTTP_401_UNAUTHORIZED
