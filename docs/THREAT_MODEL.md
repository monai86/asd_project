# Therapist App v2 Threat Model

This threat model covers the production SaaS direction for Therapist App v2. It
does not claim the current local prototype is production-ready.

## Scope

In scope:

- `apps/therapist-app-v2/` browser/PWA frontend;
- `apps/api/` FastAPI policy boundary;
- Supabase Auth, Postgres, and private Storage;
- durable workers, Redis/job queues, ASR providers, report export, audit,
  observability, notification, and privacy operations.

Out of scope:

- legacy research compatibility APIs under `src/therapist_backend/`;
- research-only model training pipelines;
- removed Vite/Capacitor and demo frontend surfaces.

## Assets

| Asset | Sensitivity | Notes |
|---|---:|---|
| Child direct identifiers | Restricted | Names, surnames, dates of birth, contact details, guardian identifiers. |
| Transcript text | Restricted | Clinical speech-language content and review notes. |
| Audio and video files | Restricted | Raw clinical media must stay in private encrypted storage. |
| Report snapshots | Restricted | Signed clinical decision-support reports and export artifacts. |
| Audit evidence | Confidential | Must be preserved and protected from tampering or silent deletion. |
| Auth tokens and sessions | Confidential | Supabase Auth tokens, refresh tokens, invitation state, MFA state. |
| Storage keys and signed URLs | Confidential | Signed URLs must be short-lived and scoped. Permanent keys are server-only. |
| Provider metadata | Confidential | ASR/AI provider, model, version, region, request hashes, and warning metadata. |
| Operational logs and telemetry | Internal | Must contain operational metadata only, never clinical content. |

## Actors

| Actor | Expected Access |
|---|---|
| Clinician | Assigned cases and workflow actions within authorized organizations. |
| Clinical supervisor | Assigned supervision scope and approved review actions. |
| Organization admin | Membership and organization settings; clinical content only when explicitly authorized. |
| Platform operator | Operational support without clinical content by default. |
| Malicious tenant user | Attempts IDOR, privilege escalation, or cross-tenant data access. |
| Compromised browser | Attempts token replay, local data exfiltration, or unauthorized upload completion. |
| Compromised worker | Attempts fabricated ASR, duplicate writes, or unauthorized storage reads. |
| External provider | Receives approved, minimized payloads only under provider and regional controls. |

## Primary Threats And Mitigations

| Threat | Example | Mitigations |
|---|---|---|
| IDOR | Guessing another case, report, transcript, or upload ID. | FastAPI resolves actor, organization, role, care-team membership, consent, and record ownership on every clinical request; generic 403/404 responses. |
| Cross-tenant data exposure | Query returns records from another organization. | Organization-scoped queries, care-team checks, SQL tenant indexes, RLS defense-in-depth, tenant isolation tests, audit events. |
| Consent bypass | Upload or ASR job starts after consent is missing or revoked. | Consent gates before upload intent, completion, enqueue, worker claim, and provider call. |
| Fabricated ASR | Worker creates transcript not tied to verified media/provider output. | Durable job state, provider provenance, checksum/duration verification, transcript review and attestation before downstream use. |
| Audit loss or tampering | Mutation succeeds but audit event is missing. | Same-transaction audit writes for mutations, append-only audit semantics, backup/PITR and restore drills. |
| Token replay | Stolen browser token or invitation link is reused. | Supabase Auth, MFA for real users, short invitation expiry, revoked membership checks, short-lived signed URLs. |
| Malicious upload | Oversized, wrong MIME, or unsafe object is accepted. | Upload intent constraints, private storage, completion verification for MIME/size/checksum/duration, malware scanning gate when enabled. |
| Prompt/provider leakage | Direct identifiers or clinical content sent to AI provider outside approval. | Organization-level opt-in, identifier sanitization, provider allowlist, regional controls, input hash provenance, rejectable drafts only. |
| Storage key exposure | Permanent key leaks to browser or logs. | Server-side service-role credentials only, managed secret store, URL sanitization in logs, short-lived signed URLs. |
| Clinical content in operations | Logs, notifications, incidents, or telemetry include restricted content. | Safety validators for logs, notifications, audit events, and observability; generic operational messages. |

## Fail-Closed Requirements

Production startup must fail closed when any of the following are configured:

- mock auth headers for real users;
- JSON, memory, local storage, or mock job queues as production backends;
- mock ASR or mock AI providers;
- wildcard or empty production CORS origins;
- missing managed secret store, credential rotation runbook, observability
  provider, or critical alert route.

## Open Production Gates

- External security review with no unresolved critical/high findings.
- Supabase Auth/MFA and invitation-only onboarding in staging and production.
- RLS tests as defense-in-depth alongside FastAPI authorization tests.
- Restore, incident, deletion, and key rotation drills with evidence.
