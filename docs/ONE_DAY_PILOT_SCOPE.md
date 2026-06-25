# One-Day Pilot Scope

Date: 2026-06-25

This scope replaces the full production SaaS roadmap for the current workday only. The target is a production-like local or staging pilot that can exercise the Therapist App v2 workflow without external vendor, legal, or clinic launch dependencies.

## Goal

Build a usable pilot vertical slice in `apps/api/` and the existing Therapist App v2 surface. The pilot must keep the production path open, but it is not production-ready and must not be represented as clinically validated.

## In Scope Today

- Local/SQL organization scaffold for one pilot organization and demo users.
- Backend tenant guard for organization ID, role, and care-team access.
- Tenant-scoped clinical records for cases, sessions, transcripts, and reports.
- Production-mode guard that rejects mock auth and local/demo fallbacks.
- Local private-storage adapter that issues short-lived upload intents and avoids committing audio bytes.
- Local pilot audio flow: upload intent, complete upload metadata, queue/process job, produce review-required draft transcript.
- Existing immutable report sign-off/export behavior remains enforced.
- Runbook for local pilot setup, limitations, and production gaps.

## Out of Scope Today

- Supabase Auth, MFA, invitations, and real user lifecycle.
- PostgreSQL RLS policy implementation.
- Supabase Storage integration beyond an interface-compatible placeholder.
- Celery/Redis durable workers and transactional outbox.
- Vendor ASR approval, Thai/English benchmark approval, or clinical validation.
- Billing, FHIR, native app shells, custom clinic integrations, and public launch automation.

## Pilot Safety Constraints

- No real child names, transcripts, audio bytes, storage keys, raw filenames with identifiers, secrets, or clinical content are committed.
- All clinical workflow reads and writes stay in `apps/api/`.
- `src/therapist_backend/` and `src/clinical_workflow/` remain legacy/research surfaces only.
- Mock/demo auth is allowed only in local mock mode. Non-mock runtime must fail closed unless production-capable auth and managed dependencies are configured.

## Definition of Done

- Backend API tests pass.
- Critical boundary tests cover tenant isolation, production auth guard, upload intent metadata flow, report immutability/export, and consent withdrawal safety.
- `docs/ONE_DAY_PILOT_RUNBOOK.md` explains how to run the pilot, what works today, and what remains non-production.

## Post-Pilot Phase 1 Update

After the one-day pilot was completed, Phase 1 production-roadmap work added
SQL tenant/RLS foundation beyond the original one-day scope: additional
organization, membership, care-team, retention, consent, notification, and job
attempt tables; organization-scoped clinical records; broader backend tenant
guards; production auth fail-close behavior for non-mock auth mode; and a
PostgreSQL RLS migration scaffold. This improves the production path without
changing the pilot claim: the system is still not full production SaaS.
