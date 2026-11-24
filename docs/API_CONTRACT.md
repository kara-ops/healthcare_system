# API Contract — Healthcare Backend

This document is the **single source of truth** for every endpoint, its request/response shapes, status codes, error format, and permission rules. All agents build and test against this contract.

---

## Global Conventions

### Base URL
All routes are prefixed with `/api/`.

### Authentication
- JWT Bearer tokens via `djangorestframework-simplejwt`.
- Include header: `Authorization: Bearer <access_token>`
- Default permission: `IsAuthenticated` (DRF global setting).
- Only register, login, and token refresh are `AllowAny`.

### Error Response Shape (ALL errors)
Every error response follows this shape. Produced by a single custom DRF exception handler in `apps/core/exceptions.py`.

```json
{
  "error": {
    "code": "<error_code>",
    "message": "<human-readable message>",
    "details": { ... }
  }
}
```

Error codes used:
| HTTP Status | `code` value | When |
|---|---|---|
| 400 | `validation_error` | Field validation failures, bad input |
| 400 | `duplicate_mapping` | Same (patient, doctor) pair already exists |
| 401 | `authentication_failed` | Missing/invalid/expired token, wrong credentials |
| 403 | `permission_denied` | Authenticated but not allowed (e.g., editing another user's doctor) |
| 404 | `not_found` | Resource does not exist or user does not own it |
| 405 | `method_not_allowed` | HTTP method not supported on this route |
| 500 | `server_error` | Unhandled exception (no stack trace or internals leaked) |

### Content Type
- Request: `application/json`
- Response: `application/json`

### No Pagination
All list endpoints return plain JSON arrays (top-level `[...]`), not paginated objects.

---

## 1. Authentication Endpoints

### POST `/api/auth/register/`
**Permission:** AllowAny

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecureP@ss123"
}
```

**Validation:**
- `name`: required, non-empty string.
- `email`: required, valid email format, unique (case-insensitive, stored lowercase).
- `password`: required, validated by Django's built-in password validators (min 8 chars, not too common, not entirely numeric, not too similar to user attributes).

**Success Response:** `201 Created`
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com"
}
```

**Error Responses:**
- `400` validation_error: missing/invalid fields, duplicate email, weak password.

---

### POST `/api/auth/login/`
**Permission:** AllowAny

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "SecureP@ss123"
}
```

**Success Response:** `200 OK`
```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

**Error Responses:**
- `401` authentication_failed: wrong email or password. Message: "No active account found with the given credentials" or similar.

---

### POST `/api/auth/token/refresh/`
**Permission:** AllowAny

Uses simplejwt's `TokenRefreshView`. 

**Request Body:**
```json
{
  "refresh": "<jwt_refresh_token>"
}
```

**Success Response:** `200 OK`
```json
{
  "access": "<new_jwt_access_token>"
}
```

**Error Responses:**
- `401` authentication_failed: invalid or expired refresh token.

---

## 2. Patient Endpoints

**All require authentication.** Patients are **private to their creator** — every query is filtered by `created_by = request.user`. Accessing another user's patient returns `404` (not `403`).

`created_by` is set server-side and read-only in the API.

### POST `/api/patients/`

**Request Body:**
```json
{
  "name": "Jane Smith",
  "age": 45,
  "gender": "Female",
  "phone": "+1234567890",
  "address": "123 Main St, City",
  "medical_history": "Diabetes Type 2"
}
```

**Field Validation:**
- `name`: required, non-empty string.
- `age`: required, positive integer, max 150.
- `gender`: required, one of: `"Male"`, `"Female"`, `"Other"`.
- `phone`: required, non-empty string.
- `address`: required, non-empty string.
- `medical_history`: optional, text (defaults to empty string or null).

**Success Response:** `201 Created`
```json
{
  "id": 1,
  "name": "Jane Smith",
  "age": 45,
  "gender": "Female",
  "phone": "+1234567890",
  "address": "123 Main St, City",
  "medical_history": "Diabetes Type 2",
  "created_by": 1,
  "created_at": "2026-11-24T12:00:00Z",
  "updated_at": "2026-11-24T12:00:00Z"
}
```

**Error Responses:**
- `400` validation_error: missing/invalid fields.
- `401` authentication_failed: no/invalid token.

---

### GET `/api/patients/`

Returns all patients created by the authenticated user.

**Success Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Jane Smith",
    "age": 45,
    "gender": "Female",
    "phone": "+1234567890",
    "address": "123 Main St, City",
    "medical_history": "Diabetes Type 2",
    "created_by": 1,
    "created_at": "2026-11-24T12:00:00Z",
    "updated_at": "2026-11-24T12:00:00Z"
  }
]
```

---

### GET `/api/patients/<id>/`

Returns one patient, only if `created_by = request.user`.

**Success Response:** `200 OK` — single patient object (same shape as above).

**Error Responses:**
- `404` not_found: patient does not exist or belongs to another user.

---

### PUT `/api/patients/<id>/`

Full update. Only if `created_by = request.user`.

**Request Body:** same as POST (all required fields must be present).

**Success Response:** `200 OK` — updated patient object.

**Error Responses:**
- `400` validation_error: missing/invalid fields.
- `404` not_found: patient does not exist or belongs to another user.

PATCH is also allowed (partial update) since generic views provide it.

---

### DELETE `/api/patients/<id>/`

Only if `created_by = request.user`. Cascades to mappings.

**Success Response:** `204 No Content` (empty body).

**Error Responses:**
- `404` not_found: patient does not exist or belongs to another user.

---

## 3. Doctor Endpoints

**All require authentication.** Doctors are a **shared directory**: any authenticated user can list and read all doctors. Only the user who created a doctor (`created_by`) can update or delete it; others get `403`.

### POST `/api/doctors/`

**Request Body:**
```json
{
  "name": "Dr. Alice",
  "specialization": "Cardiology",
  "email": "alice@hospital.com",
  "phone": "+9876543210",
  "years_of_experience": 15
}
```

**Field Validation:**
- `name`: required, non-empty string.
- `specialization`: required, non-empty string.
- `email`: required, valid email, unique (case-insensitive).
- `phone`: required, non-empty string.
- `years_of_experience`: required, non-negative integer.

**Success Response:** `201 Created`
```json
{
  "id": 1,
  "name": "Dr. Alice",
  "specialization": "Cardiology",
  "email": "alice@hospital.com",
  "phone": "+9876543210",
  "years_of_experience": 15,
  "created_by": 1,
  "created_at": "2026-11-24T12:00:00Z",
  "updated_at": "2026-11-24T12:00:00Z"
}
```

**Error Responses:**
- `400` validation_error: missing/invalid fields, duplicate email.

---

### GET `/api/doctors/`

Returns all doctors (shared directory).

**Success Response:** `200 OK` — JSON array of doctor objects.

---

### GET `/api/doctors/<id>/`

Returns one doctor.

**Success Response:** `200 OK` — single doctor object.

**Error Responses:**
- `404` not_found: doctor does not exist.

---

### PUT `/api/doctors/<id>/`

Full update. Only if `created_by = request.user`, else `403`.

**Request Body:** same as POST.

**Success Response:** `200 OK` — updated doctor object.

**Error Responses:**
- `400` validation_error.
- `403` permission_denied: not the creator.
- `404` not_found: doctor does not exist.

PATCH also allowed.

---

### DELETE `/api/doctors/<id>/`

Only if `created_by = request.user`, else `403`. Cascades to mappings.

**Success Response:** `204 No Content`.

**Error Responses:**
- `403` permission_denied: not the creator.
- `404` not_found: doctor does not exist.

---

## 4. Patient-Doctor Mapping Endpoints

**All require authentication.** Mappings are scoped to patients owned by `request.user`.

**Important:** These use explicit `APIView` / generics views with clearly commented URL patterns. NO DRF router/ViewSet, because GET `mappings/<id>/` means "doctors for patient_id" not "mapping by id".

### POST `/api/mappings/`

Assign a doctor to a patient.

**Request Body:**
```json
{
  "patient_id": 1,
  "doctor_id": 1
}
```

**Validation:**
- `patient_id`: required, must exist and belong to `request.user` (else 404 with message "Patient not found").
- `doctor_id`: required, must exist (else 400 with message "Doctor not found").
- The (patient, doctor) pair must be unique (DB constraint + clean error).

**Success Response:** `201 Created`
```json
{
  "id": 1,
  "patient_id": 1,
  "doctor_id": 1,
  "patient_name": "Jane Smith",
  "doctor_name": "Dr. Alice",
  "assigned_at": "2026-11-24T12:00:00Z"
}
```

**Error Responses:**
- `400` validation_error: doctor not found, missing fields.
- `400` or `409` duplicate_mapping: same pair already assigned.
- `404` not_found: patient not found or not owned by user.

---

### GET `/api/mappings/`

List all mappings whose patient belongs to `request.user`.

**Success Response:** `200 OK`
```json
[
  {
    "id": 1,
    "patient_id": 1,
    "doctor_id": 1,
    "patient_name": "Jane Smith",
    "doctor_name": "Dr. Alice",
    "assigned_at": "2026-11-24T12:00:00Z"
  }
]
```

---

### GET `/api/mappings/<patient_id>/`

All doctors assigned to that patient, only if the patient belongs to `request.user`, otherwise `404`.

**Note:** `<patient_id>` here is a PATIENT id, not a mapping id. The URL pattern is shared with DELETE which uses mapping id. This is handled with explicit views and commented URL patterns.

**Success Response:** `200 OK`
```json
[
  {
    "id": 1,
    "patient_id": 1,
    "doctor_id": 1,
    "patient_name": "Jane Smith",
    "doctor_name": "Dr. Alice",
    "assigned_at": "2026-11-24T12:00:00Z"
  }
]
```

**Error Responses:**
- `404` not_found: patient does not exist or not owned by user.

---

### DELETE `/api/mappings/<id>/`

Remove a mapping. `<id>` is the MAPPING id. Allowed only if the mapping's patient belongs to `request.user`.

**Note:** Since GET and DELETE on `mappings/<int:pk>/` mean different things (patient_id vs mapping_id), implement two separate URL patterns:
- `mappings/<int:patient_id>/` → GET (doctors for patient)
- `mappings/<int:pk>/delete/` → DELETE (remove mapping by id)

OR use a single URL pattern with an explicit view that dispatches GET and DELETE differently. The chosen approach must be clearly documented in comments and the README.

**Decision:** Use two separate URL patterns for clarity:
- `GET /api/mappings/<int:patient_id>/` → PatientDoctorsView  
- `DELETE /api/mappings/<int:pk>/` → MappingDeleteView

The DELETE URL works as `DELETE /api/mappings/<int:pk>/` matching the spec. The view only allows DELETE method. The GET view only allows GET method. Django URL resolution picks the right view because both match `mappings/<int:pk>/` — we use the SAME url pattern but with a view that handles both GET and DELETE with different semantics based on HTTP method.

**Final approach:** Single URL pattern `mappings/<int:pk>/` with an APIView that:
- GET: treats `pk` as `patient_id`, returns doctors for that patient.
- DELETE: treats `pk` as `mapping_id`, deletes that mapping.

This matches the spec routes exactly.

**Success Response (DELETE):** `204 No Content`.

**Error Responses:**
- `404` not_found: mapping does not exist or its patient is not owned by user.

---

## 5. Model Field Reference

### User (custom, `apps/accounts`)
| Field | Type | Constraints |
|---|---|---|
| id | AutoField | PK |
| email | EmailField | unique, USERNAME_FIELD, stored lowercase |
| name | CharField | max_length=255, required |
| password | CharField | hashed, never returned in API |
| is_active | BooleanField | default True |
| is_staff | BooleanField | default False |
| date_joined | DateTimeField | auto_now_add |

### Patient (`apps/patients`)
| Field | Type | Constraints |
|---|---|---|
| id | AutoField | PK |
| name | CharField | max_length=255, required |
| age | PositiveIntegerField | min=1, max=150 |
| gender | CharField | choices: Male, Female, Other |
| phone | CharField | max_length=20 |
| address | TextField | required |
| medical_history | TextField | blank=True, default="" |
| created_by | ForeignKey(User) | on_delete=CASCADE |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |

### Doctor (`apps/doctors`)
| Field | Type | Constraints |
|---|---|---|
| id | AutoField | PK |
| name | CharField | max_length=255, required |
| specialization | CharField | max_length=255 |
| email | EmailField | unique |
| phone | CharField | max_length=20 |
| years_of_experience | PositiveIntegerField | min=0 |
| created_by | ForeignKey(User) | on_delete=CASCADE |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |

### PatientDoctorMapping (`apps/mappings`)
| Field | Type | Constraints |
|---|---|---|
| id | AutoField | PK |
| patient | ForeignKey(Patient) | on_delete=CASCADE |
| doctor | ForeignKey(Doctor) | on_delete=CASCADE |
| assigned_at | DateTimeField | auto_now_add |
| — | unique_together | (patient, doctor) |

---

## 6. Permission Summary

| Endpoint | Method | Auth | Who |
|---|---|---|---|
| /api/auth/register/ | POST | AllowAny | Anyone |
| /api/auth/login/ | POST | AllowAny | Anyone |
| /api/auth/token/refresh/ | POST | AllowAny | Anyone |
| /api/patients/ | GET, POST | IsAuthenticated | Own patients only |
| /api/patients/<id>/ | GET, PUT, PATCH, DELETE | IsAuthenticated | Owner only (404 for others) |
| /api/doctors/ | GET, POST | IsAuthenticated | Any authenticated user |
| /api/doctors/<id>/ | GET | IsAuthenticated | Any authenticated user |
| /api/doctors/<id>/ | PUT, PATCH, DELETE | IsAuthenticated | Creator only (403 for others) |
| /api/mappings/ | GET, POST | IsAuthenticated | Own patients' mappings |
| /api/mappings/<patient_id>/ | GET | IsAuthenticated | Own patient only (404) |
| /api/mappings/<id>/ | DELETE | IsAuthenticated | Own patient's mapping (404) |
