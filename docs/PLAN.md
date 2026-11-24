# Build Plan — Healthcare Backend

## Phase 0: Plan (Orchestrator)
- Write `docs/API_CONTRACT.md` ✅
- Write this `PLAN.md` ✅

## Phase 1: Scaffold (scaffold agent)
**Owns:** `manage.py`, `requirements.txt`, `.env.example`, `.gitignore`, `docker-compose.yml`, `config/`, `apps/core/`, `apps/__init__.py`, all app `__init__.py` files, `apps/accounts/models.py`, `apps/accounts/managers.py`, `apps/accounts/admin.py`, initial migrations.

**Does NOT own:** views, serializers, URLs in accounts/patients/doctors/mappings (those belong to their respective agents).

**Gate:** `python manage.py check` passes, migrations apply cleanly.

## Phase 2: Build (parallel after scaffold)

### Auth Agent
**Owns:** `apps/accounts/serializers.py`, `apps/accounts/views.py`, `apps/accounts/urls.py`, `apps/accounts/tests.py`
**Does NOT own:** models (scaffold owns those), other apps.

### Records Agent
**Owns:** `apps/patients/` (models, serializers, views, urls, admin), `apps/doctors/` (models, serializers, views, urls, admin), and their migrations.
**Does NOT own:** accounts, mappings, core, config.

### Mappings Agent (starts after Records models exist)
**Owns:** `apps/mappings/` (models, serializers, views, urls, admin), and its migrations.
**Does NOT own:** patient/doctor models, accounts, core, config.

## Phase 3: Verify (parallel)

### QA Agent
**Owns:** Test files across all apps. Writes tests from API_CONTRACT.md only (not from reading implementation).
**Target:** All tests green, meaningful coverage.

### Docs/Postman Agent
**Owns:** `README.md`, `docs/WALKTHROUGH.md`, `docs/postman_collection.json`.

## Phase 4: Review

### Reviewer Agent (read-only)
Reviews entire repo against the contract and spec checklist. Reports findings with file and line references. Does NOT fix anything.

## Phase 5: Fix Loop
Orchestrator routes findings to owning agents. Re-test and re-review.

## Phase 6: Final Gate (Orchestrator)
Fresh setup, full test suite, smoke test, definition-of-done checklist.

---

## Shared Files Policy
- `config/settings.py`, `config/urls.py`, `requirements.txt` — edited ONLY by Orchestrator or Scaffold agent.
- Each agent commits only to files it owns.
- Conflicts resolved by Orchestrator.
