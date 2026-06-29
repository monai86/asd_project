# Production SaaS First Launch Backlog

Date: 2026-06-27

This backlog turns the agreed first-launch decisions into an execution order for
the current repository. It assumes the canonical product stays in
`apps/lingualens-app/` and `apps/api/`.

Linked decision:
[docs/adr/0017-launch-controlled-single-clinic-supabase-rollout.md](/Users/porschecaa/lingualens/docs/adr/0017-launch-controlled-single-clinic-supabase-rollout.md)

Auth rollout detail:
[docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md)

Implementation checklist:
[docs/SUPABASE_AUTH_IMPLEMENTATION_CHECKLIST.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_IMPLEMENTATION_CHECKLIST.md)

Supabase setup runbook:
[docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md)

Today execution checklist:
[docs/TODAY_LAUNCH_EXECUTION_CHECKLIST.md](/Users/porschecaa/lingualens/docs/TODAY_LAUNCH_EXECUTION_CHECKLIST.md)

Current remaining count: 11 launch workstreams.

## 1. Create the real Supabase tenancy skeleton

- [x] Create Supabase organization `LinguaLens`.
- [x] Create `lingualens-staging` in `ap-southeast-1`.
- [x] Create `lingualens-production` in `ap-southeast-1`.
- [ ] Record remaining owner contacts in deployment docs.

Definition of done:
- Both projects exist.
- Staging and production use the same architecture class, not different stacks.
- Project refs, dashboard/API URLs, publishable keys, and verifier URLs are
  recorded.
- Named human owner contacts are recorded.

## 2. Replace local auth scaffolding with real Supabase claim issuance

- [ ] Configure the real production claim contract.
- Configure invitation-only onboarding with public signup disabled.
- Implement real claim issuance for:
  - active `organization_id`
  - organization `role`
  - `membership_active`
  - `invitation_status`
  - break-glass claim metadata
  - top-level `aal`
- Move backend verification to the approved production signing method for the
  real Supabase project.

Definition of done:
- Backend accepts real Supabase tokens from staging.
- Non-mock runtime fails closed without the required claims.

## 3. Wire the frontend auth lifecycle for the launch model

- [ ] Replace the remaining scaffold assumptions in the frontend auth path with
  fully verified real Supabase flows.
- Implement login with email/password.
- Implement mandatory TOTP enrollment after invitation acceptance.
- Implement mandatory MFA challenge so only `aal2` sessions reach app access.
- Implement expired invitation handling as issue-new-invitation only.
- Implement recovery flow using Supabase-managed reset with normal membership
  and MFA gates afterward.
- Keep explicit organization selection for multi-org memberships and preserve
  automatic single-membership resolution.
- Remember last active organization as a hint only when session context is
  ambiguous.

Definition of done:
- `aal1` can reach MFA screens only.
- `aal2` is required before any clinical or admin workflow access.

## 4. Enforce the launch role and access model in backend plus UI

- [ ] Verify the agreed role matrix in real-claim runtime.
- Keep clinic roles limited to therapist, clinical supervisor, and org admin.
- Keep platform operator separate from clinic roles.
- Enforce therapist access to assigned cases only.
- Enforce clinical supervisor access to all cases in the active organization.
- Enforce org admin access to assignment-safe metadata only by default.
- Require explicit clinical grant through care-team assignment for additional
  clinical access.
- Keep platform-operator clinical access break-glass only.

Definition of done:
- API and UI behavior match the agreed role matrix.
- No role receives broader access by fallback or UI leakage.

Current local evidence:

- Maintained backend role guards now prove therapist access remains limited to
  assigned cases only, while `clinical_supervisor` retains active-org-wide
  clinical oversight without case-by-case assignment.
- Maintained backend role guards now prove `org_admin` remains assignment-safe
  by default and gains clinical read access only after an explicit care-team
  grant.
- Maintained backend and policy tests now prove `platform_operator` does not
  inherit clinic-role access and remains blocked from routine case creation,
  org membership management, and ordinary clinical reads.
- Maintained artifact access tests now prove an explicitly granted `org_admin`
  may inspect granted feature/AI/ML/report artifacts but still cannot run
  routine clinical mutation routes.

## 5. Make care-team assignment the canonical clinical grant path

- [ ] Lock care-team assignment in as the only clinical grant path.
- Add/verify assignment flows for org admin and clinical supervisor.
- Require one primary assigned therapist at case assignment time.
- Keep case creation bootstrap narrow:
  only the authenticated therapist or one active therapist membership selected
  by a clinical supervisor may seed the initial care-team record.
