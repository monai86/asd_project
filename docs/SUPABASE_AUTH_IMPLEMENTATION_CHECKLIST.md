# Supabase Auth Implementation Checklist

Date: 2026-06-28

This checklist maps the remaining Supabase Auth launch work to concrete files,
components, routes, and tests in the current repository. Use it when assigning
implementation work in `apps/lingualens-app/` and `apps/api/`.

Contract:
[docs/SUPABASE_AUTH_CONTRACT.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_CONTRACT.md)

Rollout tracker:
[docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md)

Staging verifier runbook:
[docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md)

## Frontend Work Checklist

### 1. Browser auth bootstrap and session sync

Primary files:

- [supabase-auth-runtime-bridge.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/supabase-auth-runtime-bridge.tsx)
- [supabase-browser-auth.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/supabase-browser-auth.ts)
- [supabase-access-session.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/supabase-access-session.ts)
- [supabase-session-source.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/supabase-session-source.ts)
- [supabase-session-token.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/supabase-session-token.ts)

Checklist:

- [ ] Confirm the real Supabase session payload always populates:
  - `aal`
  - `app_metadata.role`
  - `app_metadata.membership_active`
  - `app_metadata.invitation_status`
  - `app_metadata.organization_id`
  - `app_metadata.organizations`
- [x] Fail closed when any required launch claim is absent or malformed.
  Maintained browser-auth parsing now rejects sessions that lack a valid
  `aal`, approved launch role, boolean `membership_active`, or valid
  invitation status, instead of silently promoting them into an authenticated
  workspace state.
- [ ] Verify browser auth snapshot refresh happens after:
  - sign-in
  - MFA verify
  - password recovery completion
  - invitation acceptance if that flow returns to the app
  - organization switching
- [x] Ensure stale browser state cannot leave an old active organization or
  invalid `aal2` session cached after logout or claim downgrade.
  Maintained browser-auth sync now clears the stored browser snapshot,
  organization hint, and cached session token on logout or malformed-claim
  downgrade, so the frontend cannot keep sending a stale Bearer token after
  the workspace has already failed closed.

### 2. Login, recovery, and invitation-only messaging

Primary files:

- [supabase-login-form-client.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/supabase-login-form-client.tsx)
- [supabase-browser-client.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/supabase-browser-client.ts)
- [supabase-browser-client-config.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/supabase-browser-client-config.ts)

Checklist:

- [ ] Keep sign-in limited to email/password on the real Supabase project.
- [ ] Keep public signup absent from the launch UI.
- [ ] Route password recovery through the Supabase-managed reset path only.
- [x] Show explicit fail-closed status when browser config or project config is
  missing.
  Maintained login UI now disables sign-in/recovery and shows explicit
  fail-closed status when `NEXT_PUBLIC_SUPABASE_URL` or
  `NEXT_PUBLIC_SUPABASE_ANON_KEY` is missing, and also rejects malformed
  browser config such as non-HTTPS/non-Supabase URLs or invalid publishable
  key formats instead of attempting browser auth bootstrap.
- [x] Confirm post-login routing does not bypass MFA or organization-selection
  gates.
  Maintained route tests now prove the post-login destinations still stop at
  the Supabase MFA gate for `aal1` sessions and still require explicit
  organization selection for ambiguous multi-org sessions before the
  `/today` or `/settings?scope=admin` workspace payload can render.

### 3. MFA enrollment and `aal2` gating

Primary files:

- [supabase-mfa-panel.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/supabase-mfa-panel.tsx)
- [supabase-workspace-access-gate.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/supabase-workspace-access-gate.tsx)
- [app-shell.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/app-shell.tsx)

Checklist:

- [x] Force `aal1` sessions to the MFA gate only.
- [x] Force TOTP enrollment when no verified factor exists after invitation
  acceptance.
- [x] Refresh the browser session and access snapshot after successful MFA
  verification.
  Maintained Supabase gate tests now prove that an accepted `aal1` session with
  no verified factor is driven into TOTP enrollment, and that successful MFA
  verification refreshes the browser session/access snapshot into an `aal2`
  authenticated workspace state.
