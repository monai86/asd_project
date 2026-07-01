# Supabase Project Setup Evidence

- Date: {{DATE}}
- Commit: {{COMMIT}}
- Operator: {{OPERATOR}}
- Reviewer: {{REVIEWER}}
- Result: {{RESULT}}

## Preconditions

- [ ] Launch decision is accepted in `docs/adr/0017-launch-controlled-single-clinic-supabase-rollout.md`.
- [ ] Target organization name is `LinguaLens`.
- [ ] Target projects are `lingualens-staging` and `lingualens-production`.
- [ ] Target region for both projects is `ap-southeast-1`.

## Organization Record

| Field | Value | Notes |
|---|---|---|
| Organization name | `LinguaLens` |  |
| Organization ID | {{ORG_ID}} |  |
| Organization slug | {{ORG_SLUG}} |  |
| Plan/subscription | {{ORG_PLAN}} |  |
| Owner contact | {{OWNER_CONTACT}} |  |

## Named Owners

| Role | Contact | Notes |
|---|---|---|
| Engineering/product approver | {{ENGINEERING_PRODUCT_APPROVER}} |  |
| Legal/privacy approver | {{LEGAL_PRIVACY_APPROVER}} |  |
| Billing contact | {{BILLING_CONTACT}} |  |
| Primary infrastructure operator | {{INFRA_OPERATOR}} |  |

## Project Records

| Field | Staging | Production |
|---|---|---|
| Project name | `lingualens-staging` | `lingualens-production` |
| Project ref | {{STAGING_PROJECT_REF}} | {{PRODUCTION_PROJECT_REF}} |
| Region | `ap-southeast-1` | `ap-southeast-1` |
| Dashboard URL | {{STAGING_DASHBOARD_URL}} | {{PRODUCTION_DASHBOARD_URL}} |
| API URL | {{STAGING_API_URL}} | {{PRODUCTION_API_URL}} |
| Publishable key location | {{STAGING_PUBLISHABLE_KEY_LOCATION}} | {{PRODUCTION_PUBLISHABLE_KEY_LOCATION}} |
| Service-role secret location | {{STAGING_SERVICE_ROLE_SECRET_LOCATION}} | {{PRODUCTION_SERVICE_ROLE_SECRET_LOCATION}} |

## Auth Baseline

| Setting | Staging | Production | Notes |
|---|---|---|---|
| Email/password enabled | {{STAGING_EMAIL_PASSWORD_ENABLED}} | {{PRODUCTION_EMAIL_PASSWORD_ENABLED}} | {{AUTH_BASELINE_NOTES}} |
| Public signup disabled | {{STAGING_PUBLIC_SIGNUP_DISABLED}} | {{PRODUCTION_PUBLIC_SIGNUP_DISABLED}} | {{AUTH_BASELINE_NOTES}} |
| Anonymous sign-in disabled | {{STAGING_ANONYMOUS_SIGNIN_DISABLED}} | {{PRODUCTION_ANONYMOUS_SIGNIN_DISABLED}} | {{AUTH_BASELINE_NOTES}} |
| TOTP MFA enabled | {{STAGING_TOTP_MFA_ENABLED}} | {{PRODUCTION_TOTP_MFA_ENABLED}} | {{AUTH_BASELINE_NOTES}} |
| Invitation-only onboarding path | {{STAGING_INVITATION_PATH}} | {{PRODUCTION_INVITATION_PATH}} | {{INVITATION_PATH_NOTES}} |
| JWT verifier mode chosen | {{STAGING_JWT_VERIFIER_MODE}} | {{PRODUCTION_JWT_VERIFIER_MODE}} | {{JWT_VERIFIER_NOTES}} |

## Backend Verifier Inputs

| Input | Staging | Production | Notes |
|---|---|---|---|
| `LINGUALENS_SUPABASE_JWT_ISSUER` | {{STAGING_JWT_ISSUER}} | {{PRODUCTION_JWT_ISSUER}} |  |
| `LINGUALENS_SUPABASE_JWT_AUDIENCE` | {{STAGING_JWT_AUDIENCE}} | {{PRODUCTION_JWT_AUDIENCE}} |  |
| `LINGUALENS_SUPABASE_JWT_VERIFICATION_MODE` | {{STAGING_JWT_VERIFIER_MODE}} | {{PRODUCTION_JWT_VERIFIER_MODE}} |  |
| `LINGUALENS_SUPABASE_JWT_JWKS_URL` | {{STAGING_JWKS_URL}} | {{PRODUCTION_JWKS_URL}} |  |
| `LINGUALENS_SUPABASE_JWT_JWKS_JSON` | {{STAGING_JWKS_JSON}} | {{PRODUCTION_JWKS_JSON}} | if used |

## Frontend Browser Inputs

| Input | Staging | Production | Notes |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | {{STAGING_SUPABASE_URL}} | {{PRODUCTION_SUPABASE_URL}} |  |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | {{STAGING_SUPABASE_ANON_KEY}} | {{PRODUCTION_SUPABASE_ANON_KEY}} |  |

## Evidence Inventory

- Dashboard screenshots: {{DASHBOARD_SCREENSHOTS_NOTE}}
- Connector output: {{CONNECTOR_OUTPUT_NOTE}}
- Secret-store references: {{SECRET_STORE_REFERENCES_NOTE}}
- Approval references: {{APPROVAL_REFERENCES_NOTE}}

## Exceptions Or Follow-ups

- {{EXCEPTIONS_OR_FOLLOWUPS}}

## Hand-off

- Staging auth verifier ready: {{STAGING_AUTH_VERIFIER_READY}}
- Tenant-safety gate blocked/unblocked: {{TENANT_SAFETY_GATE_STATUS}}
- Evidence package location: {{EVIDENCE_PACKAGE_LOCATION}}
