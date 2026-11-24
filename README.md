# Healthcare Backend API

A production-grade, secure, multi-tenant healthcare backend built with **Django 5.1**, **Django REST Framework (DRF) 3.15**, **PostgreSQL 16**, and **JWT authentication (SimpleJWT)**. 

The system enables healthcare providers to securely register, authenticate, manage private patient records, maintain a shared directory of qualified doctors, and assign doctors to patients.

---

## Architecture Overview

The system is designed according to strict domain-driven, modular Django principles:

```
drf_healthcare_p/
├── config/                  # Project configuration & orchestration
│   ├── settings.py          # Unified settings with django-environ
│   ├── urls.py              # Root URL dispatcher
│   ├── wsgi.py / asgi.py    # Production gateway interfaces
├── apps/
│   ├── core/                # Shared enterprise foundations
│   │   ├── models.py        # Abstract TimestampedModel (created_at, updated_at)
│   │   ├── permissions.py   # IsOwner object-level permission class
│   │   └── exceptions.py    # Custom exception handler (uniform JSON error envelope)
│   ├── accounts/            # Identity & Access Management
│   │   ├── models.py        # Custom User (email as USERNAME_FIELD, name, no username)
│   │   ├── managers.py      # CustomUserManager (case-insensitive email normalization)
│   │   ├── serializers.py   # Register, Login, User serializers with password validators
│   │   └── views.py         # RegisterView, LoginView, TokenRefreshView
│   ├── patients/            # Patient Record Management (Private Isolation)
│   │   ├── models.py        # Patient model with demographic & medical history fields
│   │   ├── serializers.py   # PatientSerializer with strict field validation
│   │   └── views.py         # ListCreate and Detail views filtered by request.user
│   ├── doctors/             # Doctor Directory (Shared Directory)
│   │   ├── models.py        # Doctor model with specialization and experience
│   │   ├── serializers.py   # DoctorSerializer with case-insensitive unique email check
│   │   └── views.py         # Shared read access, creator-only update/delete permissions
│   └── mappings/            # Patient-Doctor Assignments
│       ├── models.py        # PatientDoctorMapping with unique (patient, doctor) constraint
│       ├── serializers.py   # MappingCreateSerializer & MappingReadSerializer
│       └── views.py         # MappingListCreateView & dual-semantic MappingDetailView
├── docs/
│   ├── API_CONTRACT.md      # Canonical API specification & contract
│   ├── WALKTHROUGH.md       # Architecture deep-dive for FastAPI/SQLAlchemy developers
│   └── postman_collection.json # Postman v2.1 collection with automated token extraction
├── tests/                   # Pytest test suite (comprehensive coverage & isolation tests)
├── docker-compose.yml       # Production-ready PostgreSQL container service
├── requirements.txt         # Pinned production and test dependencies
├── manage.py                # Django CLI management utility
└── pytest.ini               # Pytest configuration
```

### Key Architectural Highlights
1. **Security & Ownership Isolation**:
   - Patients are private to their creator. Querysets are strictly scoped via `created_by=request.user`. Attempting to access another user's patient returns an HTTP `404 Not Found` rather than `403 Forbidden`, preventing resource enumeration / IDOR existence leakage.
   - Doctors form a shared directory where any authenticated user can view the roster, but only the creator (`created_by`) can perform updates (`PUT`/`PATCH`) or deletion (`DELETE`), returning `403 Permission Denied` to unauthorized callers.
   - Mappings are strictly bound to patients owned by the requesting user.
2. **Uniform Error Envelope**:
   All errors across the entire API (HTTP 400, 401, 403, 404, 405, and unhandled 500s) return a predictable, standardized envelope produced by `apps/core/exceptions.py`:
   ```json
   {
     "error": {
       "code": "<error_code>",
       "message": "<human_readable_message>",
       "details": { ... }
     }
   }
   ```
