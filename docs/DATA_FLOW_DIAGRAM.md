# lingualens Data Flow Diagram

This document describes the intended production data flows. It is a textual DFD
for implementation and review; it is not evidence that every flow is complete.

## Components

| Component | Responsibility |
|---|---|
| Browser/PWA | Auth session, therapist UI, direct signed upload/download only. |
| FastAPI API | Clinical policy boundary, workflow transitions, audit, signed URL issuance. |
| Supabase Auth | User identity, sessions, MFA, invitation-backed onboarding. |
| Supabase Postgres | Clinical records, organizations, membership, reports, jobs, audit, privacy operations. |
| Supabase private Storage | Audio/media objects and export artifacts under scoped private paths. |
| Redis/job queue | Durable processing leases, retries, and worker coordination. |
| Worker | Media verification, ASR requests, feature extraction, and controlled derived writes. |
| ASR provider | Approved speech-to-text service with region/model provenance. |
| Observability provider | Privacy-safe operational telemetry and critical alerts. |

## 1. Browser Auth Flow

```text
User browser
  -> Supabase Auth: invitation accept, login, MFA
  <- Supabase Auth: user session token
User browser
  -> FastAPI: request with bearer token and selected organization context
FastAPI
  -> Supabase Auth/JWKS: validate token and claims
  -> Postgres: resolve profile, membership, role, care-team authorization
  <- FastAPI: clinical response or generic denial
```

The browser may propose organization context, but FastAPI must resolve and
enforce authorization server-side.

## 2. Upload Intent Flow

```text
Browser
  -> FastAPI: create upload intent for case/session
FastAPI
  -> Postgres: verify organization, care-team membership, active consent,
     allowed media type, retention policy
  -> Supabase Storage: create short-lived signed upload URL for scoped path
  -> Postgres: persist upload intent and audit event
  <- Browser: signed upload URL and required constraints
```

No audio bytes are sent to FastAPI during intent creation.

## 3. Direct Browser-To-Private-Storage Upload

```text
Browser
  -> Supabase private Storage: PUT media bytes to signed URL
Supabase Storage
  -> Browser: upload result
```

The signed URL must be short-lived, object-path scoped, and bound to the upload
intent constraints. Permanent storage credentials never leave the server.

## 4. Completion Verification Flow

```text
Browser
  -> FastAPI: complete upload with object reference, checksum, MIME, size,
     duration metadata
FastAPI
  -> Postgres: verify intent, consent, membership, expiry, and idempotency
  -> Supabase Storage: verify object metadata
  -> Postgres: mark upload complete, create processing job, create outbox event,
     write audit event in the same transaction
  <- Browser: accepted job state
```

Completion fails closed when consent is revoked, the URL expired, metadata does
not match the intent, or object verification fails.

## 5. Worker And ASR Flow

```text
Worker
  -> Postgres/queue: claim outbox event with lease
  -> Postgres: re-check consent, organization, job state, retry budget
  -> Supabase Storage: create server-side read access for scoped media
  -> ASR provider: submit media or provider-supported reference
  <- ASR provider: transcript draft and metadata
  -> Postgres: write transcript draft, provider provenance, job attempt,
     warnings, audit event
```

Workers must be idempotent. Retries must not create duplicate transcripts or
erase prior audit evidence.

## 6. Transcript Review And Attestation

```text
Browser
  -> FastAPI: fetch transcript draft
FastAPI
  -> Postgres: authorize by organization, role, care-team membership
Browser
  -> FastAPI: submit reviewed transcript lines and attestation
FastAPI
  -> Postgres: persist reviewed version and audit event
```

Feature extraction and report drafting must use reviewed and attested
transcripts, not raw ASR output.

## 7. Feature Extraction

```text
FastAPI or Worker
  -> Postgres: load attested transcript and feature configuration
  -> Feature extractor: compute transparent review cues
  -> Postgres: persist derived feature set with version/provenance and audit
```

Feature outputs are review support only and must not be presented as diagnosis.

## 8. Report Finalization And Export

```text
Browser
  -> FastAPI: edit draft report
FastAPI
  -> Postgres: save draft revision with concurrency token
Browser
  -> FastAPI: sign off report
FastAPI
  -> Postgres: create immutable signed snapshot, signer, timestamp, version,
     SHA-256 hash, audit event
Browser
  -> FastAPI: export signed report
FastAPI
  -> Storage/Postgres: create export artifact, timestamp, hash, audit event
  <- Browser: short-lived signed download URL or export response
```

Editing after sign-off creates a new draft revision. It must not silently mutate
the signed snapshot.

## 9. Audit And Observability Flow

```text
FastAPI/Worker
  -> Audit validator: actor, action, target, outcome, timestamp, correlation ID,
     no clinical content
  -> Postgres: append audit event
  -> Observability validator: operational-only metadata
  -> Observability provider: metric/event/alert
```

Logs, telemetry, notifications, and incident records must not include child
identifiers, transcript text, audio content, storage keys, raw filenames, report
excerpts, or clinical content.