- [x] Verify no case/report/settings workspace route opens until the session is
  `aal2`.
  Maintained frontend route and shell tests now cover both page-level and
  `AppShell`-level gating so `aal1` Supabase sessions stop at the MFA screen
  and do not render workspace payload or chrome until the session becomes
  `aal2`.
- [x] Add or keep explicit unavailable/error states for MFA factor loading,
  enrollment, and verification failures.
  Maintained MFA panel tests now cover factor-load failure, enrollment failure,
  and verification failure with explicit alert states while keeping workspace
  access blocked.

### 4. Active organization selection and switching

Primary files:

- [supabase-workspace-access-gate.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/supabase-workspace-access-gate.tsx)
- [active-organization-summary.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/active-organization-summary.tsx)
- [supabase-browser-auth.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/supabase-browser-auth.ts)
- [api.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/api.ts)

Checklist:

- [x] Require explicit selection when `organizations` contains multiple active
  memberships and no valid `organization_id` is present.
- [x] Keep a sole active organization from requiring a redundant selection
  screen when `organization_id` is absent but only one valid organization is
  available.
- [x] Persist organization choice as a hint only; do not auto-open ambiguous
  sessions silently.
  Maintained browser-auth state now stores the last explicitly chosen
  organization as a separate browser hint, carries that hint forward only for
  the same user, and keeps ambiguous `aal2` sessions blocked at the
  organization-selection gate until the user explicitly confirms the choice
  again.
- [x] Ensure `X-Organization-Id` follows the explicitly selected active
  organization on every backend request.
- [x] Verify org switching updates both UI state and backend request context.
- [x] Confirm one active organization per session at all times.
  Maintained workspace access gating now keeps exactly one active
  `organizationId` in the authenticated access session, clears active-org
  context before org switching, and requires an explicit confirmation step
  before ambiguous multi-org sessions can become authenticated again.

### 5. Local pilot admin UX separation from production auth UX

Primary files:

- [settings-workspace-client.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/settings-workspace-client.tsx)

Checklist:

- [x] Keep the local pilot invitation/membership tools clearly labeled as
  scaffold or pilot-only where they do not represent real Supabase delivery.
- [x] Prevent the launch documentation or admin UI from implying that the local
  acceptance flow is the production invitation path.
  Maintained settings admin UX now adds explicit pilot-only boundary copy that
  states the panel does not send real invitation emails, does not represent
  production Supabase invitation acceptance, and does not provision production
  MFA enrollment on its own.
- [ ] Decide whether production will hide, replace, or re-scope these pilot
  controls once real Supabase lifecycle flows are live.

## Backend Work Checklist

### 6. Token validation and principal construction

Primary files:

- [supabase_auth.py](/Users/porschecaa/lingualens/apps/api/app/auth/supabase_auth.py)
- [security.py](/Users/porschecaa/lingualens/apps/api/app/core/security.py)
- [config.py](/Users/porschecaa/lingualens/apps/api/app/core/config.py)

Checklist:

- [ ] Replace any local-only signing assumptions with the production Supabase
  validation method actually used by staging and production.
- Maintained backend auth scaffold now covers all three local verifier paths:
  HS256 shared-secret validation, local JWKS JSON validation, and remote JWKS
  URL validation with cache reuse, key-refresh-on-miss, and fetch-failure
  fail-closed behavior. The remaining open work is selecting and proving the
  real staging/production verifier mode against the actual Supabase projects.
- [x] Keep MFA and invitation validation fail closed in non-mock runtime.
  Maintained Supabase auth scaffold tests now prove non-mock runtime rejects
  inactive memberships, rejects non-`aal2` sessions when MFA is required, and
  rejects non-accepted invitation states before any protected route work can
  continue.
- [x] Validate the launch role set only:
  - `therapist`
  - `clinical_supervisor`
  - `org_admin`
  - `platform_operator`
  Maintained Supabase auth code now centralizes the allowed role set in
  `ALLOWED_SUPABASE_ROLES`, and scaffold tests prove invalid roles fail closed
  while the four launch roles continue through the expected tenant and
  authorization paths.
