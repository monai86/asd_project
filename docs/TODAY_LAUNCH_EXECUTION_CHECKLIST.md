# Today Launch Execution Checklist

Date: 2026-06-29

This is the shortest operator-facing checklist that stays inside the current
first-launch plan for lingualens. It is not a new plan. It is the compressed
execution path for the remaining work that cannot be finished by local code
changes alone.

## Current Status As Of 2026-06-30

- Repository-local launch scaffolding, fail-closed guards, staging env
  generators, and staging evidence scripts are now in place.
- The remaining blockers are primarily live operator/infrastructure actions,
  not missing local code paths.
- With the current repository state, Codex can still finish doc updates,
  evidence-packet assembly, and any final script hardening today.
- Codex cannot by itself complete live Supabase dashboard toggles, staging
  deployment wiring, real-claim issuance, or staging verifier proof without
  the corresponding external inputs and runtime access.

Canonical trackers:

- [docs/PRODUCTION_SAAS_FIRST_LAUNCH_BACKLOG.md](/Users/porschecaa/lingualens/docs/PRODUCTION_SAAS_FIRST_LAUNCH_BACKLOG.md)
- [docs/PRODUCTION_SAAS_LAUNCH_TRACKER.md](/Users/porschecaa/lingualens/docs/PRODUCTION_SAAS_LAUNCH_TRACKER.md)
- [docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md)

Detailed runbooks:

- [docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md)
- [docs/STAGING_EXECUTION_RUNBOOK.md](/Users/porschecaa/lingualens/docs/STAGING_EXECUTION_RUNBOOK.md)
- [docs/STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md)

## What Is Already Recorded

- Supabase organization: `LinguaLens`
- Organization ID: `whgbnlqvrgjodiquclnr`
- Staging project ref: `cbhwxklvcpgizeqriqxi`
- Production project ref: `rftslmbgbudqsypknzss`
- Region: `ap-southeast-1`
- Verifier mode: `jwks_url`
- Staging base URL: `https://cbhwxklvcpgizeqriqxi.supabase.co`
- Production base URL: `https://rftslmbgbudqsypknzss.supabase.co`
- Staging JWKS URL:
  `https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1/.well-known/jwks.json`
- Production JWKS URL:
  `https://rftslmbgbudqsypknzss.supabase.co/auth/v1/.well-known/jwks.json`
- Staging publishable key:
  `sb_publishable_zC7wscUPHNtoqQb4amCEEQ_K2dCC5si`
- Production publishable key:
  `sb_publishable_Yrk22_dt_oSdAa0ov-FGCA_-ZBylare`

Primary evidence source:

- [docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md](/Users/porschecaa/lingualens/docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md)

## Finish Today If Possible

External remaining count: 7 operator/infrastructure steps.

Repo-local remaining count before the next external handoff: 0 mandatory code
workstreams are known open in this repository; the remaining launch path is now
driven by external configuration, deployment, and evidence capture.

### 1. Fill The Missing Human Owner Records

Record these four fields in the project-setup evidence and deployment docs:

- engineering/product approver
- legal/privacy approver
- billing owner/contact
- primary infrastructure operator

Done when:

- the four names exist in the evidence pack
- there are no remaining `pending named human owner` placeholders

### 2. Confirm Live Supabase Auth Baseline In Dashboard

For both `staging` and `production`, confirm:

- public signup = off
- email/password = on
- anonymous sign-in = off
- TOTP MFA = on

Capture:

- one screenshot per project or one operator note with date/time
- note where the screenshot/evidence is stored

Done when:

- the project-setup evidence no longer says auth baseline is only inferred from
  chat state

### 3. Wire Staging Runtime

Use:

```bash
bash scripts/create_supabase_runtime_env_snippets.sh
bash scripts/create_staging_verification_env.sh
bash scripts/validate_staging_verification_env.sh \
  docs/release_artifacts/staging_env/<dated-file>.env
```

Set staging deployment env so that:

- frontend uses real Supabase URL + publishable key
- API uses `LINGUALENS_AUTH_MODE=supabase`
- API uses `LINGUALENS_SUPABASE_JWT_VERIFICATION_MODE=jwks_url`
- API is non-mock

Done when:

- `/api/v1/settings` on staging returns `auth_mode: "supabase"`
- staging app login no longer shows mock-only runtime path

### 4. Run Staging Auth Verifier

Required output:

- `docs/release_artifacts/auth_verifier/verifier-run-summary.md`

Preferred command:

```bash
bash scripts/run_staging_auth_verifier_bundle.sh
```

If the shell is already fully prepared, shortest path:

```bash
bash scripts/run_staging_review_bundle.sh
```

Done when the verifier evidence proves:

- invited login path works
- MFA enrollment/challenge works
- `aal1` stops at MFA only
- `aal2` reaches app access
- wrong-org and missing-bearer requests fail closed

### 5. Run Staging Tenant-Safety Gate

Required output:

- `docs/release_artifacts/tenant_safety/tenant-safety-run-summary.md`

Preferred command:

```bash
bash scripts/run_staging_tenant_safety_bundle.sh
```

Done when the evidence proves:

- therapist = assigned cases only
- clinical supervisor = all cases in active org
- org admin = assignment-safe by default
- platform operator = no routine clinical access
- break-glass = one case, one hour, audited
- revocation and break-glass expiry = fail closed on next request

### 6. Decide The Two Infrastructure Providers Still Missing

Pick and record:

- durable queue/worker provider
- managed secret-store provider

Record the chosen provider names in:

- [docs/PRODUCTION_DEPLOYMENT.md](/Users/porschecaa/lingualens/docs/PRODUCTION_DEPLOYMENT.md)
- [docs/PRODUCTION_SAAS_FIRST_LAUNCH_BACKLOG.md](/Users/porschecaa/lingualens/docs/PRODUCTION_SAAS_FIRST_LAUNCH_BACKLOG.md)

Done when:

- provider placeholders are replaced with actual products/services

### 7. Prepare Final Approval Packet

Before go-live, collect:

- auth verifier summary path
- tenant-safety summary path
- backup/restore drill evidence path
- security gate result
- legal/privacy approval reference
- engineering/product approval reference

Done when:

- the launch tracker can point to exact artifact paths instead of placeholders

## Minimal Copy/Paste Reply Back To Codex

When you finish any external step, send only the changed facts:

```text
owner contacts = <names>
staging api url = https://<host>/api/v1
staging app url = https://<host>
verifier summary = /Users/porschecaa/lingualens/docs/release_artifacts/auth_verifier/verifier-run-summary.md
tenant safety summary = /Users/porschecaa/lingualens/docs/release_artifacts/tenant_safety/tenant-safety-run-summary.md
queue provider = <provider>
secret store provider = <provider>
```

That is enough for Codex to continue updating the repo evidence without
rebuilding context from scratch.
