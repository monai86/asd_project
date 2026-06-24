# Therapist App v2 Production SaaS Handoff Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue the original production SaaS roadmap until Therapist App v2 can realistically support 5–10 clinics and roughly 100 users with real tenant isolation, production auth, private audio processing, reviewed transcripts, signed reports, operational monitoring, and controlled rollout.

**Architecture:** Keep the production product in `apps/therapist-app-v2/` and `apps/api/`. Treat `src/therapist_backend/` and `src/clinical_workflow/` as legacy/research compatibility surfaces only. The target architecture remains a modular-monolith FastAPI policy boundary backed by Supabase Postgres/Auth/private Storage, durable workers, managed Redis, and responsive web/PWA frontend.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy/Alembic, Supabase Postgres/Auth/Storage, Next.js/React/TypeScript, Celery/Redis, GitHub Actions, Terraform, managed container hosting, Sentry/CloudWatch/OTLP-class observability.

---

## Current handoff date and evidence

- Date: 2026-06-24 Asia/Bangkok.
- Current branch: `main`.
- Current version in docs: `v1.6.3`.
- Source-of-truth file: `docs/PROJECT_SOURCE_OF_TRUTH.md`.
- Canonical frontend: `apps/therapist-app-v2/`.
- Canonical backend: `apps/api/`.
- Legacy surfaces: `src/therapist_backend/` and `src/clinical_workflow/`; do not add new product endpoints there.
- Latest observed API verification before this handoff:
  - `cd apps/api && PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest -q`
  - Result observed before handoff: `175 passed, 1 warning`.
  - `scripts/security_scan.py`: passed.
  - `scripts/check_repo_consistency.py`: passed.
  - `scripts/check_api_migrations.py`: passed through Alembic head `0005_add_privacy_operation_review_fields`.
  - `git diff --check`: exit 0.

## Why this is taking long

The original goal is not a single feature. It is a 6–9 month production SaaS conversion plan covering architecture, data model, auth, tenant isolation, private storage, ASR, reports, AI governance, privacy operations, security, monitoring, CI/CD, infrastructure, and controlled clinic rollout.

The project started as a local research/demo prototype. Several turns have been spent turning implicit demo assumptions into explicit production guardrails before connecting real external systems. That work is repetitive because each production requirement needs:

1. a safety boundary in code;
2. schema or migration support when data must be persisted;
3. tests that prove the boundary;
4. docs/source-of-truth updates so future agents do not regress it;
5. verification that existing prototype workflows still pass.

The system is not done because the biggest production dependencies still require real external systems and product flows: Supabase Auth/RLS/Storage, multi-tenant organization model, invitation/MFA, Celery/Redis outbox workers, approved ASR provider integration, Next.js production auth UI, managed deployment, Terraform, smoke tests, and pilot rollout.

## Current uncommitted work that must be preserved

The current worktree is intentionally dirty with production-hardening changes. Do not discard these files. A next agent should first review, then stage/commit in logical chunks.

Observed modified tracked files:

- `.env.example`
- `.github/workflows/deploy.yml`
- `CHANGELOG.md`
- `PROJECT_STATUS.md`
- `README.md`
- `apps/api/app/api/v1/routes/privacy.py`
- `apps/api/app/api/v1/routes/reports.py`
- `apps/api/app/core/config.py`
- `apps/api/app/core/logging.py`
- `apps/api/app/core/security.py`
- `apps/api/app/db/models.py`
- `apps/api/app/main.py`
- `apps/api/app/repositories/mock_repository.py`
- `apps/api/app/repositories/sqlalchemy_repository.py`
- `apps/api/app/schemas/clinical.py`
- `apps/api/app/services/privacy_operation_service.py`
- `apps/api/app/services/report_service.py`
- `apps/api/tests/test_report_service_v1.py`
- `apps/api/tests/test_workflow.py`
- `docs/API_CONTRACT.md`
- `docs/DEPLOYMENT.md`
- `docs/PROJECT_SOURCE_OF_TRUTH.md`
- `docs/SECURITY.md`
- `scripts/check_project.sh`

Observed new untracked files:

- `apps/api/app/core/rate_limit.py`
- `apps/api/app/db/migrations/versions/0003_add_report_signed_snapshot_fields.py`
- `apps/api/app/db/migrations/versions/0004_add_audit_event_shape_fields.py`
- `apps/api/app/db/migrations/versions/0005_add_privacy_operation_review_fields.py`
- `apps/api/app/services/audit_safety.py`
- `apps/api/app/services/notification_safety.py`
- `apps/api/app/services/observability.py`
- `apps/api/tests/test_audit_safety.py`
- `apps/api/tests/test_cors_security.py`
- `apps/api/tests/test_logging.py`
- `apps/api/tests/test_notification_safety.py`
- `apps/api/tests/test_observability.py`
- `apps/api/tests/test_privacy_operations.py`
- `apps/api/tests/test_secret_management.py`
- `docs/BACKUP_RESTORE_RUNBOOK.md`
- `docs/INCIDENT_RESPONSE_RUNBOOK.md`
- `docs/SECRET_ROTATION_RUNBOOK.md`
- `docs/superpowers/plans/2026-06-24-production-saas-handoff.md`
- `scripts/check_api_migrations.py`
- `scripts/security_scan.py`
- `tests/test_api_migration_smoke.py`
- `tests/test_backup_restore_runbook.py`
- `tests/test_incident_response_runbook.py`
- `tests/test_secret_rotation_runbook.py`
- `tests/test_security_scan.py`

## Completed foundation work in the current dirty branch

This section describes what appears implemented in the current worktree, based on files, tests, and docs inspected before writing this handoff.

### Report governance foundation

- Signed-off reports now have backend-generated signed snapshot metadata:
  - signer;
  - signed timestamp;
  - report version;
  - SHA-256 report hash;
  - export metadata.
- Editing a signed-off report creates a new draft revision rather than silently mutating the signed snapshot.
- Non-template AI report drafting is explicit opt-in and records provider/input hash provenance.
- Relevant files:
  - `apps/api/app/services/report_service.py`
  - `apps/api/app/api/v1/routes/reports.py`
  - `apps/api/app/schemas/clinical.py`
  - `apps/api/app/db/migrations/versions/0003_add_report_signed_snapshot_fields.py`
  - `apps/api/tests/test_report_service_v1.py`

### Security/operations foundations

- API rate limit foundation:
  - `apps/api/app/core/rate_limit.py`
  - generic 429 response;
  - configurable via environment.
- CI/security checks:
  - `scripts/security_scan.py`
  - `.github/workflows/deploy.yml`
  - `scripts/check_project.sh`
- Structured log hardening:
  - route templates or sanitized paths;
  - no raw child IDs, transcript text, audio/storage keys, or raw filenames in normal request logs.
- CORS/Origin guard:
  - server-configured origins;
  - production rejects wildcard/empty origins;
  - unsafe browser-origin writes reject untrusted origin with generic 403.
- Production runtime fail-closed guard:
  - rejects demo/default database/Redis URLs;
  - rejects local repository/storage/job queue in production;
  - requires observability provider/critical alert route;
  - requires managed secret store provider and rotation runbook.

### Backup, incident, audit, notification, observability, privacy foundations

- Backup/restore:
  - `docs/BACKUP_RESTORE_RUNBOOK.md`
  - `scripts/check_api_migrations.py`
  - Alembic smoke reaches `0005_add_privacy_operation_review_fields`.
- Incident response:
  - `docs/INCIDENT_RESPONSE_RUNBOOK.md`
  - stop-rollout criteria: cross-tenant exposure, consent bypass, audit loss, fabricated ASR output.
- Notification safety:
  - `apps/api/app/services/notification_safety.py`
  - blocks child identifiers, transcript text, storage/audio keys, filenames, clinical content.
- Audit event shape:
  - `apps/api/app/services/audit_safety.py`
  - actor/action/target/outcome/timestamp/correlation ID;
  - clinical content blocking.
- Observability safety:
  - `apps/api/app/services/observability.py`
  - safe operational metadata only;
  - production requires approved provider and critical alert route.
- Privacy operations:
  - retention days;
  - legal hold;
  - deletion review state;
  - evidence retention summary;
  - legal hold blocks deletion-review completion;
  - audit/sign-off evidence is not auto-deleted.
- Secret rotation:
  - `docs/SECRET_ROTATION_RUNBOOK.md`
  - production requires managed secret-store provider and credential rotation runbook reference.

## Current completion assessment by original roadmap phase

