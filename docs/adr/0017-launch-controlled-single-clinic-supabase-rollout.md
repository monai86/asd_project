# Launch the first production rollout as a controlled single-clinic Supabase deployment

## Status

Accepted

## Context

lingualens is moving from a local research and pilot prototype toward a real
production SaaS launch. The product already has local foundations for
organization membership, care-team assignment, report sign-off, invitation
acceptance, MFA gating, break-glass scaffolding, and tenant-aware backend
guards, but the first real launch still has substantial external dependency and
tenant-safety risk.

The launch must preserve the production boundary already accepted in
[0015-supabase-fastapi-production-boundary](/Users/porschecaa/lingualens/docs/adr/0015-supabase-fastapi-production-boundary.md)
and the responsive web/PWA-only product surface accepted in
[0016-responsive-web-pwa-only](/Users/porschecaa/lingualens/docs/adr/0016-responsive-web-pwa-only.md).

The open question is not whether lingualens will eventually support multiple
clinic tenants. The hard-to-reverse decision is how the first real rollout
should be constrained so the team can validate security, privacy, and clinical
workflow controls without taking on unnecessary launch scope.

## Decision

The first production rollout will be a controlled clinic rollout for one clinic
organization in Thailand.

The first launch will use:

- Supabase organization `LinguaLens`;
- one staging and one production Supabase project in `ap-southeast-1`;
- Supabase Auth, Postgres, and private Storage;
- `apps/api/` as the required clinical policy boundary;
- `apps/lingualens-app/` as the only maintained product frontend.

The first launch access model is frozen as follows:

- public signup is off;
- identity is unique email;
- onboarding is invitation-only;
- membership is created on invitation acceptance;
- email/password plus required TOTP MFA is the production login path;
- post-acceptance MFA enrollment is mandatory;
- `aal2` is required before any app access;
- `aal1` may reach MFA screens only;
- recovery uses Supabase-managed reset but still re-enters normal membership and
  MFA gates;
- one active organization is attached to each session;
- multi-organization membership is allowed, but organization switching is
  explicit.

The first launch authorization model is frozen as follows:

- launch clinic roles are `therapist`, `clinical_supervisor`, and `org_admin`;
- `platform_operator` is separate and break-glass only;
- therapist access is limited to assigned cases only;
- clinical supervisor access is all cases in the active organization;
- org admin has no clinical access by default and only assignment-safe metadata
  access by default;
- org admin clinical access requires an explicit additional clinical grant
  through care-team assignment;
- assignment managers are `clinical_supervisor` and `org_admin`;
- report sign-off belongs to the primary assigned therapist only;
- every case assignment must include a primary assigned therapist;
- removing the primary therapist blocks sign-off until reassignment;
- supervisor sign-off is not a routine or launch exception path.

The first launch operational and safety model is frozen as follows:

- break-glass access is one case only;
- break-glass expires after one hour and fails closed on the next request;
- break-glass reason requires category plus free text;
- staging and production use Supabase private Storage only;
- storage object paths use opaque generated keys only;
- signed upload URLs expire after fifteen minutes;
- uploads are untrusted until backend completion verification succeeds;
- failed uploads require a new upload intent;
- processing starts only from explicit user action;
- one active processing job is allowed per audio artifact;
- reprocess creates a new job on the same audio artifact;
- therapist-reviewed transcript is the only transcript authority;
- transcript edits stale downstream outputs immediately;
- AI review is organization-level opt-in and default off;
- provider fallbacks must return explicit unavailable states and never mock or
  fabricate outputs in production;
- deletion is blocked by legal hold;
- sign-off evidence is retained per policy;
- notifications and telemetry remain operational-only;
- audit shape is actor, action, target, outcome, timestamp, and correlation ID
  with no raw clinical identifiers or content;
- same architecture class is required between staging and production;
- backup restore must pass before launch;
- unresolved high or critical security findings block launch;
- rollout freezes immediately on critical incident.

The first launch governance model is frozen as follows:

- launch country allowlist is Thailand only;
- launch scope is one clinic tenant first;
- billing is out of scope for first launch;
- production mock mode is forbidden;
- promotion from staging requires real-claim tenant-safety verification;
- go-live approval requires engineering/product plus legal/privacy.

## Consequences

- The team optimizes for a safe single-clinic production proof, not a
  self-serve multi-clinic rollout.
- Multi-org membership support remains necessary in the data and auth model, but
  the first launch still validates only one real clinic tenant in production.
- Staging must prove real-claim tenant safety before any production promotion.
- Production work that does not help the controlled rollout can be deferred,
  including billing and non-essential reference outputs.
- Any implementation that depends on public signup, organization-free sessions,
  routine platform-operator access, mock production fallbacks, or implicit
  tenant switching conflicts with this ADR.

## Supersedes

This ADR narrows the first production launch shape implied by earlier roadmap
documents and pilot planning notes where they were broader or less explicit.