3. **Stateless JWT Authentication**:
   Protected endpoints require `Authorization: Bearer <access_token>` powered by `rest_framework_simplejwt`.

---

## Prerequisites

- **Python**: Version `3.11` or newer
- **Database**: **PostgreSQL 16+** (native service or running via **Docker & Docker Compose**)
- **Git**

---

## Step-by-Step Setup Guide

### 1. Clone the Repository & Create Virtual Environment

```bash
# Clone repository
git clone <repository_url>
cd drf_healthcare_p

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
.\.venv\Scripts\activate.bat
```

### 2. Install Dependencies

Install all pinned packages:

```bash
pip install -r requirements.txt
```

### 3. Start Database (PostgreSQL via Docker or Local)

**Option A: Using Docker Compose (Recommended)**
```bash
docker-compose up -d
```
*This starts a PostgreSQL 16 container named `drf_healthcare_p-db-1` on port `5432` with a persistent volume `postgres_data`.*

**Option B: Using Local PostgreSQL**
Ensure PostgreSQL is running locally and create the database:
```sql
CREATE DATABASE healthcare_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE healthcare_db TO postgres;
```

### 4. Configure Environment Variables

Copy the provided `.env.example` template to `.env`:

```bash
# On Linux / macOS / PowerShell
cp .env.example .env
```

Review `.env` and adjust database credentials or token lifetimes if necessary:
```env
SECRET_KEY=change-me-to-a-real-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=healthcare_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
JWT_ACCESS_LIFETIME_MINUTES=60
JWT_REFRESH_LIFETIME_DAYS=7
```

### 5. Apply Database Migrations

Run database migrations to initialize tables for custom users, patients, doctors, and mappings:

```bash
python manage.py migrate
```

Verify that system checks pass cleanly:
```bash
python manage.py check
```

### 6. Start the Development Server

```bash
python manage.py runserver
```
The API is now live at: `http://127.0.0.1:8000/api/`

---

## Running Automated Tests

The project includes an exhaustive automated test suite using `pytest` and `pytest-django`.

Run the test suite:
```bash
pytest
```

To run with verbose output:
```bash
pytest -v
```

*(Note: In environments where a live PostgreSQL instance is not connected, the test suite can be run seamlessly in-memory by setting `DB_ENGINE=django.db.backends.sqlite3 pytest`).*

---

## Manual Smoke Test Command Sequence

You can execute this complete end-to-end smoke test sequence against a running server (`http://127.0.0.1:8000`) using `curl`:

### Step 1: Register a New User
```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Gregory House",
    "email": "house@princetonplainsboro.com",
    "password": "DiagnosticSupervision2026!"
  }'
```
*Response: HTTP 201 Created with `{ "id": 1, "name": "Dr. Gregory House", "email": "house@princetonplainsboro.com" }`*

### Step 2: Login and Obtain JWT Tokens
```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "house@princetonplainsboro.com",
    "password": "DiagnosticSupervision2026!"
  }'
```
*Response: HTTP 200 OK with `{ "access": "<ACCESS_TOKEN>", "refresh": "<REFRESH_TOKEN>", "user": {...} }`*

> **Export Token for subsequent commands:**
> ```bash
> # Linux / macOS bash:
> export TOKEN="<paste_access_token_here>"
> # Windows PowerShell:
> $TOKEN="<paste_access_token_here>"
> ```

### Step 3: Refresh Access Token
```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "<paste_refresh_token_here>"
  }'
```

### Step 4: Create a Patient Record
```bash
curl -s -X POST http://127.0.0.1:8000/api/patients/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "John Doe",
    "age": 42,
    "gender": "Male",
    "phone": "+1-555-0199",
    "address": "221B Baker St, London",
    "medical_history": "Hypertension, penicillin allergy"
  }'
```
*Response: HTTP 201 Created with Patient ID 1.*

### Step 5: List Patients (Owner Scoped)
```bash
curl -s -X GET http://127.0.0.1:8000/api/patients/ \
  -H "Authorization: Bearer $TOKEN"
```