| Phase | Original intent | Current status | Why not complete |
|---|---|---|---|
| Phase 0 | Freeze architecture and project language | Partially done | Source-of-truth has many rules, but ADRs for Supabase, FastAPI boundary, PWA-only decision, threat model, DFD, data classification inventory still need formal completion/review. |
| Phase 1 | Production data model | Early foundation only | Alembic exists and privacy/report/audit fields were added, but true organization/tenant/membership/care-team/encrypted identity/retention tables are not fully implemented. SQL repository still uses load/save dictionary pattern. |
| Phase 2 | Auth and authorization | Mostly missing | Still has mock headers and demo auth compatibility. Supabase Auth, invite-only signup, MFA, role matrix, care-team membership, break-glass access are not implemented. |
| Phase 3 | API/frontend production boundary | Partially done | FastAPI has safety boundaries, but endpoints are not fully tenant-scoped, org switcher/invite/MFA/care-team UI is missing, Pydantic API schemas are still mixed with persistence/demo models. |
| Phase 4 | Private audio and ASR production | Mostly missing | Local/mock audio processing exists. Supabase private storage, signed direct upload, Celery/Redis, transactional outbox, approved ASR provider, Thai/English benchmark protocol are not complete. |
| Phase 5 | Reports and AI governance | Partially done | Deterministic template/report signoff/snapshot/provenance foundations exist. Vendor governance, identifier sanitization enforcement per provider, signed PDF export, reviewed CHAT export, org-level AI opt-in are incomplete. |
| Phase 6 | Privacy, security, operations | Partially done | Many guards/runbooks exist. Still missing actual notification provider delivery, managed observability integration, real backups/PITR, rate limit provider, external security review, restore/incident/deletion drills, key rotation execution. |
| Phase 7 | CI/CD and production deployment | Mostly missing | CI hardening started. Terraform, separate dev/staging/prod projects, managed container deployment, Next.js hosting config, rolling deploys, smoke tests, rollback, country allowlist gate are not complete. |
| Phase 8 | Controlled production launch | Not started | Requires production infrastructure, legal/vendor/security review, design-partner clinic agreement, synthetic alpha, weekly rollout metrics, stop-rollout process in real ops. |

## Immediate next step before any new feature work

### Task 1: Stabilize and commit the current production-hardening branch

**Files:**

- Review all modified/untracked files listed above.
- Do not add `.next/`, `dist/`, `.local/`, `node_modules/`, or `*.tsbuildinfo`.

- [ ] **Step 1: Inspect current status**

Run:

```bash
cd /Users/porschecaa/Desktop/asd-project
git status --short --branch
git diff --stat
```

Expected: modified and untracked files matching the current hardening work.

- [ ] **Step 2: Run full verification**

Run:

```bash
cd /Users/porschecaa/Desktop/asd-project/apps/api
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest -q
```

Expected: all API tests pass. Last observed result before this handoff was `175 passed, 1 warning`.

Run:

```bash
cd /Users/porschecaa/Desktop/asd-project
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/security_scan.py
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/check_repo_consistency.py
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/check_api_migrations.py
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_api_migration_smoke.py tests/test_backup_restore_runbook.py tests/test_incident_response_runbook.py tests/test_secret_rotation_runbook.py tests/test_security_scan.py -q
git diff --check
```

Expected:

- security scan passed;
- repository consistency passed;
- migration smoke reaches `0005_add_privacy_operation_review_fields`;
- root support tests pass;
- no whitespace errors.

- [ ] **Step 3: Commit in logical chunks**

Recommended chunks:

1. report governance and migration `0003`;
2. rate limit/logging/CORS/runtime config hardening;
3. CI secret scan and migration smoke;
4. backup/incident/secret runbooks;
5. audit/notification/observability/privacy operation foundations.

Every AI commit must include:

```text
Co-Authored-By: GPT-5 Codex <codex@openai.com>
```

## Remaining implementation plan by phase

### Task 2: Finish Phase 0 architecture freeze artifacts

**Files:**

- Create: `docs/adr/0013-supabase-fastapi-production-boundary.md`
- Create: `docs/adr/0014-responsive-web-pwa-only.md`
- Create: `docs/THREAT_MODEL.md`
- Create: `docs/DATA_FLOW_DIAGRAM.md`
- Create: `docs/DATA_CLASSIFICATION_INVENTORY.md`
- Modify: `docs/PROJECT_SOURCE_OF_TRUTH.md`
- Modify: `README.md`
- Modify: `PROJECT_STATUS.md`

