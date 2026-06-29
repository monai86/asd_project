# Staging Tenant-Safety Verification

Date: 2026-06-27

This document operationalizes the `Tenant-Safety Promotion Gate` for the first
production rollout. It is the required staging evidence package before any
promotion from staging to production.

Use this only against the real staging Supabase project and the staging
`apps/api` deployment. Do not treat local mock-mode results as a substitute for
this verification.

Before running this matrix, complete the verifier setup and minimal auth
verification in
[docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md).

Single-file staging execution handoff:
[docs/STAGING_EXECUTION_RUNBOOK.md](/Users/porschecaa/lingualens/docs/STAGING_EXECUTION_RUNBOOK.md)

## Purpose

This gate proves that the first-launch tenant boundary behaves correctly with
real Supabase claims, real organization memberships, and the maintained
clinical policy boundary in `apps/api/`.

The gate passes only when all scenarios below are executed on staging and the
captured evidence shows:

- no cross-organization clinical read or write succeeds;
- therapist access is assigned-case only;
- clinical supervisor access is all cases in the active organization;
- org admin remains assignment-safe by default;
- platform operator has no routine clinical access;
- break-glass is one-case scoped, audited, and fails closed on expiry;
- membership revocation fails closed on the next request.

## Required Preconditions

- Staging Supabase project exists in `ap-southeast-1`.
- Staging API uses `THERAPIST_APP_V2_AUTH_MODE=supabase`.
- Public signup is off.
- Invitation-only onboarding is enabled.
- Real staging claims match [docs/SUPABASE_AUTH_CONTRACT.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_CONTRACT.md).
- Staging verifier mode and env match
  [docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md).
- Staging therapist app points to the staging API and Supabase project.
- At least two organizations exist in staging:
  - `org_a` for the launch clinic
  - `org_b` for the denial tenant
- At least one seeded case exists in each organization.
- Evidence capture location is agreed before the run.

## Required Identities

Create or confirm these staging users before the run:

| User | Org membership | Role | Notes |
|---|---|---|---|
| `therapist_a_assigned` | `org_a` | `therapist` | Assigned to `case_a_1` and primary therapist. |
| `therapist_a_unassigned` | `org_a` | `therapist` | Not assigned to `case_a_1`. |
| `supervisor_a` | `org_a` | `clinical_supervisor` | No special care-team grant required. |
| `org_admin_a` | `org_a` | `org_admin` | No clinical grant by default. |
| `platform_operator_a` | separate | `platform_operator` | Break-glass only. |
| `therapist_b_assigned` | `org_b` | `therapist` | Assigned to `case_b_1`. |

If multi-org membership is enabled for any user in the run, record the explicit
active organization selected for each scenario.

## Evidence Package

Record these fields with the staging run:

| Field | Required value |
|---|---|
| Date/time | UTC timestamp range for the run |
| Commit | Git SHA under test |
| Staging API base URL | Exact deployed URL |
| Supabase project ref | Exact staging project ref |
| Verifier mode | `hs256_shared_secret`, `jwks_json`, or `jwks_url` |
| Operator | Human who executed the run |
| Witness/reviewer | Second reviewer if available |
| Correlation IDs | Request IDs or audit correlation IDs for key denies/grants |
| Screenshot set | UI screenshots for auth/org-selection/deny states |
| API evidence | Saved request/response snippets with sensitive content redacted |
| Final result | `pass` or `fail` |

Do not store raw clinical content in the evidence package.

The reusable evidence file template lives at
[docs/templates/STAGING_TENANT_SAFETY_EVIDENCE_TEMPLATE.md](/Users/porschecaa/lingualens/docs/templates/STAGING_TENANT_SAFETY_EVIDENCE_TEMPLATE.md).

The auth-verifier evidence template that must be completed first lives at
[docs/templates/STAGING_AUTH_VERIFIER_EVIDENCE_TEMPLATE.md](/Users/porschecaa/lingualens/docs/templates/STAGING_AUTH_VERIFIER_EVIDENCE_TEMPLATE.md).

Generate a new evidence file from that template with:

```bash
bash scripts/create_staging_tenant_safety_evidence.sh
```

Optional slug:

```bash
bash scripts/create_staging_tenant_safety_evidence.sh clinic-a-pass-1
```

By default the script writes to `docs/release_artifacts/tenant_safety/` and
prefills the date plus current git short SHA when available.

Before starting this tenant-safety matrix, create and complete the auth
verification evidence package with:

```bash
bash scripts/create_staging_auth_verifier_evidence.sh
```