- Reject extra care-team preload at case creation so additional clinical grants
  always flow through the dedicated care-team assignment route.
- Keep org-admin explicit clinical grant read-oriented by default:
  assigned org admins may inspect granted case/session/transcript/report
  content, but routine clinical mutation stays with therapist and clinical
  supervisor routes unless a stricter rule already applies.
- Keep sensitive source/export surfaces narrower than ordinary clinical reads:
  reviewed CHAT export, signed report export, and retained audio
  metadata/bytes stay limited to therapist or clinical-supervisor sessions
  even when an org admin has a granted case read.
- Block report sign-off until a new primary therapist is assigned if the current
  primary is removed or revoked.
- Keep supervisor sign-off as non-routine and keep sign-off exceptions out of
  launch scope.

Definition of done:
- Every report-eligible case has exactly one primary assigned therapist.
- Sign-off is blocked when no primary signer exists.

Current local evidence:

- Maintained backend assignment routes now prove `clinical_supervisor` and
  `org_admin` can manage care-team assignment while broader org-admin
  membership powers remain separate.
- Maintained case-creation guards now prove therapist bootstrap stays narrow:
  therapist-created cases keep the authenticated therapist as primary, and
  supervisor-created cases require one active therapist membership to be named
  as primary at creation time.
- Maintained case-creation guards now reject extra care-team preload so
  additional grants must flow through the dedicated care-team route.
- Maintained primary-therapist lifecycle tests now prove promotion,
  revocation, and primary clearing happen through assignment/membership paths,
  and report sign-off remains blocked when no primary therapist is available.
- Maintained sensitive-surface tests now prove explicit org-admin clinical
  grants stay read-oriented and do not unlock routine artifact mutation,
  retained audio access, or sensitive export paths.

## 6. Move media handling onto Supabase private Storage

- [ ] Replace staging and production media storage with Supabase private
  Storage.
- Use opaque generated storage keys only.
- Issue short-lived signed upload URLs through FastAPI.
- Keep uploaded media untrusted until backend completion verification succeeds.
- Expired/failed uploads must create a new upload intent.

Current local evidence:

- Maintained local-private upload intent flow now generates opaque object keys
  only; storage paths no longer embed case IDs, session IDs, or original
  filenames.
- Maintained upload intent responses continue to expose only short-lived upload
  routes plus audio metadata, not raw storage paths for browser writes.
- Maintained local upload lifecycle now keeps uploaded bytes in
  `pending_verification` state until `complete-upload` succeeds; file download
  stays blocked before verification.
- Maintained local upload lifecycle now rejects stale or already-consumed upload
  intents, so a failed or incomplete attempt must be replaced by a new upload
  intent.
- Maintained browser/API responses now redact `object_key` from upload-job and
  audio-metadata payloads; the storage key stays server-side only.
- Maintained processing start now rejects caller-supplied `audio_id` values
  until the referenced artifact reaches verified `uploaded` state.
- Maintained completion and consent-withdrawal tests still prove upload
  verification and unlink/delete behavior against the opaque-key path.

Definition of done:
- No human-readable identifiers appear in storage object paths.
- The active staging media path uses Supabase private Storage end to end.

## 7. Move processing onto a durable worker stack

- [ ] Provision the durable queue/worker runtime.
- Choose and provision the managed queue/worker stack.
- Ensure processing starts only from explicit user action.
- Enforce one active processing job per audio artifact.
- Make reprocess create a new job linked to the same verified audio artifact.
- Make non-essential provider failures return explicit unavailable states, never
  fabricated outputs.

Current local evidence:

- Maintained processing routes start job creation only from explicit user API
  action; the worker does not auto-start new artifacts on its own.
- Maintained audio-processing service now blocks a second active job for the
  same uploaded audio artifact while a prior job remains queued or running.
- Maintained audio-processing service now allows reprocess to create a new job
  on the same verified audio artifact after the prior job reaches a terminal
  state.
- Maintained provider handling already returns explicit failed/unavailable job
  states with provider error reasons instead of fabricating fallback content
  when fallback is not explicitly allowed.

Definition of done:
- Staging jobs survive process restarts.
- Job history cleanly separates attempts.

## 8. Keep transcript authority and downstream invalidation strict

- [x] Prove stale downstream outputs cannot be signed.
- Ensure therapist-reviewed transcript remains the only report-eligible
  transcript source.
- Keep transcript attestation therapist-only at the maintained API boundary.
- Ensure transcript edits immediately stale dependent features, AI review, and
  draft reports.
