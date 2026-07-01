# Supabase Auth Staging Verifier Runbook

Date: 2026-06-28

This runbook defines how to configure and verify the maintained `apps/api`
Supabase auth verifier against a real staging Supabase project before running
the tenant-safety promotion gate.

Contract:
[docs/SUPABASE_AUTH_CONTRACT.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_CONTRACT.md)

Tenant-safety gate:
[docs/STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md)

Staging env wiring checklist:
[docs/STAGING_SUPABASE_ENV_WIRING_CHECKLIST.md](/Users/porschecaa/lingualens/docs/STAGING_SUPABASE_ENV_WIRING_CHECKLIST.md)

Single-file staging execution handoff:
[docs/STAGING_EXECUTION_RUNBOOK.md](/Users/porschecaa/lingualens/docs/STAGING_EXECUTION_RUNBOOK.md)

## Purpose

Use this runbook to prove that the staging API is wired to the intended
Supabase JWT verification mode and that real staging bearer tokens are accepted
or rejected correctly before the clinic launch gate proceeds.

This runbook does not replace the tenant-safety gate. It is the auth-verifier
setup and verification prerequisite for that gate.

The reusable auth-verifier evidence template lives at
[docs/templates/STAGING_AUTH_VERIFIER_EVIDENCE_TEMPLATE.md](/Users/porschecaa/lingualens/docs/templates/STAGING_AUTH_VERIFIER_EVIDENCE_TEMPLATE.md).

Generate a new evidence file with:

```bash
bash scripts/create_staging_auth_verifier_evidence.sh
```

Optional slug:

```bash
bash scripts/create_staging_auth_verifier_evidence.sh clinic-a-jwks-url-pass-1
```

By default the script writes to `docs/release_artifacts/auth_verifier/` and
prefills the date plus current git short SHA when available.

Before token-level verification, capture the staging settings preflight with:

```bash
bash scripts/run_staging_auth_verifier_preflight.sh
```

For a one-command verifier bundle after deploy, use:

```bash
bash scripts/run_staging_auth_verifier_bundle.sh
```

For repeatable token-level request capture, use:

```bash
bash scripts/run_staging_auth_verifier_probe.sh accepted_aal2_case_read
```

For the fail-fast core verifier checks, use:

```bash
bash scripts/run_staging_auth_verifier_core_gate.sh
```

The core gate now writes its probe meta files into a run-specific subdirectory
by default, so repeated verifier runs do not reuse stale probe artifacts unless
you intentionally point the script at a fixed output directory.

For the lifecycle deny matrix after the core checks, use:

```bash
EXPECTED_DENY_STATUS=<deny-status> bash scripts/run_staging_auth_verifier_lifecycle_gate.sh
```

## Verifier Modes

The maintained backend currently supports these verifier modes:

- `hs256_shared_secret`
- `jwks_json`
- `jwks_url`

Recommended staging choice:

- Prefer `jwks_url` when the staging Supabase project publishes a remote JWKS
  endpoint appropriate for the selected signing mode.
- Use `jwks_json` only for controlled operator validation or when staging
  deployment constraints require an injected JWKS document.
- Use `hs256_shared_secret` only if the real staging project explicitly uses
  shared-secret verification and this is the approved production-path design.

## Required Environment

Set these on the staging API deployment:

```text
LINGUALENS_MOCK_MODE=false
LINGUALENS_AUTH_MODE=supabase
LINGUALENS_SUPABASE_JWT_VERIFICATION_MODE=<hs256_shared_secret|jwks_json|jwks_url>
LINGUALENS_SUPABASE_JWT_SECRET=<required only for hs256_shared_secret>
LINGUALENS_SUPABASE_JWT_JWKS_JSON=<required only for jwks_json>
LINGUALENS_SUPABASE_JWT_JWKS_URL=<required only for jwks_url>
LINGUALENS_SUPABASE_JWT_JWKS_CACHE_TTL_SECONDS=300
LINGUALENS_SUPABASE_JWT_ISSUER=https://<project-ref>.supabase.co/auth/v1
LINGUALENS_SUPABASE_JWT_AUDIENCE=authenticated
LINGUALENS_SUPABASE_REQUIRE_MFA=true
LINGUALENS_SUPABASE_REQUIRE_INVITATION=true
```

The rest of the production-like requirements still apply:

- SQL repository mode
- managed/private storage mode
- durable job queue mode
- explicit CORS origins
- observability provider and critical alert route
- managed secret-store provider and rotation runbook

## Operator Decision Record

Capture these values in the staging evidence notes before verification:

| Field | Required value |
|---|---|
| Staging Supabase project ref | exact ref |
| Verifier mode | `hs256_shared_secret`, `jwks_json`, or `jwks_url` |
| Signing source | shared secret, static JWKS, or remote JWKS URL |
| JWKS cache TTL | exact seconds if `jwks_url` |
| Issuer | exact configured issuer |
| Audience | exact configured audience |
| Operator | human name |
| Commit SHA | git SHA under test |

## Preflight Checks

