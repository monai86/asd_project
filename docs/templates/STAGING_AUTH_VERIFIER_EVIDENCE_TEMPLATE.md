# Staging Supabase Auth Verifier Evidence

- Date:
- Commit:
- Staging API:
- Staging therapist app:
- Supabase project ref:
- Verifier mode:
- Signing source:
- Operator:
- Reviewer:
- Result:

## Preconditions

- [ ] Staging Supabase project exists in `ap-southeast-1`.
- [ ] `THERAPIST_APP_V2_AUTH_MODE=supabase` is active on staging API.
- [ ] `THERAPIST_APP_V2_MOCK_MODE=false` is active.
- [ ] Public signup is off.
- [ ] Invitation-only onboarding is enabled.
- [ ] MFA is enabled and `aal2` is required before app access.
- [ ] Claims match `docs/SUPABASE_AUTH_CONTRACT.md`.
- [ ] Verifier env matches the chosen signing path.

## Verifier Configuration Snapshot

| Field | Value | Notes |
|---|---|---|
| `THERAPIST_APP_V2_SUPABASE_JWT_VERIFICATION_MODE` |  |  |
| `THERAPIST_APP_V2_SUPABASE_JWT_JWKS_CACHE_TTL_SECONDS` |  |  |
| `THERAPIST_APP_V2_SUPABASE_JWT_ISSUER` |  |  |
| `THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE` |  |  |
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
- Redacted env snapshot:

## Exceptions Or Failures

- None / describe:

## Hand-off

- Tenant-safety gate ready:
- Evidence package location:
- Reviewer sign-off:
