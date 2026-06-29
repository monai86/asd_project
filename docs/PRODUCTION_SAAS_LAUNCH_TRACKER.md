# Production SaaS Launch Tracker

Date: 2026-06-27

This tracker records the agreed first-launch shape for lingualens and maps it to
the current repository state. It is for the first controlled clinic rollout,
not a public self-serve SaaS launch.

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

## Remaining Launch Workstreams

11 workstreams remain before launch can be considered ready. They are tracked
in execution order in
[docs/PRODUCTION_SAAS_FIRST_LAUNCH_BACKLOG.md](/Users/porschecaa/lingualens/docs/PRODUCTION_SAAS_FIRST_LAUNCH_BACKLOG.md).

Important:

- The 11 remaining items are launch-level workstreams, not 11 untouched code
  tasks.
- A large share of the repository-local implementation and fail-closed proof is
  already complete.
- The current critical path is now dominated by external setup:
  Supabase dashboard configuration, staging deployment wiring, real claim
  issuance, and staging evidence capture.

## Done

- Canonical product boundary stays in `apps/lingualens-app/` and `apps/api/`.
- Production platform direction is Supabase Auth/Postgres/private Storage plus
  FastAPI as the clinical policy boundary.
- Responsive web/PWA-only direction is accepted.
- Invitation, membership revocation, break-glass scaffolding, and local
  Supabase JWT contract scaffolding exist in the backend.
- Organization/care-team guard foundations and PostgreSQL RLS scaffold exist.
- Role-policy alignment now reflects the agreed launch matrix:
  - `clinical_supervisor` has org-wide clinical oversight;
  - `org_admin` is assignment-safe by default, without clinical read by
    default;
  - care-team assignment management is available to `clinical_supervisor` and
    `org_admin`.
- Local/private upload-intent workflow and report sign-off immutability
  foundations exist.
- Local runtime scaffolding now exercises:
  - explicit active-organization session selection for multi-org mock users;
  - `aal1` stopping at MFA-only screens;
  - `aal2` as the minimum for mock workspace access.
- Local backend now enforces:
  - research evaluation helpers under `/api/v1/evaluation/*` are blocked in
    production-like runtime and remain local/mock-only tooling;
  - provider-discovery endpoints for reports, features, ML, and transcription
    now require an authenticated runtime session instead of remaining public;
  - explicit primary-therapist tracking on cases;
  - primary-therapist promotion/clearing through care-team assignment and
    revocation paths;
  - case creation bootstrap limited to the authenticated therapist or one
    active therapist membership chosen by a clinical supervisor;
  - extra care-team grants blocked at case creation so the dedicated care-team
    route remains the canonical grant path;
  - explicitly assigned org admins can inspect granted case/session/transcript/
    report content but cannot run routine clinical mutation routes, including
    artifact generation/edit paths such as feature extraction, AI-review
    generation, and ML-review generation;
  - retained audio metadata/bytes, reviewed CHAT export, and signed report
    export remain therapist or clinical-supervisor-only even after an
    org-admin read grant;
  - transcript attestation and report sign-off route entry limited to
    therapist-role sessions before downstream service logic runs, with
    attestation audit actor attribution bound to the authenticated therapist;
  - report sign-off restricted to the authenticated primary assigned therapist.
- Local frontend/report flow now reflects that rule by:
  - showing primary assigned therapist context from the case record;
  - removing client-controlled signer name override from report finalization.
- Canonical case detail UI now exposes a pilot admin flow for:
  - viewing current care-team assignments;
  - promoting/reassigning the primary therapist through the existing backend
    care-team route;
  - deactivating an assignment so primary removal visibly blocks sign-off until
    reassigned.
- Local mock admin helpers now derive org/role headers from the active mock
  session instead of fixed org defaults.
- Local pilot access lifecycle UI now covers:
  - invitation creation;
  - invitation acceptance into active membership;
  - preparing an invited `aal1` session so the next app page stops at the MFA
    gate until promoted to `aal2`.
- Maintained shell UI now exposes explicit active-organization switching for
  multi-org mock sessions, while keeping exactly one active organization per
  session.
- Maintained Supabase browser auth and workspace gating now keep the last
  explicit organization as a hint only, require ambiguous multi-org sessions
  to stop at an explicit confirmation step before app access, and clear the
  active organization before switching contexts.
- Maintained pilot admin settings now state explicitly that the invitation and
  membership controls are pilot-only scaffolding, do not send real invitation
  emails, and are not the production Supabase invitation-acceptance path.
- Source-of-truth rules already require:
  - production fail-closed behavior;
  - explicit AI opt-in;
  - operational-only notifications;
  - audit shape with correlation ID;
  - privacy deletion blocked by legal hold;
  - observability metadata without clinical content;
  - backup/restore and incident-response runbooks.
- Shared launch language has now been captured in [CONTEXT.md](/Users/porschecaa/lingualens/CONTEXT.md):
  - `Invitation-Only Onboarding`
  - `Active Organization Session`
  - `Organization Role`
  - `Platform Operator`
  - `Break-Glass Access`
  - `Clinical Grant`
  - `Primary Assigned Therapist`
  - `Controlled Clinic Rollout`
  - `Assignment-Safe Metadata`
  - `Tenant-Safety Promotion Gate`

## In Progress

- Supabase organization `LinguaLens`, staging project
  `cbhwxklvcpgizeqriqxi`, and production project `rftslmbgbudqsypknzss` now
  exist and are recorded in
  [docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md](/Users/porschecaa/lingualens/docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md),
  but Codex still lacks direct connector permission to inspect/manage them.
- Phase 1 tenant isolation foundation is implemented locally but not yet
  verified against real Supabase Auth claims in staging.
- The execution artifact for that staging proof now exists in
  [docs/STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md),
  with a reusable evidence file at
  [docs/templates/STAGING_TENANT_SAFETY_EVIDENCE_TEMPLATE.md](/Users/porschecaa/lingualens/docs/templates/STAGING_TENANT_SAFETY_EVIDENCE_TEMPLATE.md),
  but no completed staging evidence package exists yet.
- Phase 2 auth lifecycle foundation exists locally, but real invitation
  delivery, MFA enrollment UI, and claim synchronization are not complete.
- Local invitation/membership lifecycle scaffolding now also enforces:
  - fixed 7-day invitation expiry;
  - expired invitations must be replaced by a newly issued invitation;
  - repeated acceptance of an already accepted invitation is rejected;
  - accepted invitation email cannot be rebound to a different `user_id`
    across organizations in the maintained backend scaffold;
  - revoked memberships lose care-team access on the next request boundary.
- Local break-glass scaffolding now also enforces:
  - scoped `case_id` binding for each break-glass grant;
  - one-hour maximum break-glass lifetime;
  - fail-closed denial when the grant case does not match the requested case;
  - fail-closed rejection of malformed break-glass claim payloads before they
    can surface a server error or widen scope.
- Production-like API guards, audit/privacy/report foundations, and runbooks are
  present, but managed infrastructure integrations are not yet wired.
- Primary-therapist and report-signer rules are enforced locally, but the
  production path still needs real Supabase claims, non-mock invitation/MFA
  UX, and staging tenant-safety verification.
- Transcript authority and downstream invalidation are now also proven locally:
  transcript edits clear dependent feature/AI/report links, remove prior
  attestation state, block further report generation/sign-off until therapist
  review is re-completed, and signed report snapshots remain immutable after
  later draft revisions.
- AI-review launch gating is now also tightened locally:
  `/api/v1/settings` declares organization opt-in default-off policy, the
  maintained runtime keeps the pilot org as an explicit local opt-in only, and
  non-opted-in organizations now receive an explicit unavailable response
  instead of silent AI-review generation.
- Audio-processing launch constraints are now also tighter locally:
  a second active job for the same uploaded audio artifact is rejected
  fail-closed, reprocess creates a new job only after the prior attempt reaches
  a terminal state, and provider failures remain explicit failed/unavailable
  job outcomes rather than fabricated outputs.
- Media-path hygiene is now also tighter locally:
  local-private upload intents generate opaque object keys only, without case
  IDs, session IDs, or original filenames in the stored path.
- Upload trust timing is now also tighter locally:
  uploaded bytes remain unverified until backend completion verification
  succeeds, direct file reads stay blocked before verification, and stale
  upload intents must be replaced instead of reused.
- Storage-key exposure is now also tighter locally:
  upload-job responses and audio metadata responses redact `object_key`, and
  processing routes reject unverified caller-supplied audio artifacts.
- Operational-metadata controls are now also proven locally:
  notification safety, audit safety, observability safety, and privacy
  evidence-retention tests all pass against generic-only operational payload
  rules.
