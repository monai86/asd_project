# Phase 1 External Readiness Gates

Last reviewed: 2026-08-16

The local Phase 1 tenant isolation foundation is in place, but full production
completion is blocked on external infrastructure and decisions. Do not represent
the system as production-ready until these are resolved and verified.

## Blocking Items

- As of 2026-08-16, no additional mandatory repository-local launch blocker is
  known ahead of the next staging handoff; the remaining blockers below are
  external environment, provider, or approval dependencies.
- Vercel, Render, and Supabase have been manually wired and runtime-smoke-tested
  during the operator handoff. This proves reachability only; it is not evidence
  that tenant isolation, Auth claims, Storage policies, or clinical rollout
  controls are production-ready.
- Real Supabase Auth custom-claims provisioning matching
  `docs/SUPABASE_AUTH_CONTRACT.md`.
- Managed Postgres RLS verification using real Supabase Auth claims, not local
  mock headers.
- Real Supabase invitation delivery, MFA enrollment UI, and custom-claim
  synchronization with the backend invitation/membership workflow.
- Managed private Storage bucket configuration, signed URL policy, and retention
  controls.
- Managed secret-store provider and rotation procedure for production
  credentials.
- Legal/privacy approval for the first real clinic tenant, Thailand-only
  country allowlist, and vendor/region choices.

Redis, Celery, or another dedicated queue is not a Phase 1 readiness blocker.
Analysis should remain synchronous while execution time is acceptable. If
asynchronous processing becomes necessary, use the existing database-backed job
model and one worker first; introduce a dedicated queue only after measured
workload shows that approach is insufficient.

## Exact Next Actions

1. Refresh and validate the staging verifier environment from
   [docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md)
   and
   [docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md](/Users/porschecaa/lingualens/docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md).
   Preferred operator path:
   - `bash scripts/create_staging_verification_env.sh`
   - edit the generated file with real staging URLs, org/case IDs, and tokens
   - `bash scripts/validate_staging_verification_env.sh <generated-env-file>`
2. Reconfirm the live Supabase auth baseline in staging and production:
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
   verification, and retention behavior in staging with the same architecture
   class planned for production.
8. Measure synchronous analysis latency before selecting an asynchronous job
   architecture. If a worker is needed, verify the existing database-backed job
   transitions and one-worker recovery behavior before evaluating a dedicated
   queue.

## Local Work Already Completed

- SQL tenant model/RLS scaffold through `0009_add_tenant_rls_policies`; active
  Alembic head is now `0012_add_report_runtime_fields`.
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
- Vercel web deployment, Render API health, Supabase-backed authentication, and
  the maintained therapist workflow have passed operator smoke checks. These
  checks do not replace the real-claim two-organization RLS evidence required
  above.
- The analysis-only transcript contract is available under
  `packages/analysis_contract/` and `packages/cha/`, but it intentionally owns
  no API, database, storage, authentication, or queue behavior and is not wired
  into production jobs.