Store the resulting file under `docs/release_artifacts/auth_verifier/` and
reference it from the tenant-safety evidence package.

For repeatable API captures, use the staging probe helper:

```bash
bash scripts/run_staging_tenant_safety_probe.sh assigned_case_read
```

The probe writes `meta`, `headers`, and `body` files under
`docs/release_artifacts/tenant_safety/probes/` by default and exits non-zero if
the response status does not match the expected policy outcome for that
scenario. Set `ALLOW_STATUS_MISMATCH=1` only when you intentionally want to
capture a failing result without stopping the shell pipeline.

For a one-command tenant-safety bundle after verifier completion, use:

```bash
bash scripts/run_staging_tenant_safety_bundle.sh
```

For the fail-fast core matrix, use:

```bash
bash scripts/run_staging_tenant_safety_core_gate.sh
```

If `REVOCATION_MEMBERSHIP_ID` is set, the core gate also runs the revocation
probe at the end. The core gate now also writes a markdown summary artifact
into `docs/release_artifacts/tenant_safety/probes/` and prints the summary file
path at completion.

Summarize all captured probe meta files into a markdown table with:

```bash
bash scripts/summarize_staging_tenant_safety_probes.sh
```

Pass a custom probe directory if needed:

```bash
bash scripts/summarize_staging_tenant_safety_probes.sh docs/release_artifacts/tenant_safety/probes
```

Optionally write the markdown table directly to a file:

```bash
bash scripts/summarize_staging_tenant_safety_probes.sh \
  docs/release_artifacts/tenant_safety/probes \
  docs/release_artifacts/tenant_safety/probes/manual-summary.md
```

To generate a combined tenant-safety run report from the probe directory:

```bash
bash scripts/summarize_staging_tenant_safety_run.sh \
  docs/release_artifacts/tenant_safety/probes \
  docs/release_artifacts/tenant_safety/tenant-safety-run-summary.md
```

`run_staging_tenant_safety_bundle.sh` already creates this combined summary
automatically.

## Operator Setup

Prepare a staging verification shell with environment values before executing
the matrix:

```bash
export STAGING_API_BASE_URL="https://<staging-api-host>/api/v1"
export STAGING_APP_BASE_URL="https://<staging-therapist-app-host>"
export STAGING_SUPABASE_PROJECT_REF="<project-ref>"
export ORG_A_CASE_ID="<case_a_1>"
export ORG_B_CASE_ID="<case_b_1>"
```

Capture one bearer token per test identity from the real staging login flow or
approved operator tooling:

```bash
export TOKEN_THERAPIST_A_ASSIGNED="<jwt>"
export TOKEN_THERAPIST_A_UNASSIGNED="<jwt>"
export TOKEN_SUPERVISOR_A="<jwt>"
export TOKEN_ORG_ADMIN_A="<jwt>"
export TOKEN_PLATFORM_OPERATOR_A="<jwt>"
export TOKEN_THERAPIST_B_ASSIGNED="<jwt>"
```

Use the active organization required for the scenario on every request:

```bash
export ORG_A_ID="org_a"
export ORG_B_ID="org_b"
```

For scripted revocation checks, also set:

```bash
export REVOCATION_MEMBERSHIP_ID="<membership_id>"
```

## Operator Command Scaffold

The exact tokens, record IDs, and expected response bodies vary by staging
data. Use commands shaped like these and save redacted outputs into the
evidence package.

Preferred scripted examples:

```bash
bash scripts/run_staging_tenant_safety_probe.sh assigned_case_read
bash scripts/run_staging_tenant_safety_probe.sh cross_org_case_read
bash scripts/run_staging_tenant_safety_probe.sh unassigned_case_read
bash scripts/run_staging_tenant_safety_probe.sh org_admin_memberships
bash scripts/run_staging_tenant_safety_probe.sh platform_break_glass
bash scripts/run_staging_tenant_safety_core_gate.sh
bash scripts/summarize_staging_tenant_safety_probes.sh
```

`run_staging_tenant_safety_core_gate.sh` is the preferred operator path for the
required pass/fail matrix because it captures the core scenarios and emits a
summary markdown artifact automatically.

When all required tenant-safety tokens are already loaded, the shortest path is:

```bash
bash scripts/run_staging_tenant_safety_bundle.sh
```

Expected status mapping in the probe:

| Scenario | Expected status |
|---|---|
| `assigned_case_read` | `200` |
| `cross_org_case_read` | `404` |
| `unassigned_case_read` | `403` |
| `supervisor_case_read` | `200` |
| `org_admin_memberships` | `200` |
| `org_admin_case_read` | `403` |
| `platform_break_glass` | `200` |
| `platform_case_read` | `403` |
| `revoke_membership` | `200` |