### Step 6: Get Patient Details by ID
```bash
curl -s -X GET http://127.0.0.1:8000/api/patients/1/ \
  -H "Authorization: Bearer $TOKEN"
```

### Step 7: Update Patient Details (Full Update)
```bash
curl -s -X PUT http://127.0.0.1:8000/api/patients/1/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "John Doe",
    "age": 43,
    "gender": "Male",
    "phone": "+1-555-0199",
    "address": "221B Baker St, London",
    "medical_history": "Hypertension, resolved allergy"
  }'
```

### Step 8: Create a Doctor Record
```bash
curl -s -X POST http://127.0.0.1:8000/api/doctors/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Allison Cameron",
    "specialization": "Immunology",
    "email": "cameron@princetonplainsboro.com",
    "phone": "+1-555-0144",
    "years_of_experience": 8
  }'
```
*Response: HTTP 201 Created with Doctor ID 1.*

### Step 9: List Doctors (Shared Directory)
```bash
curl -s -X GET http://127.0.0.1:8000/api/doctors/ \
  -H "Authorization: Bearer $TOKEN"
```

### Step 10: Get Doctor Details by ID
```bash
curl -s -X GET http://127.0.0.1:8000/api/doctors/1/ \
  -H "Authorization: Bearer $TOKEN"
```

### Step 11: Update Doctor Details (Creator Restricted)
```bash
curl -s -X PUT http://127.0.0.1:8000/api/doctors/1/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Allison Cameron",
    "specialization": "Diagnostic Immunology",
    "email": "cameron@princetonplainsboro.com",
    "phone": "+1-555-0144",
    "years_of_experience": 9
  }'
```

### Step 12: Assign Doctor to Patient (Create Mapping)
```bash
curl -s -X POST http://127.0.0.1:8000/api/mappings/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "patient_id": 1,
    "doctor_id": 1
  }'
```
*Response: HTTP 201 Created with Mapping ID 1.*

### Step 13: List All Mappings (Owner's Patients)
```bash
curl -s -X GET http://127.0.0.1:8000/api/mappings/ \
  -H "Authorization: Bearer $TOKEN"
```

### Step 14: Get All Doctors Assigned to Patient (by Patient ID)
```bash
curl -s -X GET http://127.0.0.1:8000/api/mappings/1/ \
  -H "Authorization: Bearer $TOKEN"
```
*Returns list of doctor assignments for Patient ID 1.*

### Step 15: Delete Mapping (by Mapping ID)
```bash
curl -s -X DELETE http://127.0.0.1:8000/api/mappings/1/ \
  -H "Authorization: Bearer $TOKEN"
```
*Response: HTTP 204 No Content.*

### Step 16: Delete Patient (Cascades to Mappings)
```bash
curl -s -X DELETE http://127.0.0.1:8000/api/patients/1/ \
  -H "Authorization: Bearer $TOKEN"
```
*Response: HTTP 204 No Content.*

### Step 17: Delete Doctor (Creator Restricted, Cascades to Mappings)
```bash
curl -s -X DELETE http://127.0.0.1:8000/api/doctors/1/ \
  -H "Authorization: Bearer $TOKEN"
```
*Response: HTTP 204 No Content.*

---

## Environment Variables

