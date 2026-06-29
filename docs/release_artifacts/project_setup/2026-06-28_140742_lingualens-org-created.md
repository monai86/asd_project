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

## Project Records

| Field | Staging | Production |
|---|---|---|
| Project name | `lingualens-staging` | `lingualens-production` |
| Project ref | `cbhwxklvcpgizeqriqxi` | `rftslmbgbudqsypknzss` |
| Region | `ap-southeast-1` | `ap-southeast-1` |
| Dashboard URL | `https://supabase.com/dashboard/project/cbhwxklvcpgizeqriqxi` | `https://supabase.com/dashboard/project/rftslmbgbudqsypknzss` |
| API URL | `https://cbhwxklvcpgizeqriqxi.supabase.co` | `https://rftslmbgbudqsypknzss.supabase.co` |
| Publishable key location | Project Settings -> API Keys -> Publishable key (`default`) | Project Settings -> API Keys -> Publishable key (`default`) |
| Service-role secret location | pending managed secret-store record | pending managed secret-store record |

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

## Evidence Inventory

- Dashboard screenshots: operator screenshot confirms the production project API Keys screen and the `FREE` plan badge; additional staging/owner screenshots still pending attachment.
- Connector output: `list_organizations` still shows only `monai86's Org`; `get_organization`, `get_cost`, and direct `get_project` calls against the LinguaLens org/project refs return `You do not have permission to perform this action`.
- Secret-store references: pending managed secret-store record for service-role and any future operational secrets.
- Approval references: pending named engineering/product, legal/privacy, billing, and primary infrastructure owners.

## Exceptions Or Follow-ups

- Connector permission mismatch: Codex can see the dashboard-provided org ID and operator-supplied project refs but cannot manage the org or projects through the current Supabase connector session. Manual dashboard configuration is required unless connector access is refreshed/granted.
- Named human owner contacts are still missing, so the project-setup workstream is only partially closed even though refs, dashboard URLs, API URLs, publishable keys, and verifier inputs are now recorded.

## Hand-off

- Staging auth verifier ready: partially unblocked; pending staging API/frontend env wiring and deployed cache TTL confirmation
- Tenant-safety gate blocked/unblocked: blocked pending successful staging auth verification
- Evidence package location: `docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md`
