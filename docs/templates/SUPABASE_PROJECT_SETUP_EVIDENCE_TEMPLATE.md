# Supabase Project Setup Evidence

- Date:
- Commit:
- Operator:
- Reviewer:
- Result:

## Preconditions

- [ ] Launch decision is accepted in `docs/adr/0017-launch-controlled-single-clinic-supabase-rollout.md`.
- [ ] Target organization name is `LinguaLens`.
- [ ] Target projects are `lingualens-staging` and `lingualens-production`.
- [ ] Target region for both projects is `ap-southeast-1`.

## Organization Record

| Field | Value | Notes |
|---|---|---|
| Organization name | `LinguaLens` |  |
| Organization ID |  |  |
| Organization slug |  |  |
| Plan/subscription |  |  |
| Owner contact |  |  |

## Project Records

| Field | Staging | Production |
|---|---|---|
| Project name | `lingualens-staging` | `lingualens-production` |
| Project ref |  |  |
| Region | `ap-southeast-1` | `ap-southeast-1` |
| Dashboard URL |  |  |
| API URL |  |  |
| Publishable key location |  |  |
| Service-role secret location |  |  |

## Auth Baseline

| Setting | Staging | Production | Notes |
|---|---|---|---|
| Email/password enabled |  |  |  |
| Public signup disabled |  |  |  |
| Anonymous sign-in disabled |  |  |  |
| TOTP MFA enabled |  |  |  |
| Invitation-only onboarding path |  |  |  |
| JWT verifier mode chosen |  |  |  |

## Backend Verifier Inputs

| Input | Staging | Production | Notes |
|---|---|---|---|
| `THERAPIST_APP_V2_SUPABASE_JWT_ISSUER` |  |  |  |
| `THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE` |  |  |  |
| `THERAPIST_APP_V2_SUPABASE_JWT_VERIFICATION_MODE` |  |  |  |
| `THERAPIST_APP_V2_SUPABASE_JWT_JWKS_URL` |  |  |  |
| `THERAPIST_APP_V2_SUPABASE_JWT_JWKS_JSON` |  |  | if used |

## Frontend Browser Inputs

| Input | Staging | Production | Notes |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` |  |  |  |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` |  |  |  |

## Evidence Inventory

- Dashboard screenshots:
- Connector output:
- Secret-store references:
- Approval references:

## Exceptions Or Follow-ups

- None / describe:

## Hand-off

- Staging auth verifier ready:
- Tenant-safety gate blocked/unblocked:
- Evidence package location:
