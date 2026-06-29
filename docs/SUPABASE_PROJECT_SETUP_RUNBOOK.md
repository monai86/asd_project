# Supabase Project Setup Runbook

Date: 2026-06-28

This runbook turns the first-launch Supabase infrastructure decisions into an
operator checklist. It covers the external setup needed before the repository's
staging auth and tenant-safety verification can proceed.

Launch decision:
[docs/adr/0017-launch-controlled-single-clinic-supabase-rollout.md](/Users/porschecaa/lingualens/docs/adr/0017-launch-controlled-single-clinic-supabase-rollout.md)

Launch tracker:
[docs/PRODUCTION_SAAS_LAUNCH_TRACKER.md](/Users/porschecaa/lingualens/docs/PRODUCTION_SAAS_LAUNCH_TRACKER.md)

Auth rollout tracker:
[docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md)

Staging auth verification:
[docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md)

Setup evidence template:
[docs/templates/SUPABASE_PROJECT_SETUP_EVIDENCE_TEMPLATE.md](/Users/porschecaa/lingualens/docs/templates/SUPABASE_PROJECT_SETUP_EVIDENCE_TEMPLATE.md)

## Fixed Launch Inputs

These values are already decided for the first rollout:

- Supabase organization name: `LinguaLens`
- Staging project name: `lingualens-staging`
- Production project name: `lingualens-production`
- Region for both projects: `ap-southeast-1`
- Launch scope: one clinic organization first
- Public signup: off
- Login path: email/password plus required TOTP MFA
- Production auth mode: Supabase only

## Current External State

Confirmed on 2026-06-28 from the operator-provided dashboard state and recorded
evidence:

- organization `LinguaLens` exists
- staging project `lingualens-staging` exists in `ap-southeast-1`
- production project `lingualens-production` exists in `ap-southeast-1`
- staging project ref: `cbhwxklvcpgizeqriqxi`
- production project ref: `rftslmbgbudqsypknzss`

Operational consequence:

- project creation is no longer the active blocker
- the active blocker is that the installed Supabase connector still returns a
  permission mismatch for this org/project set, so dashboard/manual operator
  execution remains required for live configuration and evidence capture

## Operator Prerequisites

- A Supabase account with permission to create an organization and projects.
- Named owners for:
  - engineering/product approval
  - legal/privacy approval
  - primary infrastructure operator
- A decision log location for:
  - project refs
  - dashboard URLs
  - billing owner
  - incident/rollback contact

Create the evidence file for this setup run first:

```bash
bash scripts/create_supabase_project_setup_evidence.sh
```

Optional slug:

```bash
bash scripts/create_supabase_project_setup_evidence.sh initial-lingualens-org
```

By default the script writes to `docs/release_artifacts/project_setup/` and
prefills the date plus current git short SHA when available.

## Step 1. Confirm The Supabase Organization Record

This step is now a confirmation step, not a creation step.

Confirm the existing organization record:

- Name: `LinguaLens`
- Dashboard URL:
  `https://supabase.com/dashboard/org/whgbnlqvrgjodiquclnr/general`
- Billing/owner contact: assigned human owner
- Notes: first controlled clinic rollout for Thailand

Record after confirmation:

- organization ID
- organization slug
- owner contact
- plan/subscription class

Completion check:

- `LinguaLens` appears in the dashboard and the setup evidence
- the organization owner is a named launch approver
- if Codex connector access does not refresh to include the new organization,
  record the permission mismatch in the setup evidence and continue manually in
  the dashboard

## Step 2. Confirm Staging And Production Projects

Confirm both projects inside the `LinguaLens` organization:

| Environment | Name | Region | Required now |
|---|---|---|---|
| staging | `lingualens-staging` | `ap-southeast-1` | yes |
| production | `lingualens-production` | `ap-southeast-1` | yes |

Record for each existing project:

- project ref
- dashboard URL
- API URL
- issuer URL
- JWKS URL
- publishable key reference location
- service-role secret storage location

Completion check:

- both projects exist
- both projects are in `ap-southeast-1`
- both projects are attached to `LinguaLens`
- if connector-based cost/project management is unavailable, capture project
  refs manually from the dashboard and continue with the same evidence package

## Step 3. Baseline Auth Configuration

Apply the minimum launch auth baseline on both projects:

