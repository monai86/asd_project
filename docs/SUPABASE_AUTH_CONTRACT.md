# Supabase Auth Contract

Date: 2026-06-25

This document freezes the backend contract for the local Supabase Auth scaffold.
It is not evidence that a real Supabase staging or production project is
configured.

## Runtime Mode

Production-like API auth uses:

```text
THERAPIST_APP_V2_AUTH_MODE=supabase
THERAPIST_APP_V2_SUPABASE_JWT_SECRET=<managed-secret-store-value>
THERAPIST_APP_V2_SUPABASE_JWT_ISSUER=https://<project-ref>.supabase.co/auth/v1
THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE=authenticated
THERAPIST_APP_V2_SUPABASE_REQUIRE_MFA=true
THERAPIST_APP_V2_SUPABASE_REQUIRE_INVITATION=true
```

When `THERAPIST_APP_V2_MOCK_MODE=false`, runtime validation requires the
Supabase JWT secret and issuer to be configured. Mock headers are ignored in
Supabase auth mode.

## Required JWT Claims

The backend accepts a `Bearer` token whose HS256 signature verifies against the
configured Supabase JWT secret and whose `iss`, `aud`, `exp`, and optional `nbf`
claims pass validation.

Required top-level claims:

| Claim | Purpose |
|---|---|
| `sub` | Stable user ID used as `CurrentUser.user_id`. |
| `iss` | Must match `THERAPIST_APP_V2_SUPABASE_JWT_ISSUER`. |
| `aud` | Must include `THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE`. |
| `exp` | Token expiry. Expired tokens fail closed. |

Required `app_metadata` fields:

| Field | Purpose |
|---|---|
| `organization_id` | Active organization context for backend tenant guards. |
| `role` | One of therapist, clinical_supervisor, org_admin, admin, or platform_operator. |
| `membership_active` | Must be true. Revoked memberships fail closed. |
| `mfa_verified` | Must be true when MFA is required. |
| `invitation_status` | Must be `accepted` when invitation gating is required. |

Optional `app_metadata.break_glass`:

```json
{
  "active": true,
  "reason": "incident review",
  "expires_at": 1799999999
}
```

Break-glass claims must include a non-empty reason and future expiry. They do
not override clinical content guards by themselves; platform operators remain
denied clinical content unless a later, audited break-glass workflow explicitly
allows scoped access.

## Not Yet Production Evidence

Still required before production readiness:

- Supabase staging and production projects.
- Real JWT/custom-claims provisioning in Supabase.
- RLS verification against managed Postgres using real Supabase Auth claims.
- Invitation acceptance UI, MFA enrollment UI, membership revocation workflow,
  and break-glass audit workflow.
- External security/legal/vendor review before any real clinic data.