Confirm all of these before login testing:

1. The staging API returns `auth_mode: "supabase"` from `/api/v1/settings`.
2. `LINGUALENS_MOCK_MODE=false` is active in the deployment.
3. The configured verifier mode matches the intended staging signing method.
4. Public signup is disabled in the staging Supabase project.
5. MFA and invitation gating remain enabled.

## Minimal Auth Verification Flow

Use real staging accounts and real staging tokens only.

### 1. Accepted `aal2` token succeeds

- Sign in as an invited, accepted, MFA-complete therapist in staging.
- Confirm the app reaches an `aal2` session.
- Capture the access token through approved operator tooling.
- Preferred scripted capture:

```bash
bash scripts/run_staging_auth_verifier_probe.sh accepted_aal2_case_read
```

- Equivalent raw route example:

```bash
curl -i \
  -H "Authorization: Bearer $TOKEN_THERAPIST_A_ASSIGNED" \
  -H "X-Organization-Id: $ORG_A_ID" \
  "$STAGING_API_BASE_URL/cases/$ORG_A_CASE_ID"
```

Expected:

- `200`
- no mock-header fallback required

### 2. Missing bearer token fails closed

Preferred scripted capture:

```bash
bash scripts/run_staging_auth_verifier_probe.sh missing_bearer_case_read
```

```bash
curl -i \
  -H "X-Organization-Id: $ORG_A_ID" \
  "$STAGING_API_BASE_URL/cases/$ORG_A_CASE_ID"
```

Expected:

- `401`

### 3. Wrong organization context fails closed

- Reuse a valid therapist token from `org_a`.
- Preferred scripted capture:

```bash
bash scripts/run_staging_auth_verifier_probe.sh wrong_org_case_read
```

- Equivalent raw route example calls a case owned by `org_b`.

Expected:

- deny response matching the tenant-safety matrix (`404`)

### 4. Invalid lifecycle claims fail closed

Validate at least one real staging example for each:

- invitation not accepted
- session below `aal2`
- revoked or inactive membership

Suggested scripted captures:

```bash
EXPECTED_STATUS=<deny-status> bash scripts/run_staging_auth_verifier_probe.sh invitation_pending_case_read
EXPECTED_STATUS=<deny-status> bash scripts/run_staging_auth_verifier_probe.sh aal1_case_read
EXPECTED_STATUS=<deny-status> bash scripts/run_staging_auth_verifier_probe.sh inactive_membership_case_read
```

Bundled lifecycle gate:

```bash
EXPECTED_DENY_STATUS=<deny-status> bash scripts/run_staging_auth_verifier_lifecycle_gate.sh
```

Expected:

- request denied before workspace access or API success

### 5. JWKS mode operational check

For `jwks_json` or `jwks_url`:

- record the active `kid` from one accepted staging token header
- confirm the deployed verifier mode can validate that token successfully

For `jwks_url` specifically:

- note the configured cache TTL
- record whether the first verified request required a JWKS fetch in operator
  logs or deployment telemetry if available

## Remote JWKS Rotation Check

This applies only when `LINGUALENS_SUPABASE_JWT_VERIFICATION_MODE=jwks_url`.

Minimum requirement before launch:

- prove that a token signed with a newly published `kid` is accepted after the
  verifier refreshes JWKS once
- prove that if the refreshed JWKS still lacks the `kid`, the request fails
  closed

Acceptable evidence sources:

- controlled staging operator simulation
- Supabase key rotation rehearsal in staging
- deployment logs plus redacted request/response capture

## Evidence To Save

Save these with the staging auth evidence package:

- verifier mode used
- relevant env values redacted to non-secret form
- one accepted `aal2` request capture
- one missing-token deny capture
- one invalid-lifecycle deny capture
- one wrong-org deny capture
- JWKS-specific evidence when `jwks_json` or `jwks_url` is used

Do not store raw secrets, raw long-lived credentials, or raw clinical content.

Summarize all captured verifier probe meta files into a markdown table with:

```bash
bash scripts/summarize_staging_auth_verifier_probes.sh
```

Optionally write the markdown table directly to a file:

```bash
bash scripts/summarize_staging_auth_verifier_probes.sh \
  docs/release_artifacts/auth_verifier/probes \
  docs/release_artifacts/auth_verifier/probes/manual-summary.md
```

To combine the preflight result plus probe results into one markdown report:

```bash
bash scripts/summarize_staging_auth_verifier_run.sh \
  <preflight-meta-path> \
  docs/release_artifacts/auth_verifier/probes \
  docs/release_artifacts/auth_verifier/verifier-run-summary.md
```

`run_staging_auth_verifier_bundle.sh` already creates this combined summary
automatically.

## Hand-off To Tenant-Safety Gate

After this runbook passes, continue immediately with:

[docs/STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md)

Record in that evidence package:

- the verifier mode used
- whether auth verification passed before the tenant-safety matrix
- the location of the verifier evidence package under
  `docs/release_artifacts/auth_verifier/`
- the location of any verifier-specific captures