- Keep signed report snapshots immutable and route post-sign-off edits into new
  draft revisions.

Current local evidence:

- Maintained backend transcript patch flow clears `feature_set_id`,
  `ml_result_id`, `ai_review_id`, and `report_id`, resets transcript
  attestation/review state, and keeps existing report sign-off blocked until
  therapist attestation is re-established.
- Maintained frontend review flow now proves that editing an attested
  transcript immediately flips the workspace back to review-required state,
  clears QA/attestation state, and disables report generation until review is
  completed again.
- Maintained pilot report flow already proves signed report snapshots remain
  immutable after a later draft revision path.

Definition of done:
- No stale downstream output can be signed off after transcript edits.

## 9. Finish AI and research gating for launch scope

- [ ] Keep AI and reference outputs explicitly non-essential at launch.
- Keep AI review default off and organization-level opt-in only.
- Show explicit unavailable states when AI review is disabled.
- Keep reference-evidence outputs gated and non-essential for launch.
- Keep research evaluation/build routes local-only and unavailable in
  production-like runtime.
- Keep provider-discovery metadata behind authenticated runtime sessions.

Current local evidence:

- Maintained API runtime now declares `ai_review_policy =
  organization_opt_in_default_off` from `/api/v1/settings`.
- Maintained repository/runtime scaffolding now keeps `pilot_org_001` as an
  explicit local opt-in while other organizations fail closed by default until
  `ai_review_enabled` is turned on.
- Maintained AI-review routes now return an explicit unavailable error when an
  organization has not enabled AI review, instead of silently generating
  review content.

Definition of done:
- Core launch workflow does not depend on AI or reference-evidence providers.

## 10. Prove tenant safety on staging with real claims

- [ ] Pass the tenant-safety promotion gate on staging.
- Execute
  [docs/STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md)
  and store the completed evidence package with the release artifacts. Start the
  artifact with `bash scripts/create_staging_tenant_safety_evidence.sh` and use
  `bash scripts/run_staging_tenant_safety_probe.sh <scenario>` for repeatable
  API capture, `bash scripts/run_staging_tenant_safety_core_gate.sh` for the
  fail-fast core matrix plus auto-generated summary artifact, and
  `bash scripts/summarize_staging_tenant_safety_probes.sh` when a manual or
  custom summary export is needed.
- Add staging verification covering:
  - cross-org denial for reads and writes;
  - therapist assignment-only access;
  - supervisor org-wide access;
  - org admin assignment-safe metadata only;
  - platform operator denial without break-glass;
  - one-case break-glass with one-hour expiry;
  - fail-closed behavior on revocation and break-glass expiry.

Definition of done:
- The `Tenant-Safety Promotion Gate` passes in staging using real Supabase
  claims and production-like infrastructure.

## 11. Finish production operational controls

- [ ] Close the operational controls gap on production-like infrastructure.
- Integrate the chosen managed secret store and execute the rotation procedure.
- Integrate the chosen observability provider with operational metadata only.
- Keep notifications/email operational-only and free of clinical content.
- Preserve audit shape as actor, action, target, outcome, timestamp, and
  correlation ID with no raw clinical identifiers or content.
- Enforce privacy deletion blocking under legal hold and retain sign-off
  evidence per policy.

Current local evidence:

- Maintained notification safety validation allows generic operational copy but
  rejects child codes, transcript fragments, filenames, storage-key hints, and
  email addresses without echoing the blocked content back in errors.
- Maintained audit safety validation enforces actor/action/target/outcome/
  correlation/timestamp shape and rejects clinical or identifying content in
  audit messages.
- Maintained observability safety validation accepts only privacy-safe event
  names, tags, route templates, numeric measurements, and generic details.
- Maintained privacy-operation flow now proves legal hold blocks deletion
  completion and completed deletion review preserves audit/sign-off evidence
  without returning raw request reason/admin-note content.

Definition of done:
- Production-like runtime can pass operational checks without local/demo
  dependencies.

## 12. Close launch gates and run the first clinic rollout

- [ ] Close final launch gates and obtain approvals.
- Resolve all unresolved high/critical security findings.
- Pass backup/restore drill on the production-like stack.
- Confirm country allowlist is Thailand only.
- Confirm first rollout remains one clinic tenant.
- Capture explicit go-live approval from engineering/product and legal/privacy.
- Freeze rollout immediately on cross-tenant exposure, consent bypass, audit
  loss, or fabricated ASR output.

Definition of done:
- The first clinic can go live without violating the agreed launch boundary.