Assigned therapist success sample:

```bash
curl -i \
  -H "Authorization: Bearer $TOKEN_THERAPIST_A_ASSIGNED" \
  -H "X-Organization-Id: $ORG_A_ID" \
  "$STAGING_API_BASE_URL/cases/$ORG_A_CASE_ID"
```

Cross-org read denial sample:

```bash
curl -i \
  -H "Authorization: Bearer $TOKEN_THERAPIST_A_ASSIGNED" \
  -H "X-Organization-Id: $ORG_A_ID" \
  "$STAGING_API_BASE_URL/cases/$ORG_B_CASE_ID"
```

Unassigned therapist denial sample:

```bash
curl -i \
  -H "Authorization: Bearer $TOKEN_THERAPIST_A_UNASSIGNED" \
  -H "X-Organization-Id: $ORG_A_ID" \
  "$STAGING_API_BASE_URL/cases/$ORG_A_CASE_ID"
```

Org-admin assignment-safe metadata sample:

```bash
curl -i \
  -H "Authorization: Bearer $TOKEN_ORG_ADMIN_A" \
  -H "X-Organization-Id: $ORG_A_ID" \
  "$STAGING_API_BASE_URL/organizations/current/memberships"
```

Platform-operator scoped break-glass sample:

```bash
curl -i -X POST \
  -H "Authorization: Bearer $TOKEN_PLATFORM_OPERATOR_A" \
  -H "X-Organization-Id: $ORG_A_ID" \
  "$STAGING_API_BASE_URL/cases/$ORG_A_CASE_ID/break-glass-access"
```

Membership revocation sample:

```bash
curl -i -X POST \
  -H "Authorization: Bearer $TOKEN_ORG_ADMIN_A" \
  -H "X-Organization-Id: $ORG_A_ID" \
  "$STAGING_API_BASE_URL/organizations/current/memberships/<membership_id>/revoke"
```

## Scenario Matrix

Run all scenarios below in staging.

### 1. Cross-org clinical read denial

- Authenticate as `therapist_a_assigned` with active org `org_a`.
- Attempt to read `case_b_1`.
- Attempt to read a session/transcript/report belonging to `org_b`.

Expected:

- API returns `404` for cross-org clinical records.
- UI does not render `org_b` clinical content through link guessing or direct
  navigation.

Evidence:

- Redacted request/response snippet for each route.
- UI screenshot of the denied state if the route is reachable in the frontend.

### 2. Cross-org clinical write denial

- Authenticate as an `org_a` user.
- Attempt to update or create a clinical record under `org_b`.
- Attempt cross-org care-team assignment against `case_b_1`.

Expected:

- Cross-org writes fail with `404` or `403`.
- No `org_b` clinical state changes are persisted.

Evidence:

- Redacted request/response snippets.
- Post-check that the target `org_b` record remains unchanged.

### 3. Assigned therapist access only

- Authenticate as `therapist_a_assigned`.
- Read `case_a_1`, its current session, transcript, and draft report.
- Authenticate as `therapist_a_unassigned`.
- Attempt the same reads against `case_a_1`.

Expected:

- Assigned therapist receives `200`.
- Unassigned therapist receives `403` with care-team denial behavior.

Evidence:

- One successful read sample for the assigned therapist.
- One denied read sample for the unassigned therapist.

### 4. Clinical supervisor org-wide access

- Authenticate as `supervisor_a`.
- Read `case_a_1` even when not directly assigned.
- Confirm access to other `org_a` cases.

Expected:

- Supervisor can read all `org_a` clinical cases.
- Supervisor still cannot read any `org_b` case.

Evidence:

- Successful read sample for unassigned `org_a` case.
- Denied cross-org sample.

### 5. Org admin assignment-safe default

- Authenticate as `org_admin_a`.
- Read assignment-safe routes:
  - `/organizations/current/memberships`
  - `/cases/{case_id}/care-team`
- Attempt clinical reads for `case_a_1`, its session, transcript, and report.

Expected:

- Assignment-safe metadata routes succeed.
- Clinical routes fail with `403`.

Evidence:

- One success sample for assignment-safe metadata.
- One denied clinical read sample.

### 6. Explicit clinical grant through care-team assignment

- From `org_admin_a` or `supervisor_a`, assign `org_admin_a` to `case_a_1`
  through the care-team route.
- Re-run clinical reads as `org_admin_a`.
- Attempt clinical mutations such as session creation or transcript patch as
  `org_admin_a`.
