# Phase 1 External Blockers

Date: 2026-06-25

The local Phase 1 tenant isolation foundation is in place, but full production
completion is blocked on external infrastructure and decisions. Do not represent
the system as production-ready until these are resolved and verified.

## Blocking Items

- Supabase project selection for staging and production.
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
- Legal/privacy approval for first real clinic tenant, country allowlist, and
  vendor/region choices.

## Exact Next Actions

1. Create separate Supabase staging and production projects.
2. Configure Supabase JWT/custom claims to match
   `docs/SUPABASE_AUTH_CONTRACT.md`.
3. Add a staging-only RLS verification test that seeds two organizations and
   proves cross-tenant reads/writes fail using real Auth claims.
4. Replace the local HS256 scaffold with the approved production Supabase token
   verification method if the project uses JWKS/asymmetric signing.
5. Wire the backend invitation, MFA, membership revocation, and break-glass
   workflow to real Supabase Auth/custom claims and frontend admin flows after
   the auth claim contract is deployed in Supabase.

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
- Tenant isolation tests covering clinician, supervisor, org admin, platform
  operator, production auth fail-close, RLS migration coverage, and audit event
  tenant tagging.