- enable email/password auth
- disable public signup
- disable anonymous sign-ins
- enable MFA/TOTP
- keep invitation-only onboarding through the backend-controlled membership
  flow
- record the issuer format:
  `https://<project-ref>.supabase.co/auth/v1`
- record the chosen JWT verification path:
  - `jwks_url`
  - `jwks_json`
  - `hs256_shared_secret`

Completion check:

- existing users can sign in
- new public self-signup is not available
- MFA enrollment/challenge path is available

## Step 4. Record Runtime Inputs

For each project, capture the values needed by the maintained runtime.

Backend verifier inputs for `apps/api`:

- `THERAPIST_APP_V2_SUPABASE_JWT_ISSUER`
- `THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE`
- `THERAPIST_APP_V2_SUPABASE_JWT_VERIFICATION_MODE`
- `THERAPIST_APP_V2_SUPABASE_JWT_JWKS_URL` if using remote JWKS
- `THERAPIST_APP_V2_SUPABASE_JWT_JWKS_JSON` only if using injected JWKS
- secret-store location for the service role and any HS256 secret if used

Frontend browser inputs for `apps/lingualens-app`:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Do not store raw secrets in repository files.

Completion check:

- the staging API deployment can be configured without placeholder values
- the staging frontend deployment can be configured without placeholder values
- verifier mode is explicitly chosen, not inferred later

## Step 5. Prepare The Staging Verification Path

Before any production promotion work, complete these in order:

1. Configure staging API with `THERAPIST_APP_V2_AUTH_MODE=supabase`.
2. Run
   [docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md)
   and save evidence under `docs/release_artifacts/auth_verifier/`.
3. Run
   [docs/STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md)
   and save evidence under `docs/release_artifacts/tenant_safety/`.

Completion check:

- auth verifier evidence exists
- tenant-safety evidence exists
- both evidence packages reference the same staging project ref and commit SHA

## Decision Log Template

Record these fields for both staging and production:

| Field | Staging | Production |
|---|---|---|
| Organization name | `LinguaLens` | `LinguaLens` |
| Organization ID | `whgbnlqvrgjodiquclnr` | `whgbnlqvrgjodiquclnr` |
| Project name | `lingualens-staging` | `lingualens-production` |
| Project ref | `cbhwxklvcpgizeqriqxi` | `rftslmbgbudqsypknzss` |
| Region | `ap-southeast-1` | `ap-southeast-1` |
| Dashboard URL | `https://supabase.com/dashboard/project/cbhwxklvcpgizeqriqxi` | `https://supabase.com/dashboard/project/rftslmbgbudqsypknzss` |
| API URL | `https://cbhwxklvcpgizeqriqxi.supabase.co` | `https://rftslmbgbudqsypknzss.supabase.co` |
| Issuer URL | `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1` | `https://rftslmbgbudqsypknzss.supabase.co/auth/v1` |
| JWKS URL | `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1/.well-known/jwks.json` | `https://rftslmbgbudqsypknzss.supabase.co/auth/v1/.well-known/jwks.json` |
| Auth mode | `supabase` | `supabase` |
| JWT verifier mode | `jwks_url` | `jwks_url` |
| Public signup | `off` | `off` |
| MFA/TOTP | `on` | `on` |
| Publishable key | `sb_publishable_zC7wscUPHNtoqQb4amCEEQ_K2dCC5si` | `sb_publishable_Yrk22_dt_oSdAa0ov-FGCA_-ZBylare` |
| Owner | pending named human owner | pending named human owner |
| Billing contact | pending named human owner | pending named human owner |

Store the completed setup record under
`docs/release_artifacts/project_setup/` and reference that path from later
auth-verifier and tenant-safety evidence packages.

For copy/paste runtime env snippets after project setup, use:

```bash
bash scripts/create_supabase_runtime_env_snippets.sh
```

## References

- Supabase Auth general configuration:
  [supabase.com/docs/guides/auth/general-configuration](https://supabase.com/docs/guides/auth/general-configuration)
- Supabase TOTP MFA:
  [supabase.com/docs/guides/auth/auth-mfa/totp](https://supabase.com/docs/guides/auth/auth-mfa/totp)
- Supabase JWT and JWKS verification:
  [supabase.com/docs/guides/auth/jwts](https://supabase.com/docs/guides/auth/jwts)
