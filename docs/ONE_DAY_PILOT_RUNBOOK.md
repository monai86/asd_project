# One-Day Pilot Runbook

This runbook describes the local/staging pilot MVP for Therapist App v2. It is production-like enough to exercise tenant-scoped workflow behavior, but it is not production-ready and is not clinically validated.

## What Works Today

- FastAPI backend in `apps/api/`.
- Local/SQL tenant scaffold with a seeded local pilot organization:
  - organization ID: `pilot_org_001`
  - default therapist user: `therapist-demo`
  - seeded demo case: `case_demo_001`
- Backend authorization guard for organization ID, role, and case care team.
- Tenant-scoped case, session, transcript, and report access.
- Phase 1 tenant foundation now also scopes therapy goals, feature sets,
  audio metadata, AI/ML review records, jobs, privacy operations, and audit
  rows with `organization_id` in the SQL model.
- Alembic migration `0009_add_tenant_rls_policies` adds organization settings,
  membership/care-team, identity, retention, consent, notification, job attempt
  tables, and PostgreSQL RLS policy SQL as defense-in-depth. Active Alembic
  head is now `0010_add_auth_lifecycle_tables`, adding backend auth lifecycle
  invitation records.
- Local private audio metadata flow:
  - create upload intent;
  - complete upload metadata;
  - queue/process local pilot transcription job;
  - draft transcript remains therapist-review required.
- Report sign-off and export keep immutable signed snapshots and hashes.
- Production-mode guard rejects mock auth and local/demo runtime dependencies.
- Backend Supabase Auth scaffold exists for production-path tests, but the
  local pilot still uses mock auth headers only.
- Backend org-admin APIs can add/list local organization memberships and assign
  case care-team members for pilot/production-path testing.
- Backend org-admin APIs now also support invitation records, invitation
  acceptance into active membership, membership revocation, and scoped audited
  break-glass case access for production-path testing only.
- Therapist App v2 Settings/Admin now includes a local Pilot Access Lifecycle
  console for invitation creation, membership review, and membership revocation
  against the backend admin endpoints.

## Run Locally

From the repository root:

```bash
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Useful local pilot environment defaults:

```bash
THERAPIST_APP_V2_MOCK_MODE=true
THERAPIST_APP_V2_AUTH_MODE=mock
THERAPIST_APP_V2_REPOSITORY_MODE=json
THERAPIST_APP_V2_STORAGE_MODE=local_private
THERAPIST_APP_V2_JOB_QUEUE_MODE=memory
THERAPIST_APP_V2_LOCAL_STORAGE_ROOT=.local/storage
```

Use mock headers only for the pilot:

```text
X-Mock-User-Id: therapist-demo
X-Mock-Role: therapist
X-Organization-Id: pilot_org_001
```

## Pilot Workflow

1. Create or open a case in `pilot_org_001`.
2. Create a therapy session.
3. Upload or manually enter a transcript.
4. Run QA and therapist attestation.
5. Extract features and optional review cues.
6. Draft a report.
7. Sign off the report.
8. Export Markdown or HTML from the signed report.

Audio pilot flow:

1. `POST /api/v1/sessions/{session_id}/audio/upload`
2. Use the returned local-private upload intent for local testing only.
3. `POST /api/v1/audio/{audio_file_id}/complete-upload`
4. `POST /api/v1/sessions/{session_id}/audio/process`
5. Run local worker once if using queued processing.

## Verification

```bash
cd apps/api
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest -q

cd ../..
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/security_scan.py
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/check_repo_consistency.py
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/check_api_migrations.py
git diff --check
```

## Not Production

The pilot still does not include:

- Real Supabase Auth project setup, MFA enrollment, invitations, or public
  onboarding controls.
- Real invitation email delivery, MFA setup UI, and Supabase custom-claim
  synchronization for membership state.
- Supabase-hosted PostgreSQL RLS verification with real auth claims.
- Supabase Storage signed URL implementation.
- Celery/Redis durable worker leases, retries, and dead-letter handling.
- Approved ASR vendor integration or region policy enforcement.
- External security review, legal review, production backup/PITR drill, or clinic launch approval.

Do not use this pilot with real child identifiers, real transcripts, real audio, secrets, storage keys, or clinical content. It remains a research/education prototype and must not be described as diagnostic or clinically validated.
