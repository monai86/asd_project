# Phase 1 External Blockers

Date: 2026-06-28

The local Phase 1 tenant isolation foundation is in place, but full production
completion is blocked on external infrastructure and decisions. Do not represent
the system as production-ready until these are resolved and verified.

## Blocking Items

- As of 2026-06-30, no additional mandatory repository-local launch blocker is
  known ahead of the next staging handoff; the remaining blockers below are
  external environment, provider, or approval dependencies.
- Real Supabase connector access for the current Codex runtime still does not
  include the `LinguaLens` organization or its projects, so dashboard/manual
  operator execution remains required for live setup and verification.
- Real Supabase Auth custom-claims provisioning matching
  `docs/SUPABASE_AUTH_CONTRACT.md`.
- Managed Postgres RLS verification using real Supabase Auth claims, not local
  mock headers.
- Real Supabase invitation delivery, MFA enrollment UI, and custom-claim
  synchronization with the backend invitation/membership workflow.
- Managed private Storage bucket configuration, signed URL policy, and retention
  controls.
- Managed Redis/Celery or equivalent durable worker account and deployment
  target.
- Managed secret-store provider and rotation procedure for production
  credentials.
- Legal/privacy approval for the first real clinic tenant, Thailand-only
  country allowlist, and vendor/region choices.

## Exact Next Actions

1. Complete staging runtime wiring and verifier-shell preparation from
   [docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md)
   and
   [docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md](/Users/porschecaa/lingualens/docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md).
   Preferred operator path:
   - `bash scripts/create_staging_verification_env.sh`
   - edit the generated file with real staging URLs, org/case IDs, and tokens
   - `bash scripts/validate_staging_verification_env.sh <generated-env-file>`
2. Configure the live Supabase auth baseline in staging and production:
   - public signup `off`
   - email/password `on`
   - anonymous sign-in `off`
   - TOTP MFA `on`
3. Configure Supabase JWT/custom claims to match
   `docs/SUPABASE_AUTH_CONTRACT.md`.
4. Execute
   [docs/STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md)
   against staging, including a staging-only RLS verification pass that seeds
   two organizations and proves cross-tenant reads/writes fail using real Auth
   claims. Capture the resulting evidence package plus the probe summary
   artifact from `scripts/run_staging_tenant_safety_core_gate.sh`.
5. Replace the local HS256 scaffold with the approved production Supabase token
   verification method if the project uses JWKS/asymmetric signing.
6. Wire the backend invitation, MFA, membership revocation, and break-glass
   workflow to real Supabase Auth/custom claims and frontend admin flows after
   the auth claim contract is deployed in Supabase.
7. Prove Supabase private Storage, signed upload expiry, upload completion
   verification, and durable queue/worker behavior in staging with the same
   architecture class planned for production.

## Local Work Already Completed

- SQL tenant model/RLS scaffold through `0009_add_tenant_rls_policies`; active
  Alembic head is now `0010_add_auth_lifecycle_tables`.
- Backend clinical route guards for organization, role, and care-team access.
- Production auth fail-close behavior for non-mock auth mode.
- Local Supabase Auth scaffold and JWT claim contract in
  `docs/SUPABASE_AUTH_CONTRACT.md`.
- Backend local organization membership and case care-team assignment APIs with
  org-admin guards.
- Backend invitation lifecycle, membership revocation, production MFA/invitation
  fail-closed guards, and scoped audited break-glass case access.
- Tenant isolation tests covering therapist, supervisor, org admin, platform
  operator, production auth fail-close, RLS migration coverage, and audit event
  tenant tagging.
