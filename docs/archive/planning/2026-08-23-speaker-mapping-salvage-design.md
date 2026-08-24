# Archived: Therapist-Confirmed Speaker Mapping Salvage Design

**Date:** 2026-08-23

**Status:** Approved design

**Target branch:** `codex/salvage-speaker-mapping`

**Canonical product surfaces:** `apps/lingualens-app/` and `apps/api/`

## Context

The preserved `codex/v1.7.0-speech-to-chat` branch contains a broad speaker-
mapping implementation, but the branch diverges substantially from the current
product and must not be merged or cherry-picked as a unit. This design salvages
the safety behavior, not the old implementation. New code starts from current
`main`, follows the maintained API and web-app architecture, and is developed
with tests first.

LinguaLens remains a research and education prototype that supports therapist
review. Speaker mapping is an integrity gate for source attribution; it is not
an automated clinical interpretation or diagnostic feature.

## Goal

Add a minimal end-to-end workflow in which a therapist explicitly maps
temporary ASR speaker identifiers to canonical CHAT speaker codes before
role-dependent QA, attestation, CHAT export, or feature extraction can proceed.
The mapping must be version-bound, auditable, tenant-safe, consent-gated, and
persisted independently from the transcript.

## Non-Goals

- Do not add or change ASR or diarization providers.
- Do not infer child, therapist, or other roles automatically.
- Do not support merging or splitting speaker clusters in this increment.
- Do not change the Desktop GUI or Terminal TUI production code.
- Do not add Redis, Celery, a new worker, or a new product surface.
- Do not revive the v1.7 release line or change the project version.
- Do not add diagnostic claims, age norms, or Thai clinical-validation claims.

## Activation Boundary

`requires_speaker_mapping(transcript)` returns true only when both conditions
hold:

1. the transcript source starts with `asr_draft:` (the existing
   `mock_asr_draft:` path does not qualify); and
2. at least one utterance has a non-empty `temporary_speaker_id`.

Manual transcripts, CHAT imports, and ASR transcripts that already contain only
canonical speaker codes bypass the gate. Existing records remain valid because
the new utterance provenance fields are optional and the new persistence table
is additive.

## Domain Model

### Utterance provenance

The maintained `Utterance` model gains two optional fields:

- `temporary_speaker_id`: the stable identifier used to group utterances from
  one ASR/diarization speaker cluster;
- `source_speaker_label`: the provider's original label, retained as provenance.

Confirmation changes the canonical `speaker` value but preserves both fields.

### Speaker mapping record

`SpeakerMapping` is a separate versioned record with:

- `mapping_id`;
- `organization_id`;
- `transcript_id`;
- `source_transcript_version`;
- `applied_transcript_version`, nullable until confirmation;
- `mapping_version` for optimistic concurrency;
- persisted `status`: `draft` or `confirmed`;
- `entries`;
- `confirmed_by_user_id`, `confirmed_by_role`, and `confirmed_at`;
- `created_at` and `updated_at`.

A confirmed record is immutable. A mapping is considered stale when its
`applied_transcript_version` does not equal the current transcript version. The
old record remains available for audit evidence; a new draft is created for the
current transcript version.

API responses additionally expose an effective workflow status of
`not_required`, `draft`, `confirmed`, or `stale`; `stale` is derived from the
current transcript version and is never written over immutable confirmation
evidence.

### Mapping entries

Each `SpeakerMappingEntry` contains:

