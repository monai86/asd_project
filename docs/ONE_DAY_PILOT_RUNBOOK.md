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
- Local private audio metadata flow:
  - create upload intent;
  - complete upload metadata;
  - queue/process local pilot transcription job;
  - draft transcript remains therapist-review required.
- Report sign-off and export keep immutable signed snapshots and hashes.
- Production-mode guard rejects mock auth and local/demo runtime dependencies.

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

- Supabase Auth, MFA, invitations, or public onboarding controls.
- PostgreSQL RLS policies.
- Supabase Storage signed URL implementation.
- Celery/Redis durable worker leases, retries, and dead-letter handling.
- Approved ASR vendor integration or region policy enforcement.
- External security review, legal review, production backup/PITR drill, or clinic launch approval.

Do not use this pilot with real child identifiers, real transcripts, real audio, secrets, storage keys, or clinical content. It remains a research/education prototype and must not be described as diagnostic or clinically validated.