- [x] Keep claim-shape validation strict:
  - `membership_active` must be a boolean, not a truthy string fallback
  - `role` must be one of the approved launch roles
  - `invitation_status` must be one of the approved lifecycle states
  - if `organizations` or `organization_memberships` is present, the active
    `organization_id` and `role` must match one listed membership
  - if a listed membership carries `active`, it must be a boolean and the
    selected membership must remain active
  - if `break_glass` is present, it must be a dict with boolean `active` and
    integer `expires_at` before any scoped grant is considered
  Maintained Supabase auth tests now cover invalid role, invitation status,
  membership-active type, malformed membership entries, inactive selected
  memberships, malformed break-glass payloads, and non-integer break-glass
  expiry so malformed claims fail closed instead of widening access or
  surfacing a server error.
- [x] Confirm `organization_id` comes from trusted claims and is not widened by
  fallback behavior.
  Maintained Supabase auth now accepts `X-Organization-Id` only as an explicit
  active-organization selector that must match a listed membership claim,
  derives the effective org-scoped role from that membership, and otherwise
  fails closed on ambiguous or missing membership context.
- [x] Confirm revocation is enforced by the next request boundary defined by the
  launch model.
  Maintained organization-admin route tests now prove a therapist can read an
  assigned case before revocation, loses that read on the very next request
  after membership revocation, and receives a fail-closed care-team denial.

### 7. Authorization helpers and launch role cleanup

Primary files:

- [authorization.py](/Users/porschecaa/lingualens/apps/api/app/auth/authorization.py)
- [security.py](/Users/porschecaa/lingualens/apps/api/app/core/security.py)
- [organization_admin.py](/Users/porschecaa/lingualens/apps/api/app/api/v1/routes/organization_admin.py)
- [privacy.py](/Users/porschecaa/lingualens/apps/api/app/api/v1/routes/privacy.py)
- [audit.py](/Users/porschecaa/lingualens/apps/api/app/api/v1/routes/audit.py)

Checklist:

- [x] Remove or replace legacy role aliases that do not belong to the launch
  model:
  - `admin`
  - `supervisor`
- [x] Replace `require_admin` and related route guards with launch-correct
  authorization rules.
  Maintained backend auth and route guards now accept only the four launch
  roles in both Supabase and mock runtime paths, reject legacy mock-role
  aliases such as `admin` and `supervisor`, and keep org-admin route protection
  on explicit `org_admin` helpers instead of broad legacy admin aliases.
- [x] Privacy queue and audit log routes now use org-admin guards, and the
  audit log API is scoped to the caller's organization.
- [x] Org-admin privacy queue/update responses are now assignment-safe
  summaries and omit free-text request reason, requester identity, and admin
  note fields.
- [x] Keep org-admin access assignment-safe by default and prevent accidental
  clinical read expansion through helper reuse.
  Maintained backend helpers now keep default org-admin case reads denied,
  reopen case access only after explicit care-team assignment, and block
  org-admin case creation as a self-bootstrap path.
- [x] Keep case creation aligned with the canonical care-team grant path.
  Maintained backend case creation now restricts therapist bootstrap to the
  authenticated therapist, requires clinical supervisors to name an active
  therapist membership as primary, and rejects extra care-team preload outside
  the dedicated assignment route.
- [x] Keep non-therapist org-admin clinical grants read-oriented unless a
  narrower rule says otherwise.
  Maintained backend routes now allow an explicitly assigned `org_admin` to
  read granted case/session/transcript/report content while rejecting routine
  clinical mutations such as session creation, transcript edits/QA, audio job
  mutations, therapy-goal mutations, report draft edits, feature extraction,
  AI-review generation/patch, and ML-review generation.
- [x] Keep sensitive source/export surfaces narrower than ordinary read grants.
  Maintained backend routes now require therapist or clinical-supervisor role
  for retained audio metadata/bytes, reviewed CHAT export, and signed report
  export access even when an `org_admin` holds a granted case read.
- [x] Keep transcript attestation and report sign-off therapist-only at the API
  boundary.
  Maintained backend routes now reject transcript attestation and report
  sign-off requests from `clinical_supervisor` and `org_admin` sessions before
  service logic runs, preserve authenticated therapist identity matching for
  attestation/sign-off payloads, and write transcript-attestation audit events
  with the authenticated actor instead of a generic system placeholder.
- [x] Keep platform operators excluded from routine clinical access outside the
  scoped break-glass endpoint.
  Maintained backend routes now deny routine platform-operator case creation and
  continue to deny direct clinical reads outside the scoped break-glass path.

