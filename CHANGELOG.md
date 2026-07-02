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
- Added a lingualens Settings/Admin Pilot Access Lifecycle console for
  backend-backed invitation creation, membership review, and membership
  revocation, with production-path guardrails visible in the frontend.
- Extended the Settings/Admin Pilot Access Lifecycle console with local
  invitation acceptance into active membership and invited `aal1` session
  preparation so the MFA gate can be exercised in the maintained frontend.
- Added an explicit active-organization session switcher in the maintained
  shell for multi-org mock users, keeping one active organization per session.
- Added a runtime-aware login surface that keeps mock access simulation for
  local auth mode and uses a real browser-side Supabase email/password sign-in
  plus recovery-email path in `supabase` auth mode when browser config is
  present.
- Added frontend Supabase workspace gating so signed-out, `aal1`, and explicit
  org-selection-required states block app routes instead of reusing the mock
  workspace path.
- Added a frontend browser-auth bridge that can normalize a Supabase-like
  session payload into the invitation/MFA/org access-state scaffold used by the
  maintained shell, including initial session restore and auth-state syncing
  from `@supabase/supabase-js`.
- Added frontend persistence for explicit active-organization selection and
  switch-back flow so multi-org Supabase sessions keep one active organization
  per session across refreshes.
- Added a browser-side Supabase TOTP MFA panel for `aal1` workspace gates so
  users can enroll a TOTP factor, verify the authenticator code, and elevate
  the current session to `aal2` without falling back to mock controls.
- Added frontend API auth-header switching so `supabase` runtime requests use
  the current bearer token and active organization context instead of default
  demo headers.
- Added authenticated audio blob loading for protected backend media playback in
  `supabase` runtime, avoiding raw file URLs that cannot carry bearer auth.
- Added authenticated backend upload handling for relative audio-upload routes in
  `supabase` runtime while leaving absolute signed upload URLs free of app auth
  headers.
- Added configurable Playwright smoke-test ports so the maintained therapist
  workflow browser smoke can run on alternate localhost ports when `8000` or
  `3100` are already occupied.
- Added Clinical Speech Artifact Package quality reports that compare ASR draft
  CHAT against reviewed CHAT using WER, CER, speaker-label accuracy, and
  line edit burden, and canonical feature drift without invoking ML decision
  support.
- Added a Clinical Speech Artifact benchmark reporter for multi-session
  ASR-draft-versus-reviewed-CHAT evaluation, producing JSON and CSV summaries
  for WER, CER, speaker-label accuracy, line edit rate, and feature drift.
- Added a diarization runtime readiness check that reports whether pyannote,
  speechbrain embedding diarization, pitch fallback, or no backend is available
  before running audio jobs.

### Changed
- Kept report-draft generation available after therapist transcript attestation
  and feature extraction even when ML readiness/evidence review is unavailable,
  preserving AI/reference outputs as non-essential launch paths.

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