- Attempt one artifact-generation mutation such as feature extraction, AI
  review generation, or ML review generation as `org_admin_a` after the grant.
- Attempt one sensitive source/export read such as reviewed CHAT export,
  signed report export, or retained audio retrieval as `org_admin_a` after the
  grant.

Expected:

- If launch policy keeps org admin without a clinical grant by default, the
  reads become allowed only after the explicit care-team assignment.
- Clinical mutations still fail for `org_admin_a` unless a narrower launch rule
  explicitly delegates that action.
- Sensitive source/export reads still fail for `org_admin_a` unless a narrower
  launch rule explicitly delegates that action.
- The case record shows the assignment in audit-safe metadata.

Evidence:

- Assignment request/response snippet.
- Before/after read results.
- One denied mutation sample after the read grant is active.
- One denied artifact-generation sample after the read grant is active.
- One denied sensitive source/export sample after the read grant is active.

### 7. Platform operator routine denial

- Authenticate as `platform_operator_a` without break-glass claims.
- Attempt to read `case_a_1`.

Expected:

- Routine clinical read is denied with `403`.

Evidence:

- Denied request/response snippet.

### 8. Scoped break-glass case access

- Authenticate as `platform_operator_a` with valid break-glass reason and
  expiry less than or equal to one hour.
- Call `/api/v1/cases/{case_id}/break-glass-access` for `case_a_1`.
- Attempt the same route for `case_b_1` while active org is `org_a`.

Expected:

- Scoped break-glass access succeeds only for the targeted `org_a` case.
- Cross-org scoped access is denied.
- An audit event is written with actor, action, target, outcome, timestamp, and
  correlation ID.

Evidence:

- Successful scoped-access response for `case_a_1`.
- Denied cross-org scoped-access response.
- Audit event snippet with sensitive content redacted.

### 9. Break-glass expiry fail-closed

- Reuse the platform operator after the break-glass expiry time passes.
- Re-call `/break-glass-access`.
- Attempt routine case reads.

Expected:

- Expired break-glass access fails closed on the next request.
- Routine case reads remain denied.

Evidence:

- Expired request/response snippet showing denial.

### 10. Membership revocation fail-closed

- Authenticate as a currently assigned therapist in `org_a`.
- Confirm case access succeeds.
- Revoke that membership from an authorized assignment manager.
- Retry the same clinical reads using a fresh request with the still-cached
  token.

Expected:

- Access fails closed on the next request.
- Care-team assignment is deactivated or otherwise no longer grants access.

Evidence:

- Success-before / denial-after pair.
- Membership revocation response snippet.

## Execution Record Template

Copy this block into the staging evidence file for each run, or start from
[docs/templates/STAGING_TENANT_SAFETY_EVIDENCE_TEMPLATE.md](/Users/porschecaa/lingualens/docs/templates/STAGING_TENANT_SAFETY_EVIDENCE_TEMPLATE.md):

```md
# Tenant-Safety Promotion Gate Evidence

- Date:
- Commit:
- Staging API:
- Supabase project ref:
- Operator:
- Reviewer:
- Result:

## Scenario Results

| Scenario | Result | Evidence reference | Notes |
|---|---|---|---|
| Cross-org clinical read denial |  |  |  |
| Cross-org clinical write denial |  |  |  |
| Assigned therapist access only |  |  |  |
| Clinical supervisor org-wide access |  |  |  |
| Org admin assignment-safe default |  |  |  |
| Explicit clinical grant through care-team assignment |  |  |  |
| Platform operator routine denial |  |  |  |
| Scoped break-glass case access |  |  |  |
| Break-glass expiry fail-closed |  |  |  |
| Membership revocation fail-closed |  |  |  |

## Approval

- Engineering/Product:
- Legal/Privacy:
```

## Pass Criteria

The staging tenant-safety gate passes only when:

- every required scenario is executed;
- every required scenario passes;
- all evidence is captured and reviewable;
- no cross-tenant exposure, routine platform-operator access, or revocation
  bypass is observed;
- any failure triggers rollout freeze until remediated and re-run.

## Failure Handling

Any failure in this document is a promotion blocker.

If a failure indicates cross-tenant exposure, consent bypass, audit loss, or
fabricated provider output:

1. Freeze rollout immediately.
2. Follow [docs/INCIDENT_RESPONSE_RUNBOOK.md](/Users/porschecaa/lingualens/docs/INCIDENT_RESPONSE_RUNBOOK.md).
3. Re-run the full gate after remediation, not only the failed scenario.
