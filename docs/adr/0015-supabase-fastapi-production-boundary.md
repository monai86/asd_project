# Supabase and FastAPI production boundary

## Status

Accepted

## Context

Therapist App v2 is moving from a local research prototype toward a production
SaaS architecture for a small controlled clinic rollout. The product needs
managed authentication, relational clinical records, private media storage,
tenant isolation, auditability, and durable operational controls without moving
clinical policy decisions into browser code.

Earlier Supabase pilot documents allowed more direct browser access for
workflow records. That is no longer the production direction for Therapist App
v2.

## Decision

Supabase is the production platform for:

- PostgreSQL clinical and operational data;
- Supabase Auth identity sessions;
- private Supabase Storage for audio and other clinical media.

The browser may use Supabase Auth and short-lived signed upload or download URLs
only. All clinical reads, writes, workflow transitions, report actions, privacy
operations, and audit-producing actions must go through `apps/api/`.

FastAPI is the authoritative clinical policy boundary. It resolves the actor,
organization, role, care-team membership, consent state, retention state, and
record eligibility before any clinical data is returned or mutated.

PostgreSQL Row Level Security is required as defense in depth. RLS must not be
the only tenant or clinical authorization control, and green RLS tests do not
permit bypassing FastAPI policy checks.

## Consequences

- `apps/api/` remains the canonical backend for Therapist App v2.
- Browser code must not directly query clinical tables for product workflows.
- Storage object paths, signed URL creation, and completion verification must be
  mediated by FastAPI.
- Production mode must fail closed if mock headers, local repositories, local
  storage, mock ASR, or demo defaults are enabled.
- Supabase service-role credentials must stay server-side and come from a
  managed secret store.

## Supersedes

This production boundary supersedes the direct clinical workflow access implied
by earlier pilot ADRs where it conflicts. Historical ADRs remain useful context
for why Supabase was selected.
