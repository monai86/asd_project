# Staging Supabase Env Wiring Checklist

Date: 2026-06-28

Use this checklist to wire the confirmed staging Supabase project into the
maintained frontend and API before running the staging auth verifier.

Single-file operator handoff:
[docs/STAGING_EXECUTION_RUNBOOK.md](/Users/porschecaa/lingualens/docs/STAGING_EXECUTION_RUNBOOK.md)

To generate copy/paste env snippets for both staging and production, run:

```bash
bash scripts/create_supabase_runtime_env_snippets.sh
```

To create a dated working verifier env file without editing the template
directly, run:

```bash
bash scripts/create_staging_verification_env.sh
```

After replacing the placeholders in that working copy, validate it with:

```bash
bash scripts/validate_staging_verification_env.sh \
  docs/release_artifacts/staging_env/<dated-file>.env
```

The script writes `.env`-style snippets under
`docs/release_artifacts/runtime_env/`.

The verifier env helper writes a working copy under
`docs/release_artifacts/staging_env/`.

The validator now fails closed before any staging verifier bundle runs when:

- `STAGING_API_BASE_URL` is not an HTTPS API base ending in `/api/v1`;
- `STAGING_APP_BASE_URL` still points at an API-style URL;
- the app and API URLs were pasted as the same value;
- required core tokens are not JWT-shaped values;
- the staging project ref does not match `cbhwxklvcpgizeqriqxi`.

The downstream packet assembly step also now accepts the same app URL under
either `STAGING_APP_BASE_URL` or `STAGING_APP_URL`, so the generated verifier
env file can flow directly into the review bundle without renaming variables.

Project setup evidence:
[docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md](/Users/porschecaa/lingualens/docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md)

Auth verifier artifact:
[docs/release_artifacts/auth_verifier/2026-06-28_141705_cbhwxklvcpgizeqriqxi-jwks-url.md](/Users/porschecaa/lingualens/docs/release_artifacts/auth_verifier/2026-06-28_141705_cbhwxklvcpgizeqriqxi-jwks-url.md)

Verifier runbook:
[docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md)

## Confirmed Staging Values

- Staging project ref: `cbhwxklvcpgizeqriqxi`
- Staging Supabase base URL: `https://cbhwxklvcpgizeqriqxi.supabase.co`
- Staging JWKS URL:
  `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1/.well-known/jwks.json`
- Staging issuer:
  `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1`
- Staging audience: `authenticated`
- Verifier mode: `jwks_url`
- Staging publishable key:
  `sb_publishable_zC7wscUPHNtoqQb4amCEEQ_K2dCC5si`

## Frontend Env

Set these on the staging therapist app deployment:

```text
NEXT_PUBLIC_API_BASE_URL=<staging-api-base-url>/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://cbhwxklvcpgizeqriqxi.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_zC7wscUPHNtoqQb4amCEEQ_K2dCC5si
```

Completion check:

- login screen detects `NEXT_PUBLIC_SUPABASE_URL`
- login screen detects `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- no mock-only auth path is presented as the production path

## API Env

Set these on the staging API deployment:

```text
THERAPIST_APP_V2_MOCK_MODE=false
THERAPIST_APP_V2_AUTH_MODE=supabase
THERAPIST_APP_V2_SUPABASE_JWT_VERIFICATION_MODE=jwks_url
THERAPIST_APP_V2_SUPABASE_JWT_JWKS_URL=https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1/.well-known/jwks.json
THERAPIST_APP_V2_SUPABASE_JWT_JWKS_CACHE_TTL_SECONDS=300
THERAPIST_APP_V2_SUPABASE_JWT_ISSUER=https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1
THERAPIST_APP_V2_SUPABASE_JWT_AUDIENCE=authenticated
THERAPIST_APP_V2_SUPABASE_REQUIRE_MFA=true
THERAPIST_APP_V2_SUPABASE_REQUIRE_INVITATION=true
```

Production-like API requirements that must also be true:

```text
THERAPIST_APP_V2_REPOSITORY_MODE=sql
THERAPIST_APP_V2_STORAGE_MODE=supabase_private
THERAPIST_APP_V2_JOB_QUEUE_MODE=<durable managed mode>
THERAPIST_APP_V2_SECRET_STORE_PROVIDER=<managed provider>
THERAPIST_APP_V2_OBSERVABILITY_ENABLED=true
THERAPIST_APP_V2_OBSERVABILITY_PROVIDER=<approved provider>
THERAPIST_APP_V2_CRITICAL_ALERT_ROUTE=<configured route>
```

Completion check:

- `/api/v1/settings` reports `auth_mode: "supabase"`
- staging API no longer runs in mock mode
- verifier mode is `jwks_url`

Capture this preflight as an artifact with:

```bash
bash scripts/run_staging_auth_verifier_preflight.sh
```

The script writes `meta`, `headers`, and `body` files under
`docs/release_artifacts/auth_verifier/preflight/` by default and fails if the
settings endpoint does not show:

- HTTP `200`
- `auth_mode: "supabase"`
- `mock_mode: false`
- `required_app_aal: "aal2"`

If core tokens and optional lifecycle tokens are already prepared, the bundled
operator path is:

```bash
bash scripts/run_staging_auth_verifier_bundle.sh
```

The bundle runs preflight, core gate, optional lifecycle gate, and combined
summary generation in sequence.

## Evidence Updates

After wiring env on staging, update
[docs/release_artifacts/auth_verifier/2026-06-28_141705_cbhwxklvcpgizeqriqxi-jwks-url.md](/Users/porschecaa/lingualens/docs/release_artifacts/auth_verifier/2026-06-28_141705_cbhwxklvcpgizeqriqxi-jwks-url.md)
with:

- `Staging API`
- `Staging therapist app`
- deployed JWKS cache TTL confirmation
- active `kid` observed
- redacted env snapshot references

## Execute Verifier

Run the verifier flow immediately after staging env wiring:

1. Confirm `/api/v1/settings` returns `auth_mode: "supabase"`.
   Preferred artifact path:

   ```bash
   bash scripts/run_staging_auth_verifier_preflight.sh
   ```
2. Sign in with an invited therapist staging account.
3. Complete MFA so the session reaches `aal2`.
4. Capture one accepted token and one deny case per the verifier runbook.
   Preferred probe commands:

   ```bash
   bash scripts/run_staging_auth_verifier_probe.sh accepted_aal2_case_read
   bash scripts/run_staging_auth_verifier_probe.sh missing_bearer_case_read
   bash scripts/run_staging_auth_verifier_probe.sh wrong_org_case_read
   ```
   Or run the fail-fast bundled gate:

   ```bash
   bash scripts/run_staging_auth_verifier_core_gate.sh
   ```
   When lifecycle tokens are available, run the deny matrix:

   ```bash
   EXPECTED_DENY_STATUS=<deny-status> bash scripts/run_staging_auth_verifier_lifecycle_gate.sh
   ```
5. Record JWKS acceptance and refresh behavior evidence.

After preflight and probe runs, combine the artifacts into one markdown report:

```bash
bash scripts/summarize_staging_auth_verifier_run.sh \
  <preflight-meta-path> \
  docs/release_artifacts/auth_verifier/probes \
  docs/release_artifacts/auth_verifier/verifier-run-summary.md
```

Completion check:

- auth verifier artifact is marked `pass`
- verifier evidence location is ready for tenant-safety hand-off

## Next Step

After the verifier passes, continue with
[docs/STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md).