- [ ] **Step 1: Write architecture ADRs**

`0013` must state:

- Supabase provides Postgres, Auth, and private Storage.
- Browser may use Supabase Auth and signed upload/download URLs only.
- All clinical reads/writes go through FastAPI.
- PostgreSQL RLS is defense-in-depth, not the only policy layer.
- FastAPI is the authoritative clinical policy boundary.

`0014` must state:

- Responsive web/PWA is the product direction.
- Do not recreate Vite/Capacitor/native shell app.
- Next.js app in `apps/therapist-app-v2/` remains canonical.

- [ ] **Step 2: Create threat model**

`docs/THREAT_MODEL.md` must include at least:

- assets: child identifiers, transcript text, audio, report snapshots, audit evidence, auth tokens, storage keys;
- actors: clinician, supervisor, org admin, platform operator, malicious tenant user, compromised browser, compromised worker, external provider;
- threats: IDOR, cross-tenant data exposure, consent bypass, fabricated ASR, audit loss, token replay, malicious upload, prompt/provider data leakage;
- mitigations: FastAPI policy boundary, care-team membership, signed URLs, RLS defense-in-depth, audit events, fail-closed provider behavior.

- [ ] **Step 3: Create data-flow diagram**

`docs/DATA_FLOW_DIAGRAM.md` must document:

- browser auth flow;
- upload intent flow;
- direct browser-to-private-storage upload;
- completion callback/API verification;
- worker/ASR flow;
- transcript review/attestation;
- feature extraction;
- report finalization/export;
- audit/observability flow.

- [ ] **Step 4: Create data classification inventory**

`docs/DATA_CLASSIFICATION_INVENTORY.md` must classify:

- child direct identifiers;
- pseudonymous case IDs;
- transcript text;
- audio files;
- report snapshots;
- audit evidence;
- provider metadata;
- operational logs.

For each item include allowed storage, retention, logging rule, export rule, deletion rule.

- [ ] **Step 5: Verify docs**

Run:

```bash
cd /Users/porschecaa/Desktop/asd-project
rg -n "Capacitor|native shell|Supabase|FastAPI|RLS|Threat|Data Flow|Data Classification" docs README.md PROJECT_STATUS.md
```

Expected: new docs are discoverable and do not contradict `docs/PROJECT_SOURCE_OF_TRUTH.md`.

### Task 3: Replace dictionary-style SQL repository with transactional repository

**Files:**

- Modify: `apps/api/app/repositories/sqlalchemy_repository.py`
- Create: `apps/api/app/repositories/base.py`
- Create: `apps/api/tests/test_sql_repository_transactions.py`
- Modify: service modules that mutate dictionaries directly.

Current problem:

- `SqlAlchemyRepository` still loads rows into in-memory dictionaries and saves snapshots.
- This is not production-safe for concurrent requests.
- Production requires per-record transactions, optimistic concurrency, and no full-database overwrite pattern.

- [ ] **Step 1: Define repository protocol**

Create `apps/api/app/repositories/base.py` with explicit methods such as:

```python
from typing import Protocol

class ClinicalRepository(Protocol):
    def get_case(self, case_id: str): ...
    def create_case(self, payload, actor_id: str): ...
    def update_case(self, case_id: str, patch, expected_version: int | None, actor_id: str): ...
    def list_cases_for_user(self, user_id: str, organization_id: str): ...
```

Do not keep adding product logic directly to public dictionaries.

- [ ] **Step 2: Add failing transaction tests**

Create tests proving:

- updating one case does not rewrite unrelated cases;
- expected version mismatch returns conflict;
- cross-tenant query does not return other org records;
- audit event is written in the same transaction as mutation.

Run:

```bash
cd /Users/porschecaa/Desktop/asd-project/apps/api
PYTHONPATH=. pytest tests/test_sql_repository_transactions.py -q
```

Expected before implementation: fail for missing methods/behavior.

- [ ] **Step 3: Implement transactional methods one workflow at a time**

Start with cases, sessions, transcripts, reports, audit events. Do not migrate every service at once.

