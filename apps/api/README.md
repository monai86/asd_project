# Therapist App v2 API

FastAPI boundary for the case-centered Therapist App v2 workflow.

Local development defaults to a durable JSON repository at
`.local/therapist-app-v2-repository.json`. Set
`THERAPIST_APP_V2_REPOSITORY_MODE=memory` for isolated test/demo runs, or
`THERAPIST_APP_V2_REPOSITORY_MODE=sql` with
`THERAPIST_APP_V2_DATABASE_URL` for the SQLAlchemy-backed repository.

- `json`: default local usable-prototype persistence; survives API restarts.
- `memory`: isolated tests and intentional demo resets only.
- `sql`: PostgreSQL-ready SQLAlchemy scaffold; not pilot-hardened yet.

The frontend treats backend records as the clinical workflow source of truth.
`sessionStorage` is only a UI cache/local fallback. Audio bytes remain in memory
unless the therapist explicitly uploads them.

Transcript and report creation are retry-safe. If a session already has an
active transcript or editable report draft, creation returns that record.
Intentional transcript replacement requires `replace_existing: true`.

Run locally:

```bash
cd apps/api
uvicorn app.main:app --reload --port 8000
```

Run tests:

```bash
cd apps/api
PYTHONPATH=. pytest -q
```

`THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE=false` is the default and keeps failed-QA
or unattested transcripts blocked from feature extraction. Engineering-only runs
may set it to `true` when they also provide an explicit override reason.