- Launch policy is now clarified:
  - one organization represents one clinic at launch;
  - launch scope is one clinic tenant first;
  - country allowlist is Thailand only;
  - billing is out of scope for first launch;
  - provider fallbacks must return explicit unavailable states, never mock or
    fabricated outputs.

## Blocked

- No known mandatory repository-local launch code gap is currently identified
  ahead of the next external handoff. Remaining blockers are live-environment
  or operator-owned unless new staging evidence exposes a concrete code defect.
- No real Supabase custom-claim provisioning exists for:
  - `organization_id`
  - `role`
  - `membership_active`
  - `invitation_status`
  - break-glass metadata
  - top-level `aal`
- Browser-side Supabase login, recovery, TOTP enrollment/challenge, and
  workspace gating scaffolds now exist in the maintained frontend, but they are
  not yet proven end to end against real staging claims and invitation
  delivery.
- Local frontend evidence now proves that `aal1` Supabase sessions stop at the
  MFA gate and do not render workspace routes or shell chrome before the
  session is elevated to `aal2`.
- Browser-side organization selection now supports:
  - automatic single-membership resolution;
  - explicit selection for ambiguous multi-org sessions;
  but real claim issuance and staged verification are still incomplete.
- No staging proof yet exists for these required launch behaviors:
  - therapist can access assigned cases only;
  - clinical supervisor can access all cases in the active organization;
  - org admin is limited to assignment-safe metadata by default;
  - platform operator has no routine clinical access;
  - break-glass access is one-case scoped and expires fail-closed.
- Supabase private Storage is not yet the active staging/production media path.
- Durable queue/worker deployment is not yet the active staging/production job
  path.
- Managed secret-store integration and rotation execution are not yet complete.
- Backup/restore drill has not yet been demonstrated on the production-like
  stack.
- Dependency/security gate still requires zero unresolved high/critical
  findings before launch.
- Go-live approval path is not yet operationalized across
  engineering/product and legal/privacy owners.

## Launch Definition

The first launch is ready only when all of the following are true:

- Supabase staging and production projects exist in `ap-southeast-1`.
- Production auth uses invitation-only email/password plus required TOTP MFA.
- `aal2` is required before app access.
- Public signup is off.
- Production mock/demo mode is forbidden.
- One active organization is selected per session.
- Therapist access is limited to assigned cases.
- Report sign-off belongs to the primary assigned therapist only.
- Transcript authority is therapist-reviewed transcript only.
- AI review remains org-level opt-in and default off.
- Staging tenant-safety verification passes using real Supabase claims.
- Backup/restore drill passes.
- No unresolved high/critical security findings remain.
- Legal/privacy and engineering/product explicitly approve go-live.

## Launch Gate Checklist

- [x] Supabase organization `LinguaLens` exists.
- [x] Staging and production Supabase projects exist in `ap-southeast-1`.
- [ ] Invitation-only email/password plus TOTP MFA is live.
- [ ] `aal2` is required before app access.
- [ ] Public signup is disabled.
- [ ] Explicit organization selection is live for multi-org users.
- [ ] Therapist access is assigned-case only.
- [ ] Clinical supervisor access is active-org-wide.
- [ ] Org admin remains assignment-safe by default.
- [ ] Platform operator access is break-glass only, one case, one hour, fail
  closed on next request.
- [ ] Primary assigned therapist is required and is the only sign-off path.
- [ ] Supabase private Storage is the active media path.
- [ ] Durable queue/worker is the active processing path.
- [x] Transcript edits stale downstream outputs immediately.
- [ ] AI review stays org-opt-in and default off.
- [ ] Staging tenant-safety verification passes with real claims.
- [ ] Backup/restore drill passes.
- [ ] No unresolved high/critical security findings remain.
- [ ] Go-live approval is signed off by engineering/product and legal/privacy.

## Immediate External Dependencies

- Configure Supabase Auth claim issuance to match
  [docs/SUPABASE_AUTH_CONTRACT.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_CONTRACT.md).
- Choose the managed queue/worker and secret-store providers that production
  will actually use.
- Record the remaining named human owners/approvers and complete the staged
  verifier plus tenant-safety evidence runs in
  [docs/TODAY_LAUNCH_EXECUTION_CHECKLIST.md](/Users/porschecaa/lingualens/docs/TODAY_LAUNCH_EXECUTION_CHECKLIST.md).

Use
[docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md)
to execute and record the Supabase organization/project setup.
