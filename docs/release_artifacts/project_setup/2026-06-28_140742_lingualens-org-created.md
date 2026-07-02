# Supabase Project Setup Evidence

- Date: 2026-06-28
- Commit: 3537259e
- Operator: Porsche
- Reviewer:
- Result: in_progress

## Preconditions

- [ ] Launch decision is accepted in `docs/adr/0017-launch-controlled-single-clinic-supabase-rollout.md`.
- [ ] Target organization name is `LinguaLens`.
- [ ] Target projects are `lingualens-staging` and `lingualens-production`.
- [ ] Target region for both projects is `ap-southeast-1`.

## Organization Record

| Field | Value | Notes |
|---|---|---|
| Organization name | `LinguaLens` |  |
| Organization ID | `whgbnlqvrgjodiquclnr` | Confirmed from dashboard URL shared by operator. |
| Organization slug | `whgbnlqvrgjodiquclnr` | Dashboard URL uses org slug path. |
| Plan/subscription | `FREE` | Captured from operator screenshot in the dashboard chrome. |
| Owner contact | pending named human owner | Project/org refs are known; named launch owner still needs human assignment. |

## Named Owners

| Role | Contact | Notes |
|---|---|---|
| Engineering/product approver | pending named human owner | Required before go-live approval can close. |
| Legal/privacy approver | pending named human owner | Required before go-live approval can close. |
| Billing contact | pending named human owner | Required before the project-setup workstream can close. |
| Primary infrastructure operator | pending named human owner | Required before the project-setup workstream can close. |

## Project Records

| Field | Staging | Production |
|---|---|---|
| Project name | `lingualens-staging` | `lingualens-production` |
| Project ref | `cbhwxklvcpgizeqriqxi` | `rftslmbgbudqsypknzss` |
| Region | `ap-southeast-1` | `ap-southeast-1` |
| Dashboard URL | `https://supabase.com/dashboard/project/cbhwxklvcpgizeqriqxi` | `https://supabase.com/dashboard/project/rftslmbgbudqsypknzss` |
| API URL | `https://cbhwxklvcpgizeqriqxi.supabase.co` | `https://rftslmbgbudqsypknzss.supabase.co` |
| Publishable key location | Project Settings -> API Keys -> Publishable key (`default`) | Project Settings -> API Keys -> Publishable key (`default`) |
| Service-role secret location | `infisical` managed secret-store record pending exact path/secret name | `infisical` managed secret-store record pending exact path/secret name |

## Auth Baseline

| Setting | Staging | Production | Notes |
|---|---|---|---|
| Email/password enabled | done | done | Confirmed by operator message `auth baseline done`. |
| Public signup disabled | done | done | Confirmed by operator message `auth baseline done`. |
| Anonymous sign-in disabled | done | done | Confirmed by operator message `auth baseline done`. |
| TOTP MFA enabled | done | done | Confirmed by operator message `auth baseline done`. |
| Invitation-only onboarding path | backend-controlled membership flow, public signup off | backend-controlled membership flow, public signup off | Launch model decision; real invitation delivery still external work. |
| JWT verifier mode chosen | `jwks_url` | `jwks_url` | Operator selected `verifier = jwks_url`. |

## Backend Verifier Inputs

| Input | Staging | Production | Notes |
|---|---|---|---|
| `THERAPIST_APP_V2_SUPABASE_JWT_ISSUER` | `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1` | `https://rftslmbgbudqsypknzss.supabase.co/auth/v1` | Inferred from standard Supabase issuer format and project refs. |
| `THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE` | `authenticated` | `authenticated` | Launch default. |
| `THERAPIST_APP_V2_SUPABASE_JWT_VERIFICATION_MODE` | `jwks_url` | `jwks_url` | Operator selected this mode. |
| `THERAPIST_APP_V2_SUPABASE_JWT_JWKS_URL` | `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1/.well-known/jwks.json` | `https://rftslmbgbudqsypknzss.supabase.co/auth/v1/.well-known/jwks.json` | Derived from standard Supabase JWKS path and project refs. |
| `THERAPIST_APP_V2_SUPABASE_JWT_JWKS_JSON` | not used | not used | `jwks_url` selected. |

## Frontend Browser Inputs

| Input | Staging | Production | Notes |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://cbhwxklvcpgizeqriqxi.supabase.co` | `https://rftslmbgbudqsypknzss.supabase.co` | Inferred from project refs; operator-provided URLs were JWKS endpoints, not project base URLs. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `sb_publishable_zC7wscUPHNtoqQb4amCEEQ_K2dCC5si` | `sb_publishable_Yrk22_dt_oSdAa0ov-FGCA_-ZBylare` | Captured from Project Settings > API > Publishable key. |

## Staging Runtime Record

| Field | Value | Notes |
|---|---|---|
| Backend host/provider | `Render` | Operator confirmed the staging API is deployed on Render. |
| Database provider | `Render Postgres` | Operator-selected managed SQL provider for staging. |
| Redis provider | `Render Key Value` | Operator-selected durable queue backing service for staging. |
| Secret-store provider | `infisical` | Operator-selected managed secret-store provider. |
| Staging API base URL | `https://lingualens-api-staging.onrender.com/api/v1` | Backend URL is now known and can be used in frontend wiring and verifier env. |

## Evidence Inventory

- Dashboard screenshots: operator screenshot confirms the production project API Keys screen and the `FREE` plan badge; additional staging/owner screenshots still pending attachment.
- Connector output: `list_organizations` still shows only `monai86's Org`; `get_organization`, `get_cost`, and direct `get_project` calls against the LinguaLens org/project refs return `You do not have permission to perform this action`.
- Secret-store references: operator selected `infisical` as the managed secret-store provider; exact staging/production secret paths still need to be recorded.
- Approval references: pending named engineering/product, legal/privacy, billing, and primary infrastructure owners.

## Exceptions Or Follow-ups

- Connector permission mismatch: Codex can see the dashboard-provided org ID and operator-supplied project refs but cannot manage the org or projects through the current Supabase connector session. Manual dashboard configuration is required unless connector access is refreshed/granted.
- Named human owner contacts are still missing, so the project-setup workstream is only partially closed even though refs, dashboard URLs, API URLs, publishable keys, and verifier inputs are now recorded.

## Hand-off

- Staging auth verifier ready: backend URL now known; pending staging frontend deployment, CORS update, claim verification, and deployed cache TTL confirmation
- Tenant-safety gate blocked/unblocked: blocked pending successful staging auth verification
- Evidence package location: `docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md`
