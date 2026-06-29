# Supabase Auth Contract

Date: 2026-06-28

This document freezes the backend contract for the local Supabase Auth scaffold.
It is not evidence that a real Supabase staging or production project is
configured.

Execution gap tracker:
[docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md)

Implementation checklist:
[docs/SUPABASE_AUTH_IMPLEMENTATION_CHECKLIST.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_IMPLEMENTATION_CHECKLIST.md)

Staging verifier runbook:
[docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md)

## Runtime Mode

Production-like API auth uses:

```text
THERAPIST_APP_V2_AUTH_MODE=supabase
THERAPIST_APP_V2_SUPABASE_JWT_VERIFICATION_MODE=hs256_shared_secret | jwks_json | jwks_url
THERAPIST_APP_V2_SUPABASE_JWT_SECRET=<managed-secret-store-value>
THERAPIST_APP_V2_SUPABASE_JWT_JWKS_JSON=<managed-jwks-json-when-using-asymmetric-verification>
THERAPIST_APP_V2_SUPABASE_JWT_JWKS_URL=<managed-jwks-url-when-using-remote-asymmetric-verification>
THERAPIST_APP_V2_SUPABASE_JWT_JWKS_CACHE_TTL_SECONDS=300
THERAPIST_APP_V2_SUPABASE_JWT_ISSUER=https://<project-ref>.supabase.co/auth/v1
THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE=authenticated
THERAPIST_APP_V2_SUPABASE_REQUIRE_MFA=true
THERAPIST_APP_V2_SUPABASE_REQUIRE_INVITATION=true
```

When `THERAPIST_APP_V2_MOCK_MODE=false`, runtime validation requires the
selected Supabase verification material and issuer to be configured, and MFA
plus invitation acceptance guards must remain enabled. Mock headers are ignored
in Supabase auth mode.

## Required JWT Claims

The current scaffold supports two local verification paths:

- `hs256_shared_secret`: verifies the `Bearer` token against the configured
  Supabase JWT shared secret.
- `jwks_json`: verifies an `RS256` `Bearer` token against a configured JWKS JSON
  document.
- `jwks_url`: verifies an `RS256` `Bearer` token against a JWKS document fetched
  from a configured URL and cached locally for the configured TTL.

For `jwks_url`, the verifier re-fetches the JWKS once if the cached document
does not contain the presented signing key. If the refreshed document still
lacks the key, the request fails closed.

In both cases, `iss`, `aud`, `exp`, and optional `nbf` claims must pass
validation.

Required top-level claims:

| Claim | Purpose |
|---|---|
| `sub` | Stable user ID used as `CurrentUser.user_id`. |
| `iss` | Must match `THERAPIST_APP_V2_SUPABASE_JWT_ISSUER`. |
| `aud` | Must include `THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE`. |
| `exp` | Token expiry. Expired tokens fail closed. |
| `aal` | Must be `aal2` when MFA is required for app access. |

Required `app_metadata` fields:

| Field | Purpose |
|---|---|
| `organization_id` | Active organization context for backend tenant guards. |
| `role` | One of therapist, clinical_supervisor, org_admin, or platform_operator. |
| `membership_active` | Must be true. Revoked memberships fail closed. |
| `invitation_status` | Must be `accepted` when invitation gating is required. |

Optional `app_metadata.organizations`:

```json
[
  {
    "organization_id": "org_a",
    "name": "Clinic A",
    "role": "therapist",
    "active": true
  },
  {
    "organization_id": "org_b",
    "name": "Clinic B",
    "role": "clinical_supervisor",
    "active": true
  }
]
```

When a user has more than one active membership, the app must treat stored
organization memory as a hint only. If the active context is ambiguous, the
user must explicitly select one organization before any clinical or admin route
opens. Only one active organization is valid per session.

When `organizations` or `organization_memberships` is present, the backend
verifier expects the selected `organization_id` and `role` to match one listed
membership. If an `active` flag is present on that entry, it must be a boolean
and must be `true`.

Optional `app_metadata.break_glass`:

```json
{
  "active": true,
  "case_id": "case_a_1",
  "category": "incident_review",
  "reason": "incident review",
  "expires_at": 1799999999
}
```

Break-glass claims must include a non-empty scoped `case_id`, non-empty
category, non-empty free-text reason, and an expiry that is still in the
future and no more than one hour ahead. They do not override clinical content
guards by themselves; platform operators remain denied clinical content through
normal routes. The backend exposes a scoped break-glass case-access endpoint
that requires platform-operator role plus a valid case/category/reason/expiry
tuple and writes an audit event for each case access.

## Backend Lifecycle Workflow

The local backend foundation supports:

- org-admin invitation create/list/accept endpoints;
- invitation acceptance that creates or reactivates active organization
  membership;
- membership revocation that deactivates care-team assignments;
- production runtime validation that rejects disabled MFA or invitation guards;
- scoped break-glass case access audited per target case.

These APIs are backend workflow scaffolding. Real invitation delivery, MFA
enrollment, and custom-claim synchronization must be implemented in Supabase and
the frontend before production use.

## Not Yet Production Evidence

Still required before production readiness:

- Supabase staging and production projects.
- Real JWT/custom-claims provisioning in Supabase.
- RLS verification against managed Postgres using real Supabase Auth claims.
- Explicit organization-selection UX using real Supabase membership claims.
- Invitation acceptance UI, MFA enrollment UI, managed custom-claim sync, and
  operational break-glass review process.
- External security/legal/vendor review before any real clinic data.