Current remaining code drift to resolve:

- Review maintained backend services and routes for any additional legacy role
  aliases outside the auth/admin cleanup already completed.

### 8. Invitation, membership, revocation, and break-glass routes

Primary files:

- [organization_admin.py](/Users/porschecaa/lingualens/apps/api/app/api/v1/routes/organization_admin.py)
- [0010_add_auth_lifecycle_tables.py](/Users/porschecaa/lingualens/apps/api/app/db/migrations/versions/0010_add_auth_lifecycle_tables.py)

Checklist:

- [x] Verify invitation acceptance creates or reactivates membership exactly as
  the launch model requires.
- [x] Enforce 7-day invitation expiry end to end.
- [x] Ensure expired invitations require newly issued invitations.
- [x] Ensure membership revocation deactivates care-team access and fails closed
  on the next request.
  Maintained invitation repositories now issue fixed 7-day invitations, reject
  expired invitations with explicit reissue-only handling, reject repeated
  acceptance of already accepted invites, reject attempts to bind one accepted
  invitation email to a different `user_id`, and keep membership revocation
  deactivating care-team access so the next request is denied.
- [x] Ensure break-glass requires category plus free text, one case scope, and
  one-hour expiry.
  Maintained auth parsing and route guards now require a scoped break-glass
  `case_id`, a non-empty category, non-empty free-text reason, and an expiry
  that remains within the one-hour ceiling before allowing the scoped case
  access route to succeed.

## Test Checklist

Frontend tests to extend or keep current:

- [supabase-browser-auth.test.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/__tests__/supabase-browser-auth.test.ts)
- [supabase-workspace-access-gate.test.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/__tests__/supabase-workspace-access-gate.test.tsx)
- [supabase-login-form-client.test.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/__tests__/supabase-login-form-client.test.tsx)
- [session-workspace-audio-auth.test.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/__tests__/session-workspace-audio-auth.test.tsx)
- [api-auth.test.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/__tests__/api-auth.test.ts)

Backend tests to extend or keep current:

- [test_supabase_auth_scaffold.py](/Users/porschecaa/lingualens/apps/api/tests/test_supabase_auth_scaffold.py)
- [test_organization_admin_routes.py](/Users/porschecaa/lingualens/apps/api/tests/test_organization_admin_routes.py)
- [test_tenant_isolation_phase1.py](/Users/porschecaa/lingualens/apps/api/tests/test_tenant_isolation_phase1.py)

Checklist:

- [x] Add tests for real launch role normalization if legacy role aliases are
  removed.
  Maintained backend tests now reject legacy mock-role aliases directly and
  keep Supabase claim tests rejecting invalid role values outside the launch
  set.
- [x] Add tests for explicit organization switching on authenticated requests.
- [x] Add tests that prove `aal1` never reaches workspace content.
- [x] Add tests for invitation expiry and reissue-only handling.
- [x] Add tests for revocation fail-closed on the next request boundary.
- [x] Add tests for break-glass reason shape now that category plus free text
  is explicit in the route contract.

## Documentation and Evidence Checklist

Primary files:

- [SUPABASE_AUTH_CONTRACT.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_CONTRACT.md)
- [SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_ROLLOUT_GAP_TRACKER.md)
- [STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md)
- [PRODUCTION_SAAS_LAUNCH_TRACKER.md](/Users/porschecaa/lingualens/docs/PRODUCTION_SAAS_LAUNCH_TRACKER.md)

Checklist:

- [ ] Keep the contract, rollout tracker, and launch tracker aligned when any
  auth invariant changes.
- [ ] Record the final staging auth evidence under
  `docs/release_artifacts/auth_verifier/`.
- [ ] Link the auth-verifier evidence package from the tenant-safety evidence
  package.
- [ ] Update launch docs when legacy role aliases are removed from code.

## Recommended Execution Sequence

1. Clean up backend role drift and route guards first.
2. Finish real claim validation and session refresh behavior.
3. Finish MFA and organization-selection UX against the real Supabase session.
4. Close invitation/revocation/break-glass lifecycle gaps.
5. Extend tests for the final launch auth path.
6. Run staging tenant-safety and auth evidence capture.
