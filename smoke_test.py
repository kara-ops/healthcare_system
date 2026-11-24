"""
Manual smoke test script executing the full end-to-end user journey across all endpoints.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('DB_ENGINE', 'django.db.backends.sqlite3')
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.core.management import call_command
call_command('migrate', verbosity=0)

from rest_framework.test import APIClient

client = APIClient()

print("--- 1. Register User ---")
reg_res = client.post('/api/auth/register/', {
    'name': 'Smoke Test User',
    'email': 'smoke@hospital.org',
    'password': 'StrongSmokePass987!'
}, format='json')
print(f"Status: {reg_res.status_code}, Body: {reg_res.json()}")
assert reg_res.status_code == 201

print("\n--- 2. Login User ---")
login_res = client.post('/api/auth/login/', {
    'email': 'smoke@hospital.org',
    'password': 'StrongSmokePass987!'
}, format='json')
print(f"Status: {login_res.status_code}")
tokens = login_res.json()
access_token = tokens['access']
refresh_token = tokens['refresh']
client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

print("\n--- 3. Token Refresh ---")
ref_client = APIClient()
ref_res = ref_client.post('/api/auth/token/refresh/', {'refresh': refresh_token}, format='json')
print(f"Status: {ref_res.status_code}, New access: {bool(ref_res.json().get('access'))}")
assert ref_res.status_code == 200

print("\n--- 4. Create Patient ---")
pat_res = client.post('/api/patients/', {
    'name': 'Alice Patient',
    'age': 32,
    'gender': 'Female',
    'phone': '+1-555-0100',
    'address': '742 Evergreen Terrace',
    'medical_history': 'No prior chronic conditions'
}, format='json')
print(f"Status: {pat_res.status_code}, Body: {pat_res.json()}")
assert pat_res.status_code == 201
patient_id = pat_res.json()['id']

print("\n--- 5. List Patients ---")
list_pat_res = client.get('/api/patients/')
print(f"Status: {list_pat_res.status_code}, Count: {len(list_pat_res.json())}")
assert list_pat_res.status_code == 200

print("\n--- 6. Get Patient by ID ---")
get_pat_res = client.get(f'/api/patients/{patient_id}/')
print(f"Status: {get_pat_res.status_code}, Name: {get_pat_res.json()['name']}")
assert get_pat_res.status_code == 200

print("\n--- 7. Update Patient ---")
put_pat_res = client.put(f'/api/patients/{patient_id}/', {
    'name': 'Alice Patient Updated',
    'age': 33,
    'gender': 'Female',
    'phone': '+1-555-0199',
    'address': '742 Evergreen Terrace Apt 4',
    'medical_history': 'Seasonal allergies'
}, format='json')
print(f"Status: {put_pat_res.status_code}, Updated age: {put_pat_res.json()['age']}")
assert put_pat_res.status_code == 200

print("\n--- 8. Create Doctor ---")
doc_res = client.post('/api/doctors/', {
    'name': 'Bob Physician',
    'specialization': 'Neurology',
    'email': 'dr.bob@hospital.org',
    'phone': '+1-555-0200',
    'years_of_experience': 12
}, format='json')
print(f"Status: {doc_res.status_code}, Body: {doc_res.json()}")
assert doc_res.status_code == 201
doctor_id = doc_res.json()['id']

print("\n--- 9. List Doctors ---")
list_doc_res = client.get('/api/doctors/')
print(f"Status: {list_doc_res.status_code}, Count: {len(list_doc_res.json())}")
assert list_doc_res.status_code == 200

print("\n--- 10. Get Doctor by ID ---")
get_doc_res = client.get(f'/api/doctors/{doctor_id}/')
print(f"Status: {get_doc_res.status_code}, Doctor: {get_doc_res.json()['name']}")
assert get_doc_res.status_code == 200

print("\n--- 11. Update Doctor ---")
put_doc_res = client.put(f'/api/doctors/{doctor_id}/', {
    'name': 'Bob Physician MD',
    'specialization': 'Chief Neurology',
    'email': 'dr.bob@hospital.org',
    'phone': '+1-555-0200',
    'years_of_experience': 13
}, format='json')
print(f"Status: {put_doc_res.status_code}, Spec: {put_doc_res.json()['specialization']}")
assert put_doc_res.status_code == 200

print("\n--- 12. Create Patient-Doctor Mapping ---")
map_res = client.post('/api/mappings/', {
    'patient_id': patient_id,
    'doctor_id': doctor_id
}, format='json')
print(f"Status: {map_res.status_code}, Mapping: {map_res.json()}")
assert map_res.status_code == 201
mapping_id = map_res.json()['id']

print("\n--- 13. List Mappings ---")
list_map_res = client.get('/api/mappings/')
print(f"Status: {list_map_res.status_code}, Count: {len(list_map_res.json())}")
assert list_map_res.status_code == 200

print("\n--- 14. Get Doctors for Patient (GET /api/mappings/<patient_id>/) ---")
get_pat_docs_res = client.get(f'/api/mappings/{patient_id}/')
print(f"Status: {get_pat_docs_res.status_code}, Doctors assigned: {len(get_pat_docs_res.json())}")
assert get_pat_docs_res.status_code == 200

print("\n--- 15. Delete Mapping (DELETE /api/mappings/<mapping_id>/) ---")
del_map_res = client.delete(f'/api/mappings/{mapping_id}/')
print(f"Status: {del_map_res.status_code}")
assert del_map_res.status_code == 204

print("\n--- 16. Delete Patient ---")
del_pat_res = client.delete(f'/api/patients/{patient_id}/')
print(f"Status: {del_pat_res.status_code}")
assert del_pat_res.status_code == 204

print("\n--- 17. Delete Doctor ---")
del_doc_res = client.delete(f'/api/doctors/{doctor_id}/')
print(f"Status: {del_doc_res.status_code}")
assert del_doc_res.status_code == 204

print("\n==========================================")
print("ALL 17 SMOKE TEST ENDPOINTS VERIFIED 100%!")
print("==========================================")