- [ ] **Step 4: Remove production use of `create_all()`**

Current `SqlAlchemyRepository(... create_schema=True)` can call `Base.metadata.create_all`. Production must use Alembic only.

Add config guard:

- local tests may use schema creation;
- production `mock_mode=false` must reject automatic schema creation.

### Task 4: Implement organization and tenant model

**Files:**

- Modify: `apps/api/app/db/models.py`
- Add migration: `apps/api/app/db/migrations/versions/0006_add_organization_tenant_model.py`
- Modify: `apps/api/app/schemas/clinical.py`
- Modify: routes under `apps/api/app/api/v1/routes/`
- Create: `apps/api/tests/test_tenant_isolation.py`

Tables required:

- `organizations`
- `organization_settings`
- `user_profiles`
- `organization_memberships`
- `case_care_team_assignments`
- `identity_profiles`
- `regional_retention_policies`
- `consent_records`
- `notifications`
- `job_attempts`

- [ ] **Step 1: Add failing tenant isolation tests**

Test matrix:

- clinician cannot read other organization case;
- clinician cannot read case in same org without care-team membership;
- supervisor can read assigned care-team cases;
- org admin can manage membership but not bypass clinical content rules unless allowed;
- platform operator cannot read clinical content by default.

Run:

```bash
cd /Users/porschecaa/Desktop/asd-project/apps/api
PYTHONPATH=. pytest tests/test_tenant_isolation.py -q
```

- [ ] **Step 2: Add schema and migration**

Every clinical record needs `organization_id`.

Add indexes:

- `(organization_id, case_id)`
- `(organization_id, session_id)`
- `(organization_id, transcript_id)`
- `(organization_id, report_id)`
- membership indexes on `(organization_id, user_id)`.

- [ ] **Step 3: Add application-level tenant guards**

Every clinical endpoint must resolve organization and role in backend, not from browser-supplied role headers.

### Task 5: Implement Supabase Auth, invitation, MFA, roles, and care-team authorization

**Files:**

- Create: `apps/api/app/auth/supabase_auth.py`
- Create: `apps/api/app/auth/authorization.py`
- Modify: `apps/api/app/core/security.py`
- Create: `apps/api/tests/test_authorization_matrix.py`
- Modify frontend pages under `apps/therapist-app-v2/`.

Required roles:

- Clinician
- Clinical Supervisor
- Organization Admin
- Platform Operator

- [ ] **Step 1: Add failing auth tests**

Cover:

- missing/invalid token rejected;
- expired invitation rejected;
- revoked membership rejected;
- MFA required for real users;
- platform operator denied clinical content by default;
- break-glass access requires time limit, reason, audit event.

- [ ] **Step 2: Replace mock production auth**

Current `X-User-Id`, `x-mock-role`, and demo fallback remain useful for local demo, but production must fail closed if they are enabled.

Add runtime settings:

- `THERAPIST_APP_V2_AUTH_MODE=mock|supabase`
- production requires `supabase`.

- [ ] **Step 3: Add frontend flows**

Pages required:

- invitation accept;
- MFA setup;
- organization switcher;
- care-team assignment;
- access denied.

### Task 6: Implement private audio upload and durable ASR pipeline

**Files:**

- Modify: `apps/api/app/services/audio_job_service.py`
- Create: `apps/api/app/services/storage/supabase_private_storage.py`
- Create: `apps/api/app/tasks/celery_app.py`
- Create: `apps/api/app/tasks/outbox.py`
- Add migration: `apps/api/app/db/migrations/versions/0007_add_outbox_and_job_attempts.py`
- Create: `apps/api/tests/test_private_audio_storage.py`
- Create: `apps/api/tests/test_worker_outbox_idempotency.py`

Required API flow:

```text
create upload intent → direct browser upload → complete upload → enqueue processing
```

- [ ] **Step 1: Add failing storage tests**

Cover:

- upload intent requires active consent;
- generated URL is short-lived;
- API never receives audio bytes;
- completion verifies MIME, size, checksum, duration;
- expired URL fails closed.

- [ ] **Step 2: Add transactional outbox**

Job creation and enqueue must be atomic:

- create job row;
- create outbox event row;
- worker claims event with lease;
- retries do not duplicate transcripts.

- [ ] **Step 3: Add ASR provider adapter**

