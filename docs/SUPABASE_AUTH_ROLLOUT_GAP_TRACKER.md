# Supabase Auth Rollout Gap Tracker

Date: 2026-06-28

This tracker turns the agreed Supabase Auth launch model into concrete
implementation and verification work. It maps the current local foundation to
the remaining production-path gaps for the first controlled clinic rollout.

Contract:
[docs/SUPABASE_AUTH_CONTRACT.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_CONTRACT.md)

Launch tracker:
[docs/PRODUCTION_SAAS_LAUNCH_TRACKER.md](/Users/porschecaa/lingualens/docs/PRODUCTION_SAAS_LAUNCH_TRACKER.md)

Implementation checklist:
[docs/SUPABASE_AUTH_IMPLEMENTATION_CHECKLIST.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_IMPLEMENTATION_CHECKLIST.md)

Staging verifier runbook:
[docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md)

Supabase setup runbook:
[docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md)

## Launch Contract Summary

The production auth path must satisfy all of these conditions together:

- Supabase Auth is the only production-capable auth mode.
- Login is invitation-only email/password with public signup disabled.
- Invitation acceptance creates active membership.
- Mandatory TOTP enrollment follows invitation acceptance.
- `aal1` can reach MFA screens only.
- `aal2` is required before any clinical or admin workflow access.
- One active organization is required per session.
- Multi-org membership is allowed, but organization switching is explicit.
- Membership revocation fails closed on the next request.
- Platform operator access is break-glass only, one case scoped, one hour
  maximum, with category plus free-text reason.

## Current Local Foundation

The repository already contains local or scaffolded foundations for these
behaviors:

| Area | Current evidence |
|---|---|
| Browser auth snapshot parsing | [supabase-browser-auth.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/supabase-browser-auth.ts) derives `signed_out`, `mfa_required`, `org_selection_required`, and `authenticated` states from Supabase-like session claims, auto-resolves a sole active organization, accepts an explicit `organization_id` when no membership list is attached, and now stores the last explicitly chosen organization as a separate hint instead of silently authenticating an ambiguous session. |
| Browser config guard | [supabase-browser-client-config.ts](/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/supabase-browser-client-config.ts) now fails closed unless `NEXT_PUBLIC_SUPABASE_URL` is an HTTPS `*.supabase.co` project URL and `NEXT_PUBLIC_SUPABASE_ANON_KEY` matches an accepted publishable/legacy anon-key shape; [supabase-login-form-client.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/supabase-login-form-client.tsx) surfaces explicit missing/invalid config status instead of attempting browser sign-in bootstrap. |
| Workspace gate | [supabase-workspace-access-gate.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/supabase-workspace-access-gate.tsx) blocks workspace access unless the session reaches `aal2` and an active organization is selected, and now requires an explicit confirmation step before an ambiguous multi-org session can reopen with a hinted organization. |
| MFA scaffold | [supabase-mfa-panel.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/supabase-mfa-panel.tsx) uses the browser-side Supabase MFA APIs for TOTP enrollment and verification. |
| Backend auth fail-closed rules | [test_supabase_auth_scaffold.py](/Users/porschecaa/lingualens/apps/api/tests/test_supabase_auth_scaffold.py) verifies invitation acceptance, MFA requirement, role matrix, membership activity, selected membership consistency, malformed break-glass claim rejection, and break-glass expiry in non-mock auth mode. |
| Local admin lifecycle UX | [settings-workspace-client.tsx](/Users/porschecaa/lingualens/apps/lingualens-app/src/components/settings-workspace-client.tsx) exposes pilot invitation and membership flows against backend scaffolding, clearly labels them as pilot-only, and now states explicitly that they do not send real invitation emails or represent the production Supabase acceptance path. |

This is foundation only. It does not prove that staging or production Supabase
projects are configured or that the real browser session and backend tokens stay
in sync under the launch model.

Local maintained browser auth now also fails closed when required session claims
are absent or malformed and clears the cached access token on claim downgrade,
so a broken or downgraded session cannot keep an old `aal2` Bearer token alive
after the workspace has already dropped to a blocked state.

