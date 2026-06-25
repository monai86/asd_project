# Changelog

## Unreleased

### Added
- Added backend-generated signed report snapshot metadata for signed-off
  reports, including signer, signed timestamp, report version, SHA-256 report
  hash, and export metadata on report exports.
- Added draft report revision creation when editing a signed-off report, keeping
  the original signed snapshot immutable for audit.
- Added an explicit opt-in gate for non-template AI report drafting providers,
  with provider and input-hash provenance recorded on report drafts.
- Added configurable in-memory API rate limiting with safe generic 429
  responses as a production-hardening foundation.
- Added CI repository consistency, secret scanning, and report-only dependency
  audit steps as security-hardening foundations.
- Hardened structured API request logging to record route templates or sanitized
  paths instead of raw record IDs or sensitive URL segments.
- Added configurable CORS origins with production validation and an Origin guard
  for unsafe browser-origin requests.
- Added production runtime validation that rejects demo/default database or
  Redis URLs, local repositories, local storage, and in-memory queues.
- Added an API migration smoke check and backup/restore runbook with RPO/RTO
  restore drill expectations.
- Added an incident-response runbook with stop-rollout criteria for
  cross-tenant exposure, consent bypass, audit loss, and fabricated ASR output.
- Added notification/email safety validation for generic operational messages
  without clinical content or direct identifiers.
- Added audit event shape validation with actor, outcome, correlation ID, and
  clinical-content blocking before persistence.
- Added production observability validation requiring an approved provider,
  critical alert route, and privacy-safe telemetry metadata.
- Added privacy operation retention/legal-hold metadata and deletion-review
  completion safeguards that preserve audit/sign-off evidence.
- Added production secret-store and credential-rotation runtime validation plus
  a secret rotation runbook.
- Added one-day production-like pilot scope/runbook, local/SQL tenant
  scaffolding, backend organization/care-team guards for core clinical records,
  local-private upload intents, and a production auth-mode fail-closed guard.
- Added Phase 1 tenant isolation foundation with organization settings,
  membership/care-team assignment, identity, retention, consent, notification,
  job-attempt SQL tables, organization-scoped clinical child records, broader
  backend tenant guards, PostgreSQL RLS migration SQL, and tests for clinician,
  supervisor, org admin, platform operator, production auth fail-close, and RLS
  coverage.
- Added a backend Supabase Auth scaffold with HS256 bearer-token verification,
  production JWT secret/issuer runtime guards, mock-header bypass protection,
  invitation/MFA/membership checks, break-glass claim validation, and a frozen
  local auth contract in `docs/SUPABASE_AUTH_CONTRACT.md`.
- Added backend organization-admin membership and case care-team assignment
  endpoints with org-admin-only guards, cross-tenant denial, audit tagging, and
  tests proving newly assigned clinicians can access assigned cases.
- Added transactional SQL persistence for organization memberships and case
  care-team assignments, including same-transaction audit writes and case
  care-team updates.
- Added backend-only Phase 2 auth lifecycle workflow endpoints for
  organization invitations, invitation acceptance into active membership,
  membership revocation, scoped audited break-glass case access, and production
  Supabase MFA/invitation fail-closed runtime guards.
- Added a Therapist App v2 Settings/Admin Pilot Access Lifecycle console for
  backend-backed invitation creation, membership review, and membership
  revocation, with production-path guardrails visible in the frontend.

## [v1.6.3] - 2026-06-21

### Changed
- Replaced therapist Cases pages with backend-backed case and timeline views,
  while keeping seeded fallback content only for offline/demo continuity.
- Replaced the placeholder Reports page with a persisted report index that opens
  draft or finalized reports from the active API workspace.
- Aligned maintained therapist-product metadata across the therapist app,
  shared package, API OpenAPI version, and report audit provenance.
- Removed obsolete demo surfaces, legacy benchmark pipelines, stale benchmark
  artifacts, and outdated summary documents from the working tree so the
  repository points only to the current therapist workflow and current
  reference-evidence ML path.
- Refreshed maintained documentation and repository checks to describe only the
  current runtime, current ML workflow, and current verification path.

### Fixed
- Accepted the therapist frontend `X-User-Id` header in the active API security
  dependency to remove auth-contract drift between the canonical frontend and
  backend.