Required metadata:

- provider;
- model;
- version;
- region;
- timestamps;
- diarization support;
- warnings.

Production must reject mock provider and cross-region fallback.

- [ ] **Step 4: Add Thai/English/mixed benchmark protocol**

Create:

- `docs/ASR_BENCHMARK_PROTOCOL.md`
- tests for provider timeout, duplicate request, worker crash, revoked consent, expired URL.

### Task 7: Finish report exports and AI governance

**Files:**

- Modify: `apps/api/app/services/report_service.py`
- Create: `apps/api/app/services/report_export_service.py`
- Create: `apps/api/app/services/ai_sanitization_service.py`
- Create: `apps/api/tests/test_report_exports.py`
- Create: `apps/api/tests/test_ai_governance.py`

Remaining requirements:

- signed PDF export;
- Markdown export;
- reviewed CHAT export;
- organization-level AI opt-in;
- identifier sanitization before AI provider;
- provider/model/prompt/version/input hash/region retained for every AI draft;
- AI output editable/rejectable and never report-eligible automatically;
- prohibited diagnostic wording blocked.

- [ ] **Step 1: Add export tests**

Cover signed PDF, Markdown, reviewed CHAT, export timestamp, hash, signer.

- [ ] **Step 2: Add AI governance tests**

Cover opt-in, sanitization, provenance, rejectability, diagnostic wording block.

### Task 8: Finish operations and security controls

**Files:**

- Modify: `apps/api/app/core/config.py`
- Create: `apps/api/app/services/notification_delivery.py`
- Create: `apps/api/app/services/retention_policy_service.py`
- Create: `apps/api/tests/test_notification_delivery.py`
- Create: `apps/api/tests/test_retention_policy.py`

Remaining requirements:

- actual notification/email provider abstraction;
- delivery retry state;
- provider allowlist in production;
- no clinical content in delivered messages;
- managed rate limit integration;
- backup/PITR provider check;
- restore drill evidence;
- incident drill evidence;
- consent deletion drill evidence;
- external security review tracking;
- key rotation execution evidence.

- [ ] **Step 1: Implement notification delivery safely**

Use existing `notification_safety.py` before any provider call.

Production config must require approved provider:

- SES;
- SendGrid;
- Postmark;
- Resend;
- equivalent approved provider.

- [ ] **Step 2: Implement retention policy service**

Policy inputs:

- organization;
- country;
- legal hold;
- consent status;
- record type.

Policy outputs:

- retain until;
- deletion review required;
- export allowed;
- audit evidence retention.

### Task 9: Build CI/CD and infrastructure

**Files:**

- Modify: `.github/workflows/deploy.yml`
- Create: `.github/workflows/production-smoke.yml`
- Create: `infra/terraform/`
- Create: `docs/DEPLOYMENT_RUNBOOK.md`
- Create: `docs/COUNTRY_ALLOWLIST.md`

Remaining requirements:

- separate dev/staging/prod projects;
- Terraform provisioning;
- managed containers for FastAPI and workers;
- frontend managed hosting without clinical edge cache;
- rolling deployments;
- expand → migrate → contract migration discipline;
- smoke tests after deploy;
- automatic rollback;
- country allowlist gate.

- [ ] **Step 1: Add deployment smoke tests**

Smoke test must verify:

- auth;
- organization isolation;
- upload intent;
- job enqueue;
- transcript draft creation;
- report signoff/export;
- audit write;
- observability event.

- [ ] **Step 2: Add Terraform skeleton**

Start with variables and modules for:

- API service;
- worker service;
- Redis;
- secrets;
- observability;
- Supabase project references;
- frontend environment.

### Task 10: Frontend production flows

**Files:**

- Modify: `apps/therapist-app-v2/`
- Create tests under `apps/therapist-app-v2/src/__tests__/`

Remaining pages/flows:

- Supabase login;
- invitation accept;
- MFA setup;
- organization switcher;
- access denied;
- care-team assignment;
- upload intent/direct upload UI;
- transcript review persistence after refresh/re-login;
- report finalization with concurrency token;
- notification center.

- [ ] **Step 1: Replace fail-open browser fallback**

Production frontend must fail closed if API unavailable. It must not use `sessionStorage` to bypass backend safety gates.

- [ ] **Step 2: Add organization switcher**

Only show switcher for users with multiple memberships. Organization selection must be sent to backend as context but backend must still resolve authorization.

### Task 11: Controlled launch preparation

**Files:**

- Create: `docs/CONTROLLED_LAUNCH_PLAN.md`
- Create: `docs/DESIGN_PARTNER_CHECKLIST.md`
- Create: `docs/WEEKLY_ROLLOUT_METRICS.md`

Launch sequence:

1. internal alpha with synthetic data;
2. first design-partner clinic under agreement;
3. expand one organization at a time;
4. weekly review of tenant isolation, support load, ASR latency, report rejection rate, incident rate;
5. stop rollout for cross-tenant exposure, consent bypass, audit loss, fabricated ASR output;
6. country expansion only after legal/privacy/vendor/region review.

## Production readiness gates still missing

The system is not production-ready until each gate below has direct evidence:

- [ ] External security review has no unresolved critical/high findings.
- [ ] Dependency audit has no unresolved critical/high production findings.
- [ ] Supabase Auth and MFA are active in staging and production.
- [ ] Public signup is disabled; invitation-only onboarding works.
- [ ] Tenant isolation tests pass against SQL/Postgres.
- [ ] PostgreSQL RLS policies exist and are tested as defense-in-depth.
- [ ] Private Supabase Storage is used for audio.
- [ ] Browser uploads directly to storage using short-lived signed URLs.
- [ ] Celery/Redis workers handle retry, timeout, lease, dead-letter, and idempotency.
- [ ] ASR provider is approved per region and never falls back to mock in production.
- [ ] Thai/English/mixed ASR benchmark protocol is approved by Clinical Safety Owner.
- [ ] Final reports export signed PDF, Markdown, and reviewed CHAT.
- [ ] Production observability provider is connected and critical alerts are routed.
- [ ] Backup/PITR restore drill succeeds within RPO 15 minutes and RTO 4 hours.
- [ ] Consent withdrawal/deletion drill succeeds without deleting audit/sign-off evidence.
- [ ] Rolling deploy and rollback are proven without workflow data loss.
- [ ] Country allowlist gate exists and is enforced.
- [ ] Controlled launch plan is approved before real clinic data.

## Commands future agents should use

Backend full suite:

```bash
cd /Users/porschecaa/Desktop/asd-project/apps/api
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest -q
```

Root production-hardening checks:

```bash
cd /Users/porschecaa/Desktop/asd-project
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/security_scan.py
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/check_repo_consistency.py
PYTHONPYCACHEPREFIX=/tmp/codex-pycache PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/check_api_migrations.py
git diff --check
```

Frontend commands:

```bash
cd /Users/porschecaa/Desktop/asd-project/apps/therapist-app-v2
npm test
npm run build
```

Full local verification:

```bash
cd /Users/porschecaa/Desktop/asd-project
bash scripts/check_project.sh
```

## Rules future agents must not violate

- Do not add product endpoints under `src/therapist_backend/` or `src/clinical_workflow/`.
- Do not recreate `therapist-clinician-app/`.
- Do not commit `.next/`, `dist/`, `.local/`, `node_modules/`, or `*.tsbuildinfo`.
- Do not log or fixture real child names, surnames, direct identifiers, transcript text, audio bytes, or storage keys.
- Do not claim ASD diagnosis, Thai clinical validation, or automated clinical decision-making.
- Do not treat green local tests as proof of production readiness.
- Do not use mock headers, mock ASR, local storage, or JSON repository in production mode.
- Do not delete audit/sign-off evidence automatically for privacy deletion requests.

## Recommended handoff order for another AI

1. Verify and commit the current dirty production-hardening branch.
2. Finish Phase 0 docs and ADRs.
3. Implement organization/tenant schema and tenant isolation tests.
4. Replace dictionary-style SQL repository with transactional repository.
5. Implement Supabase Auth/invitation/MFA/care-team authorization.
6. Implement Supabase private storage and Celery/Redis outbox workers.
7. Integrate approved ASR provider and ASR benchmark protocol.
8. Finish report export and AI governance.
9. Build CI/CD/Terraform/deployment smoke tests.
10. Build frontend production auth/org/upload/report flows.
11. Run controlled alpha and design-partner launch gates.

The goal remains active and incomplete until the production readiness gates above are met with evidence.