- `temporary_speaker_id`;
- `confirmed_chat_code`: `CHI`, `THER`, or `OTH` (`THER` follows the maintained
  API's existing therapist-speaker convention);
- `participant_role`: `target_child`, `therapist`, or `other`;
- `affected_utterance_ids`;
- `reviewed_utterance_ids`;
- server-derived `source_speaker_label` and provider metadata.

The backend ignores client-supplied provider labels or metadata and reconstructs
them from the transcript. Confirmation requires exactly one `CHI`, unique
canonical codes, an entry for every temporary speaker ID, and exact reviewed
coverage of every affected utterance. More than three distinct temporary
speakers cannot be confirmed in this minimal increment because silent role
merging is forbidden.

## Persistence and Repository Boundary

Alembic revision `0014` adds a `speaker_mappings` table without modifying or
deleting existing transcript data. The table stores scalar identity/version
columns and validated mapping entries as JSON. It includes organization and
transcript indexes and a uniqueness constraint that prevents duplicate mapping
versions for one transcript.

The repository contract supports:

- creating or replacing a current-version draft with optimistic concurrency;
- reading the latest mapping for a transcript;
- atomically confirming a draft while applying the mapped transcript update;
- preserving prior confirmed records.

The in-memory/JSON and SQL repositories must expose equivalent behavior. SQL
confirmation, transcript update, downstream invalidation, mapping persistence,
and audit persistence occur in one transaction.

## API

The maintained transcript router adds:

- `GET /transcripts/{transcript_id}/speaker-mapping`;
- `PUT /transcripts/{transcript_id}/speaker-mapping`;
- `POST /transcripts/{transcript_id}/speaker-mapping/confirm`.

All three routes reuse current transcript authorization, organization scoping,
and active-consent checks. Draft mutation requires a user permitted to mutate
clinical records. Confirmation additionally requires the therapist role.

The GET response states whether mapping is required and returns either the
current draft, the current confirmed mapping, or a stale prior mapping with a
structured issue. When mapping is required and no record exists, the service
returns an unsaved server-derived draft; reading alone does not write data.

PUT accepts expected transcript and mapping versions plus therapist-editable
entry fields. POST accepts expected transcript and mapping versions only. The
authenticated user identity is always the confirmation identity.

## Confirmation Transaction

Confirmation performs these operations atomically:

1. re-read and authorize the current transcript and draft;
2. verify transcript and mapping versions;
3. verify exactly one target child, unique codes, complete speaker coverage,
   and complete utterance review evidence;
4. apply canonical speaker codes to a cloned utterance list while retaining raw
   provider provenance;
5. regenerate reviewed transcript source text through the maintained transcript
   serializer;
6. create a new transcript version and invoke existing downstream-staleness
   behavior for QA, attestation, findings, and reports;
7. persist an immutable confirmed mapping bound to the new transcript version;
8. write a privacy-safe audit event containing identifiers, versions, actor,
   action, outcome, and correlation metadata but no transcript content.

If any step fails, neither the transcript nor the mapping is changed.

## Workflow Gates

When mapping is required, these actions fail closed unless a confirmed mapping
matches the current transcript version:

- transcript QA;
- transcript attestation;
- CHAT export;
- role-dependent feature extraction.

The gate is centralized in the speaker-mapping service and reused by each
workflow service. It emits stable error codes:

- `SPEAKER_MAPPING_REQUIRED`;
- `SPEAKER_MAPPING_INCOMPLETE`;
- `SPEAKER_MAPPING_TARGET_REQUIRED`;
- `SPEAKER_MAPPING_DUPLICATE_CODE`;
- `SPEAKER_MAPPING_VERSION_CONFLICT`;
- `SPEAKER_MAPPING_STALE`.

Errors contain actionable generic guidance and never echo transcript text or
provider payloads.

## Web Application

The Session Transcript workspace conditionally loads mapping state only after a
loaded transcript indicates temporary speaker IDs. Unaffected workflows do not
mount mapping requests or effects.

The Speaker Mapping panel appears before QA and attestation controls. For each
temporary speaker it shows the provider label, affected utterances, canonical
code selector, role selector, and a review control for every affected
utterance. The panel does not infer or preselect a clinical role. Draft must be
saved before confirmation, and confirmation remains disabled until the locally
visible mapping is complete and matches the saved mapping version.

Stale or version-conflict responses disable confirmation and instruct the user
to reload the current transcript. All controls have accessible labels, keyboard
operation, visible focus states, and at least 44-pixel touch targets.

## GUI and TUI Compatibility

Desktop GUI and Terminal TUI production code are out of scope. Their manual and
local-audio workflows currently use canonical speaker codes and therefore do
not activate the mapping gate. Optional response fields remain backward
compatible.

The existing GUI and TUI test suites are mandatory regression gates. Additional
API compatibility tests prove that manual, CHAT-imported, and canonical-ASR
transcripts continue through QA and attestation without a mapping request.

## Privacy and Clinical Safety

- Mapping is a therapist-reviewed source-integrity control, not a diagnosis.
- Tests use synthetic, non-identifying utterances and system-generated IDs.
- Logs and audit events contain no transcript text, raw provider payload,
  filename, audio content, or direct identifier.
- Existing consent, organization, care-team, and role checks remain in force.
- Provider metadata is preserved privately and never trusted from the client.

## Test Strategy and Acceptance Criteria

Backend tests cover activation, bypass compatibility, server-derived
provenance, validation rules, optimistic concurrency, tenant/consent/role
authorization, atomic confirmation, transcript versioning, staleness, workflow
gates, audit safety, JSON behavior, and SQL persistence.

Frontend tests cover conditional loading, draft editing, save-before-confirm,
complete segment review, stale and conflict states, accessible controls, and
the absence of mapping effects for unaffected transcripts. A browser E2E path
covers temporary ASR speakers through mapping confirmation, QA, and attestation.

Completion requires:

- focused backend and frontend tests;
- all Desktop GUI and Terminal TUI tests;
- API migration smoke through revision `0014`;
- frontend typecheck, production build, and UI audit;
- `bash scripts/check_project.sh`;
- all GitHub CI checks.

## Documentation and Rollout

`README.md` will describe the mapping step only in the ASR review workflow.
`CHANGELOG.md` will record the new behavior. `docs/PROJECT_SOURCE_OF_TRUTH.md`
will state that temporary ASR speaker identifiers require a current
therapist-confirmed mapping, while canonical/manual/CHAT workflows remain
compatible.

The feature ships through a small pull request from current `main`. The donor
branch remains unchanged and is not merged. No production deployment or branch
cleanup is part of this design.