| Variable Name | Default | Required? | Description |
|---|---|---|---|
| `SECRET_KEY` | *(None)* | **Yes** | Django secret key for cryptographic signing & session security. |
| `DEBUG` | `False` | No | Boolean flag for Django debug mode (`True` in dev, `False` in prod). |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | No | Comma-delimited list of host/domain names this Django site can serve. |
| `DB_ENGINE` | `django.db.backends.postgresql` | No | Database engine. Override with `django.db.backends.sqlite3` for in-memory testing. |
| `DB_NAME` | `healthcare_db` | No | PostgreSQL database name. |
| `DB_USER` | `postgres` | No | PostgreSQL user role. |
| `DB_PASSWORD` | `postgres` | No | PostgreSQL user password. |
| `DB_HOST` | `localhost` | No | PostgreSQL host address (e.g. `localhost` or docker host). |
| `DB_PORT` | `5432` | No | PostgreSQL connection port. |
| `JWT_ACCESS_LIFETIME_MINUTES` | `60` | No | Access token validity duration in minutes. |
| `JWT_REFRESH_LIFETIME_DAYS` | `7` | No | Refresh token validity duration in days. |

---

## API Endpoints Reference

All routes are prefixed with `/api/`. Default permission is `IsAuthenticated`.

| Method | Endpoint | Auth Required | Description | Example curl |
|---|---|---|---|---|
| `POST` | `/api/auth/register/` | **No** (AllowAny) | Register a new user with `name`, `email`, `password`. | `curl -X POST http://127.0.0.1:8000/api/auth/register/ -H "Content-Type: application/json" -d '{"name":"John Doe","email":"john@example.com","password":"SecureP@ss123"}'` |
| `POST` | `/api/auth/login/` | **No** (AllowAny) | Authenticate user credentials, returning access & refresh tokens. | `curl -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" -d '{"email":"john@example.com","password":"SecureP@ss123"}'` |
| `POST` | `/api/auth/token/refresh/` | **No** (AllowAny) | Exchange valid refresh token for new access token. | `curl -X POST http://127.0.0.1:8000/api/auth/token/refresh/ -H "Content-Type: application/json" -d '{"refresh":"<REFRESH_TOKEN>"}'` |
| `POST` | `/api/patients/` | **Yes** (Bearer) | Create a new private patient record for authenticated user. | `curl -X POST http://127.0.0.1:8000/api/patients/ -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"name":"Jane Smith","age":45,"gender":"Female","phone":"+1234567890","address":"123 Main St","medical_history":"None"}'` |
| `GET` | `/api/patients/` | **Yes** (Bearer) | List all patients created by the authenticated user. | `curl -X GET http://127.0.0.1:8000/api/patients/ -H "Authorization: Bearer <TOKEN>"` |
| `GET` | `/api/patients/<id>/` | **Yes** (Bearer) | Retrieve patient details (owner-only, 404 for other users). | `curl -X GET http://127.0.0.1:8000/api/patients/1/ -H "Authorization: Bearer <TOKEN>"` |
| `PUT` | `/api/patients/<id>/` | **Yes** (Bearer) | Full update of a patient record (owner-only). | `curl -X PUT http://127.0.0.1:8000/api/patients/1/ -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"name":"Jane Smith","age":46,"gender":"Female","phone":"+1234567890","address":"123 Main St","medical_history":"Asthma"}'` |
| `PATCH` | `/api/patients/<id>/` | **Yes** (Bearer) | Partial update of a patient record (owner-only). | `curl -X PATCH http://127.0.0.1:8000/api/patients/1/ -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"age":47}'` |
| `DELETE` | `/api/patients/<id>/` | **Yes** (Bearer) | Delete patient record (owner-only, cascades to mappings). | `curl -X DELETE http://127.0.0.1:8000/api/patients/1/ -H "Authorization: Bearer <TOKEN>"` |
| `POST` | `/api/doctors/` | **Yes** (Bearer) | Add a doctor to the shared directory. | `curl -X POST http://127.0.0.1:8000/api/doctors/ -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"name":"Dr. Alice","specialization":"Cardiology","email":"alice@hospital.com","phone":"+9876543210","years_of_experience":15}'` |
| `GET` | `/api/doctors/` | **Yes** (Bearer) | List all doctors in shared directory. | `curl -X GET http://127.0.0.1:8000/api/doctors/ -H "Authorization: Bearer <TOKEN>"` |
| `GET` | `/api/doctors/<id>/` | **Yes** (Bearer) | Retrieve details of a doctor. | `curl -X GET http://127.0.0.1:8000/api/doctors/1/ -H "Authorization: Bearer <TOKEN>"` |
| `PUT` | `/api/doctors/<id>/` | **Yes** (Bearer) | Full update of doctor details (creator-only, 403 for others). | `curl -X PUT http://127.0.0.1:8000/api/doctors/1/ -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"name":"Dr. Alice Smith","specialization":"Cardiology","email":"alice@hospital.com","phone":"+9876543210","years_of_experience":16}'` |
| `PATCH` | `/api/doctors/<id>/` | **Yes** (Bearer) | Partial update of doctor details (creator-only, 403 for others). | `curl -X PATCH http://127.0.0.1:8000/api/doctors/1/ -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"years_of_experience":17}'` |
| `DELETE` | `/api/doctors/<id>/` | **Yes** (Bearer) | Delete doctor (creator-only, 403 for others, cascades to mappings). | `curl -X DELETE http://127.0.0.1:8000/api/doctors/1/ -H "Authorization: Bearer <TOKEN>"` |
| `POST` | `/api/mappings/` | **Yes** (Bearer) | Assign a doctor to a patient owned by authenticated user. | `curl -X POST http://127.0.0.1:8000/api/mappings/ -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"patient_id":1,"doctor_id":1}'` |
| `GET` | `/api/mappings/` | **Yes** (Bearer) | List mappings for patients owned by authenticated user. | `curl -X GET http://127.0.0.1:8000/api/mappings/ -H "Authorization: Bearer <TOKEN>"` |
| `GET` | `/api/mappings/<patient_id>/` | **Yes** (Bearer) | Get all doctors assigned to patient `<patient_id>` (owner-only). | `curl -X GET http://127.0.0.1:8000/api/mappings/1/ -H "Authorization: Bearer <TOKEN>"` |
| `DELETE` | `/api/mappings/<id>/` | **Yes** (Bearer) | Remove doctor assignment `<id>` (mapping ID, owner-only). | `curl -X DELETE http://127.0.0.1:8000/api/mappings/1/ -H "Authorization: Bearer <TOKEN>"` |