Local maintained route gating now also proves that post-login routing targets do
not bypass the launch gates: `/today` remains blocked behind MFA or explicit
organization selection when claims require it, `/settings?scope=admin` does the
same for org-admin sessions, and malformed org-admin lifecycle payloads now
degrade to the local backend-unavailable banner instead of crashing the
workspace shell.

Local maintained backend auth also now has current proof that the non-mock
Supabase path accepts only the four launch roles, denies inactive memberships,
denies non-`aal2` sessions when MFA is required, and denies non-accepted
invitation states before route-level authorization can widen access.

Local maintained runtime now also rejects legacy mock-role aliases such as
`admin` and `supervisor`, so both mock and Supabase scaffolds align to the same
four-role launch model.

## Remaining Gaps

### 1. Supabase project and auth configuration

Status: in progress

- [x] Create Supabase organization `LinguaLens`.
- [x] Create `lingualens-staging` in `ap-southeast-1`.
- [x] Create `lingualens-production` in `ap-southeast-1`.
- [ ] Disable public signup in both projects.
- [ ] Enable email/password auth and TOTP MFA in both projects.
- [ ] Record owner contacts and operational owners.
  Project refs, API URLs, issuer URLs, JWKS URLs, dashboard URLs, and
  publishable keys are now recorded in the setup evidence and deployment
  runbooks; named human owners are still pending.

Definition of done:
- Real staging and production projects exist and expose the same auth feature
  class.
- Project refs and backend verifier inputs are recorded from real projects.

### 2. Real claim issuance and synchronization

Status: scaffold exists locally, real provisioning missing

- [ ] Provision the required claims in Supabase tokens:
  - `aal`
  - `app_metadata.organization_id`
  - `app_metadata.organizations`
  - `app_metadata.role`
  - `app_metadata.membership_active`
  - `app_metadata.invitation_status`
  - `app_metadata.break_glass`
- [ ] Define how claim refresh happens after invitation acceptance, membership
  revocation, break-glass grant, and break-glass expiry.
- [ ] Replace local HS256 assumptions with the production signing validation
  path actually used by the Supabase projects.
- [ ] Decide whether staging/production will use shared-secret verification or
  an asymmetric JWKS path, then configure the matching verifier mode.
- [ ] If remote JWKS is used, verify cache TTL, refresh behavior, and failure
  handling for key rotation and temporary JWKS fetch failure.
- Local maintained verifier scaffolding now proves:
  - remote JWKS payloads are cached and reused inside the configured TTL;
  - a cached key miss forces one refresh against the JWKS URL before access is
    denied;
  - refresh still fails closed when the new JWKS payload does not contain the
    signing key;
  - temporary JWKS fetch failure fails closed with an explicit verifier error.
- [ ] Verify remote JWKS refresh-on-missing-key behavior against a real staging
  key rotation scenario or controlled operator simulation.
- [ ] Verify that stale claims fail closed until the browser session is
  refreshed.

Definition of done:
- Backend accepts real staging tokens and rejects tokens that lack the launch
  claims.

### 3. Invitation acceptance and account bootstrap

Status: backend scaffold exists, real delivery flow missing

- [ ] Implement invitation issuance through Supabase-backed delivery, not local
  placeholder acceptance only.
- [x] Ensure invitation acceptance creates or reactivates membership in the
  correct organization.
- [x] Enforce 7-day invitation expiry.
- [x] Handle expired invitations by issuing a new invitation rather than
  reviving the old one.
- [x] Keep membership revocation fail-closed at the next request boundary in
  the maintained backend scaffolding.
  Local maintained route tests now prove an assigned therapist loses case
  access on the very next request after membership revocation.
- [x] Local/backend invitation acceptance now keeps identity unique by email
  across organizations by rejecting attempts to bind one accepted invitation
  email to a different `user_id`.
- [ ] Prove the real Supabase identity path preserves unique email binding
  across organizations.

Definition of done:
- An invited user can accept a real invitation and lands in a valid
  post-acceptance membership state.

### 4. MFA enrollment and login lifecycle

Status: browser-side TOTP panel exists, full production path not verified

- [ ] Connect the real login flow so accepted users reach the MFA gate with an
  `aal1` session.
- [x] Local/frontend scaffold now forces TOTP enrollment when an accepted
  `aal1` session has no verified factor.
- [x] Local/frontend scaffold now refreshes the browser session/access snapshot
  into `aal2` after successful MFA verification.
- [ ] Force MFA challenge on later sign-ins until the real staging session
  becomes `aal2`.
- [ ] Keep password recovery on the Supabase-managed reset path, then re-apply
  membership and MFA gates before app access.
- [x] Local/frontend scaffold now verifies that no app route or shell payload
  opens while the session remains `aal1`.
- [x] Local/frontend scaffold now covers explicit MFA load/enroll/verify error
  states without opening workspace access.
- [ ] Verify that no app route opens while the real staging session remains
  `aal1`.

Definition of done:
- The real browser auth lifecycle consistently transitions `accepted invite ->
  aal1 -> MFA verify -> aal2`.

### 5. Active organization selection and switching

Status: local gate exists with single-org auto-resolution, hint-only ambiguous
selection, and explicit multi-org confirmation; real claims and persistence
path still need staging proof

- [ ] Supply the real active membership list from Supabase claims or a trusted
  backend lookup.
- [x] Local/frontend scaffold now preserves the last explicit organization as a
  hint only, without opening ambiguous sessions automatically.
- [ ] Keep single active memberships from stalling on an unnecessary selection
  screen when the claim set identifies only one valid organization.
- [x] Local/frontend scaffold now requires explicit organization selection
  whenever multiple active memberships exist and no active organization claim
  is present.
- [x] Local/frontend scaffold now keeps org switching explicit and updates the
  backend request context.
- [x] Local/frontend scaffold now verifies exactly one active organization per
  session.

Definition of done:
- Multi-org users can switch deliberately, and ambiguous context never opens the
  workspace by accident.

### 6. Sensitive auth/admin actions and reauthentication

Status: policy decided, production UX not wired

- [ ] Add reauthentication checks only for sensitive security/admin actions.
- [ ] Identify the exact flows that require reauth:
  - invitation management if elevated
  - membership revocation
  - break-glass grant
  - future security-setting changes
- [ ] Keep normal clinical browsing free of unnecessary reauth prompts.

Definition of done:
- Sensitive actions require fresh verification without degrading routine use.

### 7. Revocation and break-glass fail-closed behavior

Status: backend scaffold and tests exist, staging proof missing

- [ ] Verify membership revocation denies the next request using real staging
  claims.
- [x] Local/backend scaffold now requires break-glass category plus free text.
- [ ] Verify break-glass access requires category plus free text in real staging
  claims.
- [x] Local/backend scaffold now enforces one-case break-glass scope and the
  one-hour expiry ceiling.
- [ ] Verify break-glass stays one-case scoped and expires after one hour in
  real staging claims.
- [x] Verify routine case reads still fail for platform operators outside the
  scoped endpoint.
  Local maintained backend tests now cover denied routine platform-operator
  case reads and case creation outside the scoped break-glass path.
- [ ] Verify audit evidence is emitted without raw clinical identifiers or
  content.

Definition of done:
- Staging evidence proves revocation and break-glass both fail closed on the
  next request boundary defined by the launch model.

## Execution Order

1. Create the real Supabase org/projects and disable public signup.
2. Provision real claims and backend token verification.
3. Wire invitation delivery and acceptance into real account bootstrap.
4. Complete MFA enrollment/challenge behavior against the real Supabase
   session.
5. Complete explicit organization selection and switching on the real claim
   path.
6. Run staging tenant-safety verification and attach evidence.

## Required Evidence Before Closing This Tracker

- A completed staging auth-verifier evidence package using
  [SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_STAGING_VERIFIER_RUNBOOK.md)
  and stored under `docs/release_artifacts/auth_verifier/`.
- A completed staging tenant-safety evidence package using
  [STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md).
- A real staging login recording or operator capture that shows:
  - invitation-only sign-in;
  - MFA enrollment or challenge;
  - blocked `aal1` workspace access;
  - explicit organization selection when ambiguous;
  - successful `aal2` workspace access.
- Backend verification results showing real staging tokens satisfy the contract.
- Proof that revocation and break-glass expiry fail closed on the next request.

## Current Closure State

This tracker is open. The repository has local auth foundations, but the real
Supabase rollout work and staging proof are not complete.
