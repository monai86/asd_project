# Supabase PostgreSQL Integration Design Document

- **Date:** 2026-08-12
- **Milestone:** Phase 1 Pilot Hardening — Managed Supabase PostgreSQL Integration
- **Target Surfaces:** `apps/api/`, `docs/`, `scripts/`
- **Status:** Approved Design Spec

---

## 1. Overview & Context

LinguaLens relies on an auditable, versioned clinical data pipeline (cases, sessions, transcripts, speaker mappings, QA limitations, attestations, CHAT exports, feature projections, reports, audit logs).

Currently, local developer workflows use JSON or Memory repositories (`LINGUALENS_REPOSITORY_MODE=json`). While 15 Alembic SQL migrations (`0001` through `0015`) and `SQLAlchemyRepository` exist in `apps/api/`, full integration with a managed **Supabase PostgreSQL** database is required for production pilot readiness, Row Level Security (RLS) enforcement, multi-tenant isolation, and reliable transactions.

---

## 2. Architecture & Data Model

### 2.1 Repository Mode Control
- Controlled via `LINGUALENS_REPOSITORY_MODE=sql`.
- Connection URL supplied via `LINGUALENS_DATABASE_URL` (e.g., `postgresql+psycopg://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres` or Transaction Pooler port 6543).

### 2.2 Core Entities & Tables
1. `child_cases`: Child metadata, consent status (`VERIFIED`, `WITHDRAWN`), care team assignments (`care_team_user_ids`).
2. `therapy_sessions`: Clinical session dates, types, links to current transcript/feature set/report/findings.
3. `audio_file_metadata` & `normalized_audio_assets`: Audio intake records, checksums (SHA-256), duration, and normalization provenance.
4. `transcripts`: Full utterance transcripts, versions, QA status, sources (`asr_draft:local_faster_whisper`, `manual`).
5. `reviewed_speaker_mappings`: Confirmed mapping between temporary speaker codes and CHAT roles (`CHI`, `THE`).
6. `limitation_acknowledgments` & `transcript_attestations`: Version-bound QA limitation acknowledgments and typed therapist attestations.
7. `chat_exports` & `findings_projections`: Canonical CHAT `.cha` exports, SHA-256 checksums, and 12 Thai-aware descriptive feature metrics.
8. `reports`: Editable/signed report drafts, SHA-256 signed snapshot hashes, sign-off metadata.
9. `audit_events` & `privacy_operations`: Immutable audit logs without raw clinical identifiers.

---

## 3. Security, Isolation & Row Level Security (RLS)

- **Organization Scoping:** Every table contains `organization_id`. RLS policies in `0009_add_tenant_rls_policies.py` enforce tenant boundaries using `auth.jwt() -> organization_id`.
- **Care Team Access:** Access to clinical cases and session data requires therapist membership in `care_team_user_ids` or assignment as `therapist_id`.
- **Consent Fencing:** Cases with `consent_status == "WITHDRAWN"` trigger active consent fences that block reads, updates, exports, and feature projections.
- **Log Privacy:** Audit events and structured HTTP logs omit raw child names, transcript text, audio bytes, and private storage keys.

---

## 4. Migration & Environment Setup

1. **Alembic Migration Engine:** [`apps/api/app/db/migrations_runner.py`](file:///Users/porschecaa/lingualens/.worktrees/v1.7.0-speech-to-chat/apps/api/app/db/migrations_runner.py) automatically validates and applies migrations `0001` to `0015` on API startup.
2. **Environment Configuration Helper:** [`scripts/create_supabase_runtime_env_snippets.sh`](file:///Users/porschecaa/lingualens/.worktrees/v1.7.0-speech-to-chat/scripts/create_supabase_runtime_env_snippets.sh) generates staging and production `.env` templates containing JWKS, RLS, and PostgreSQL settings.

---

## 5. Verification & Testing Strategy

- **Migration Verification:** Run `python scripts/check_api_migrations.py` to confirm Alembic head.
- **SQL Repository Unit & Transaction Tests:** Run `pytest apps/api/tests/test_sql_repository_transactions.py` under `LINGUALENS_REPOSITORY_MODE=sql`.
- **End-to-End Pipeline Check:** Run `bash scripts/check_v170_speech_pipeline.sh` to ensure all 413 API unit tests and 16 frontend unit tests pass cleanly under SQL mode.