---

## Decisions on Ambiguities

*(Reproduced verbatim from Section 2 of the Project Specification)*

1. Custom user model, created BEFORE the first migration: email is the login identifier (USERNAME_FIELD = "email", unique, stored lowercase), plus a `name` field and password. No username field. Set AUTH_USER_MODEL from the start.
2. Register: validate name (non-empty), email (valid, unique, case-insensitive), password (Django's built-in password validators). Never return the password. Return 201 with the user's id, name and email.
3. Login: accept email + password, return 200 with `access`, `refresh` and basic user info. Wrong credentials return 401 with the standard error shape. Build this on simplejwt (custom serializer or view). Also expose POST /api/auth/token/refresh/ using simplejwt's refresh view.
4. All endpoints require authentication by default (DRF DEFAULT_PERMISSION_CLASSES = IsAuthenticated). Only register, login and token refresh use AllowAny, and each is explicitly marked.
5. Patients are private to their creator. Every patient query is filtered by created_by = request.user. Accessing another user's patient returns 404, not 403, so existence is not leaked. created_by is set server-side and is read-only in the API.
6. Doctors are a shared directory: any authenticated user can list and read all doctors. Only the user who created a doctor (created_by) can update or delete it; others get 403. Doctor email is unique.
7. Mappings:
   - POST: the patient must belong to request.user (else 404 or 400 with a clear message); the doctor must exist; the same (patient, doctor) pair cannot be assigned twice (DB unique constraint plus a clean 400 or 409 response).
   - GET /api/mappings/: returns only mappings whose patient belongs to request.user (this avoids leaking other users' patient data).
   - GET /api/mappings/<patient_id>/: doctors assigned to that patient, only if the patient belongs to request.user, otherwise 404.
   - DELETE /api/mappings/<id>/: <id> is the mapping id; allowed only if the mapping's patient belongs to request.user, otherwise 404.
   - GET and DELETE share the route `mappings/<int:pk>/` but mean different things. Implement this with explicit APIView / generics views and clearly commented URL patterns. DO NOT use a DRF router/ViewSet for mappings, because it would silently map GET to the mapping id.
8. Deleting a patient or doctor cascades to its mappings (on_delete=CASCADE). Say so in the README.
9. No pagination: list endpoints return plain JSON arrays so response shapes match the spec literally. Mention pagination as a possible extension in the README, but do not implement it.
10. PUT is a full update. Allowing PATCH as well is fine because the generic views provide it.
11. Model fields:
    - Patient: name, age (positive integer, sane upper bound), gender (choices), phone, address, medical_history (optional text), created_by (FK to user), created_at, updated_at.
    - Doctor: name, specialization, email (unique), phone, years_of_experience (non-negative), created_by (FK to user), created_at, updated_at.
    - PatientDoctorMapping: patient (FK), doctor (FK), assigned_at, unique constraint on (patient, doctor).
12. Consistent error response shape for ALL errors, including 400/401/403/404/405/500, produced by one custom DRF exception handler. For example: {"error": {"code": "validation_error", "message": "...", "details": {...}}}. Unhandled exceptions return a generic 500 with no stack trace or internals.

---

## Cascade Deletion Behavior

The system models relationships using strict relational referential integrity (`on_delete=models.CASCADE`):

- **Patient Deletion (`DELETE /api/patients/<id>/`)**:
  When a patient is deleted by their creator, all corresponding `PatientDoctorMapping` records referencing that patient are automatically deleted from PostgreSQL in the same database transaction. The doctor record remains unaffected in the shared directory.
- **Doctor Deletion (`DELETE /api/doctors/<id>/`)**:
  When a doctor is deleted by their creator, all corresponding `PatientDoctorMapping` records referencing that doctor are automatically deleted from PostgreSQL. The patient records remain intact.
- **User Account Deletion**:
  If a user account is deleted, Django's cascading deletion automatically removes all patients and doctors created by that user, which recursively cascades to remove all associated patient-doctor mappings.

---

## Known Limitations & Production Extensions

1. **No Pagination (By Specification)**:
   In strict accordance with the API contract, all list endpoints (`/api/patients/`, `/api/doctors/`, `/api/mappings/`, `/api/mappings/<patient_id>/`) return unpaginated top-level JSON arrays. For high-volume enterprise deployments with tens of thousands of records, DRF's `PageNumberPagination` or `CursorPagination` should be enabled via `REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']`.
2. **Rate Limiting & Throttling**:
   Currently, authentication and resource endpoints do not enforce rate limits. In production, DRF's `AnonRateThrottle` (e.g. 10/min on `/api/auth/login/` to prevent credential brute-forcing) and `UserRateThrottle` (e.g. 1000/hour) should be activated.
3. **Interactive Swagger / OpenAPI Documentation**:
   `drf-spectacular` can be introduced to auto-generate an OpenAPI 3.0 specification and interactive Swagger UI / Redoc at `/api/docs/`.
4. **Token Revocation & Blacklisting**:
   `rest_framework_simplejwt.token_blacklist` can be added along with a `POST /api/auth/logout/` endpoint to invalidate refresh tokens immediately upon user logout.
5. **Role-Based Access Control (RBAC)**:
   The current model uses a simple ownership pattern (`created_by`). A production hospital management system could introduce granular roles (`Admin`, `Doctor`, `Nurse`, `Billing`) using Django groups and permissions.
6. **Audit Trails & Soft Deletion**:
   For regulatory compliance (such as HIPAA / GDPR), physical row deletion can be replaced with soft deletion (`is_deleted` flag) accompanied by an immutable audit log of clinical data access.
