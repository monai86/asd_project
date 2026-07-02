# Staging Execution Runbook

Date: 2026-06-28

This is the shortest operator path from confirmed Supabase project setup to
staging verification evidence for the first controlled clinic rollout.

If you need a single-file operator checklist that includes the remaining owner
records and post-verifier handoff, start with
[docs/TODAY_LAUNCH_EXECUTION_CHECKLIST.md](/Users/porschecaa/lingualens/docs/TODAY_LAUNCH_EXECUTION_CHECKLIST.md)
first, then return here for the staging execution details.

Project setup evidence:
[docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md](/Users/porschecaa/lingualens/docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md)

Staging env wiring:
[docs/STAGING_SUPABASE_ENV_WIRING_CHECKLIST.md](/Users/porschecaa/lingualens/docs/STAGING_SUPABASE_ENV_WIRING_CHECKLIST.md)

Auth verifier runbook:
[docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md)

Tenant-safety gate:
[docs/STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md)

Shell env template:
[docs/templates/STAGING_VERIFICATION_ENV_TEMPLATE.env](/Users/porschecaa/lingualens/docs/templates/STAGING_VERIFICATION_ENV_TEMPLATE.env)

Staging evidence packet template:
[docs/templates/STAGING_EVIDENCE_PACKET_TEMPLATE.md](/Users/porschecaa/lingualens/docs/templates/STAGING_EVIDENCE_PACKET_TEMPLATE.md)

## Confirmed Staging Values

- Staging project ref: `cbhwxklvcpgizeqriqxi`
- Staging backend host/provider: `Render`
- Staging database provider: `Render Postgres`
- Staging Redis provider: `Render Key Value`
- Staging secret-store provider: `infisical`
- Staging API base URL: `https://lingualens-api-staging.onrender.com/api/v1`
- Staging Supabase base URL: `https://cbhwxklvcpgizeqriqxi.supabase.co`
- Staging JWKS URL:
  `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1/.well-known/jwks.json`
- Staging issuer:
  `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1`
- Staging publishable key:
  `sb_publishable_zC7wscUPHNtoqQb4amCEEQ_K2dCC5si`
- Verifier mode: `jwks_url`

## Step 1. Wire Staging Runtime

Generate copy/paste runtime snippets:

```bash
bash scripts/create_supabase_runtime_env_snippets.sh
```

Create a dated working shell env file from the template:

```bash
bash scripts/create_staging_verification_env.sh
```

Validate the edited working env file before you source it:

```bash
bash scripts/validate_staging_verification_env.sh \
  docs/release_artifacts/staging_env/<dated-file>.env
```

This validator now catches common handoff mistakes before the bundles run:

- API URL missing the `/api/v1` suffix
- app URL accidentally pasted as an API endpoint
- identical app/API URLs
- malformed non-JWT token values
- wrong staging project ref

Primary artifact:

- [docs/release_artifacts/runtime_env/2026-06-28_142938_staging_supabase.env](/Users/porschecaa/lingualens/docs/release_artifacts/runtime_env/2026-06-28_142938_staging_supabase.env)

This writes a working copy under `docs/release_artifacts/staging_env/` so the
template stays untouched.

Before running verification commands, prepare a shell from the generated copy
or directly from:

- [docs/templates/STAGING_VERIFICATION_ENV_TEMPLATE.env](/Users/porschecaa/lingualens/docs/templates/STAGING_VERIFICATION_ENV_TEMPLATE.env)

Apply the staging values to:

- therapist app deployment
- API deployment

Minimum required outcome:

