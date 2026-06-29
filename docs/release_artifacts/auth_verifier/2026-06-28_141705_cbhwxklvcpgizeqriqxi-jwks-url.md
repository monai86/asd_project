# Staging Supabase Auth Verifier Evidence

- Date: 2026-06-28
- Commit: 3537259e
- Staging API:
- Staging therapist app:
- Supabase project ref: `cbhwxklvcpgizeqriqxi`
- Verifier mode: `jwks_url`
- Signing source: remote JWKS URL
- Operator:
- Reviewer:
- Result: in_progress

## Preconditions

- [x] Staging Supabase project exists in `ap-southeast-1`.
- [ ] `THERAPIST_APP_V2_AUTH_MODE=supabase` is active on staging API.
- [ ] `THERAPIST_APP_V2_MOCK_MODE=false` is active.
- [x] Public signup is off.
- [ ] Invitation-only onboarding is enabled.
- [x] MFA is enabled and `aal2` is required before app access.
- [ ] Claims match `docs/SUPABASE_AUTH_CONTRACT.md`.
- [ ] Verifier env matches the chosen signing path.

## Verifier Configuration Snapshot

| Field | Value | Notes |
|---|---|---|
| `THERAPIST_APP_V2_SUPABASE_JWT_VERIFICATION_MODE` | `jwks_url` | Operator selected verifier mode. |
| `THERAPIST_APP_V2_SUPABASE_JWT_JWKS_CACHE_TTL_SECONDS` | `300` | Launch default unless staging deployment overrides it. |
| `THERAPIST_APP_V2_SUPABASE_JWT_ISSUER` | `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1` | Inferred from standard project-ref issuer format. |
| `THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE` | `authenticated` | Launch default. |
| `THERAPIST_APP_V2_SUPABASE_JWT_JWKS_URL` | `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1/.well-known/jwks.json` | Derived from standard Supabase JWKS path. |
| Active `kid` observed |  |  |

## Scenario Results

| Scenario | Result | Evidence reference | Correlation/request IDs | Notes |
|---|---|---|---|---|
| Accepted `aal2` token succeeds |  |  |  |  |
| Missing bearer token fails closed |  |  |  |  |
| Wrong organization context fails closed |  |  |  |  |
| Invitation-not-accepted token denied |  |  |  |  |
| `aal1` session denied before app access |  |  |  |  |
| Revoked or inactive membership denied |  |  |  |  |
| JWKS `kid` acceptance check |  |  |  |  |
| JWKS refresh-on-missing-key check |  |  |  |  |

## Evidence Inventory

- Screenshots:
- API snippets:
- Deployment/log snippets:
- Redacted env snapshot: staging frontend publishable key captured; pending exact staging API base URL and deployed env screenshot or settings export confirmation.

## Exceptions Or Failures

- None / describe:

## Hand-off

- Tenant-safety gate ready:
- Evidence package location:
- Reviewer sign-off:
