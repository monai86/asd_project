# Project Status

Current maintained version: `v1.6.3`.

This project is an AI-assisted speech-language clinical decision-support prototype for therapist review, language sample analysis, transcript QA, guideline-linked interpretation, and Progress Report generation. It is not a diagnostic device and has not been clinically validated for Thai children.

## Current Deliverable Status

- lingualens (`apps/lingualens-app` + `apps/api`): primary deliverable
  and main demo surface.
- Python ML and audio pipeline: research and prototype support code, not a
  deployed clinical system.
- Legacy benchmark and demo surfaces removed from the working tree to keep the
  repository aligned with the current therapist workflow.
- Legacy Vite/Capacitor therapist app: removed from Git.
- Legacy `src/therapist_backend`: retained only for research compatibility and
  its existing tests.

## Current Strengths

- Human-in-the-loop transcript review and sign-off workflow.
- Mock/demo mode with seeded therapist cases and sessions.
- Reviewed-only report eligibility boundary for decision-support outputs.
- Shared Guideline Mapping Catalog for feature-to-construct mapping.
- Safety wording that separates research model results from clinical decision support.
- One documented runtime source of truth shared across Codex and Antigravity.
- Gate 1 reference-evidence candidate passes the engineering promotion gate,
  while clinical and diagnostic claims remain explicitly blocked.
- Phase 0 production architecture freeze artifacts are documented: Supabase
  Auth/Postgres/private Storage plus FastAPI as clinical policy boundary,
  responsive web/PWA-only direction, threat model, data-flow diagram, and data
  classification inventory.
- One-day production-like pilot scope is documented in
  `docs/ONE_DAY_PILOT_SCOPE.md` and `docs/ONE_DAY_PILOT_RUNBOOK.md`, with
  local/SQL tenant scaffolding, backend organization/care-team guards, and
  local-private upload intents for pilot use only.
- Phase 1 tenant isolation foundation now includes SQL model/migration support
  for organization settings, memberships, care-team assignments, identity
  profiles, retention policies, consent records, notifications, job attempts,
  organization-scoped clinical child records, broader backend route guards, and
  PostgreSQL RLS policy SQL as defense-in-depth.
- Phase 2 auth foundation now includes a backend Supabase Auth scaffold,
  JWT claim contract, production JWT secret/issuer guard, invitation/MFA/active
  membership checks, break-glass claim validation, backend invitation lifecycle,
  membership revocation, scoped audited break-glass case access, and a Therapist
  App v2 Settings/Admin Pilot Access Lifecycle console for local admin workflow
  demonstration.
- Backend organization-admin endpoints can add/list local memberships and assign
  case care-team members with cross-tenant denial and audit tenant tagging.
- Full local verification currently passes via `scripts/check_project.sh`,
  including repository consistency, secret scan, Python core tests, API migration
  smoke to Alembic head, Therapist App v2 tests, and production build.

## Current Limitations

- The system does not diagnose ASD and cannot confirm or rule out ASD.
- The model was evaluated on public English-language datasets, not validated as a clinical model for Thai children.
- The audio-to-CHAT pipeline is experimental and requires therapist transcript review.
- Guideline-linked findings provide construct linkage and review cues only; no project-verified Thai thresholds or norms are applied.
- Acoustic/prosody features are exploratory/display-only unless separately validated.
- SQL persistence, production authentication, durable workers, monitoring, and
  managed private object storage still require production hardening beyond the
  one-day pilot, Phase 1 tenant/RLS foundation, and local Supabase Auth
  scaffold.
- Gate 1 is an engineering validation on proxy labels and public English
  corpora, not clinical validation.
- lingualens currently uses Next.js 14.2.35. Production dependency audit
  reports high/moderate advisories whose automated fix requires a breaking
  Next.js major upgrade; this must be resolved before public production
  deployment.
- Therapist App v2 verification still emits non-blocking test/build warnings
  from jsdom navigation gaps, React test `act(...)` coverage, deprecated Vite
  CJS API usage, and a React hook dependency warning in the session workspace.
- AI report drafting through non-template providers is gated behind explicit
  opt-in and records provider/input provenance, but full vendor governance,
  region controls, and legal review are still required before production use.
- API rate limiting now has an opt-in in-memory foundation with generic 429
  responses; public production still needs managed edge/API-gateway enforcement
  and alerting.
- CI now includes repository consistency and secret scanning before test/deploy
  jobs. Dependency audit steps are present but report-only until known
  production advisories are resolved.
- Structured API request logging now records route templates or sanitized paths
  and suppresses INFO-level HTTP access logs that can include raw clinical URLs.
- CORS allowed origins are now server-configurable, production rejects wildcard
  or empty origins, and unsafe browser-origin writes are protected by an Origin
  guard.
- Production runtime validation now rejects demo/default database or Redis URLs,
  local repositories, local storage, and in-memory queues when mock mode is off.
- API migration smoke checks now verify Alembic head on a fresh database, and
  `docs/BACKUP_RESTORE_RUNBOOK.md` defines the RPO/RTO restore drill gate.
- `docs/INCIDENT_RESPONSE_RUNBOOK.md` now defines stop-rollout criteria for
  cross-tenant exposure, consent bypass, audit loss, and fabricated ASR output.
- Notification/email safety now has a backend validator that blocks child
  identifiers, transcript text, audio/storage keys, raw filenames, and clinical
  content from outbound operational messages.
- Audit events now carry actor, action, target, outcome, timestamp, and
  correlation ID fields with backend validation against clinical content.
- Production observability now requires an approved provider and critical alert
  route when mock mode is off, with backend validation for privacy-safe telemetry
  metadata.
- Privacy deletion-review requests now include retention days, legal-hold state,
  eligible deletion timestamps, completion timestamps, and retained-evidence
  summaries while preserving audit/sign-off evidence.
- Production runtime validation now requires an approved managed secret-store
  provider and credential rotation runbook reference when mock mode is off.
- Phase 0 architecture artifacts are written and Phase 1 tenant/RLS plus Phase
  2 auth scaffolds exist locally, including backend invitation/revocation and
  audited break-glass workflow foundations, but implementation evidence is still
  missing for real Supabase Auth/MFA project configuration, managed Postgres RLS
  verification, private Storage, durable workers, provider integrations,
  infrastructure, and controlled rollout gates.

## Canonical Demo Path

The recommended demo path is the Therapist Five-Step Workflow:

1. Open case
2. Add session
3. Upload file
4. Review transcript
5. Generate Progress Report

See `docs/PROJECT_SOURCE_OF_TRUTH.md` for the exact active/legacy boundaries.