- frontend uses real Supabase browser config
- API uses `THERAPIST_APP_V2_AUTH_MODE=supabase`
- API uses `THERAPIST_APP_V2_SUPABASE_JWT_VERIFICATION_MODE=jwks_url`
- API is non-mock
- `STAGING_API_BASE_URL=https://lingualens-api-staging.onrender.com/api/v1`
- `NEXT_PUBLIC_SUPABASE_URL=https://cbhwxklvcpgizeqriqxi.supabase.co`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_zC7wscUPHNtoqQb4amCEEQ_K2dCC5si`
- `THERAPIST_APP_V2_SUPABASE_JWT_JWKS_URL=https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1/.well-known/jwks.json`
- staged verifier env passes `scripts/validate_staging_verification_env.sh`

## Step 2. Run Auth Verifier

Required shell:

- `STAGING_API_BASE_URL`
- `ORG_A_ID`
- `ORG_B_ID`
- `ORG_A_CASE_ID`
- `ORG_B_CASE_ID`
- `TOKEN_THERAPIST_A_ASSIGNED`

If only core verifier tokens are ready, run:

```bash
bash scripts/run_staging_auth_verifier_bundle.sh
```

This bundle runs:

- settings preflight
- core accepted/missing-bearer/wrong-org checks
- lifecycle deny checks if lifecycle tokens are present
- combined summary generation

By default the auth bundle now writes probe artifacts into a run-specific
subdirectory under `docs/release_artifacts/auth_verifier/probes/`, so evidence
from older runs does not get mixed into the current summary unless you
explicitly override the output directory.

Expected output artifact:

- `docs/release_artifacts/auth_verifier/verifier-run-summary.md`

Verification target:

- auth verifier summary shows pass for preflight and core scenarios

If all verifier and tenant-safety tokens are already prepared, the shortest
operator path from this point is:

```bash
bash scripts/run_staging_review_bundle.sh
```

## Step 3. Run Tenant-Safety Gate

After the auth verifier passes and tenant-safety tokens are ready:

```bash
bash scripts/run_staging_tenant_safety_bundle.sh
```

This bundle runs:

- core tenant-safety matrix
- optional revocation probe when `REVOCATION_MEMBERSHIP_ID` is set
- combined summary generation

By default the tenant-safety bundle now writes probe artifacts into a
run-specific subdirectory under
`docs/release_artifacts/tenant_safety/probes/`, so stale meta files from
earlier runs do not bleed into the current summary.

Expected output artifact:

- `docs/release_artifacts/tenant_safety/tenant-safety-run-summary.md`

Verification target:

- tenant-safety summary shows pass for required launch scenarios

## Step 4. Update Evidence Files

After the bundles run, update:

- [docs/release_artifacts/auth_verifier/2026-06-28_141705_cbhwxklvcpgizeqriqxi-jwks-url.md](/Users/porschecaa/lingualens/docs/release_artifacts/auth_verifier/2026-06-28_141705_cbhwxklvcpgizeqriqxi-jwks-url.md)
- the generated tenant-safety evidence file under `docs/release_artifacts/tenant_safety/`

Create a review packet with:

```bash
bash scripts/create_staging_evidence_packet.sh
```

Or assemble a packet prefilled from known artifact paths with:

```bash
bash scripts/assemble_staging_evidence_packet.sh
```

When `run_staging_review_bundle.sh` is used, this packet assembly step is
already performed automatically.

Record:

- staging API URL
- staging therapist app URL
- summary artifact paths
- active `kid`
- JWKS cache TTL confirmation
- reviewer sign-off

The packet assembly step accepts either `STAGING_APP_URL` or the existing
template variable `STAGING_APP_BASE_URL`, so you do not need to rename the app
URL variable before running `run_staging_review_bundle.sh` or
`assemble_staging_evidence_packet.sh`.

## Minimal Handoff Back To Codex

If you want Codex to continue from the run results, send only:

```text
verifier summary = /Users/porschecaa/lingualens/docs/release_artifacts/auth_verifier/verifier-run-summary.md
tenant safety summary = /Users/porschecaa/lingualens/docs/release_artifacts/tenant_safety/tenant-safety-run-summary.md
staging api url = https://<staging-api-host>/api/v1
staging app url = https://<staging-therapist-app-host>
```

If tenant-safety has not run yet, send just the verifier summary first.
