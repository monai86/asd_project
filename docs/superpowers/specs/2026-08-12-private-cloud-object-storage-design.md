# Private Cloud Object Storage & Presigned URLs Design Document

- **Date:** 2026-08-12
- **Milestone:** Phase 2 Pilot Hardening — Supabase Private Storage & Presigned URLs
- **Target Surfaces:** `apps/api/`, `docs/`, `scripts/`
- **Status:** Approved Design Spec

---

## 1. Overview & Goal

LinguaLens requires private, secure audio file storage for sensitive child session recordings. Public access to audio files must be completely disabled.

This design specifies the implementation and verification of **Supabase Private Object Storage** (`supabase_private` mode) using presigned upload/playback URLs, SHA-256 integrity verification, bounded download streams, and automated consent cleanup reconcilers.

---

## 2. Storage Architecture & Signed URL Flow

### 2.1 Storage Bucket Configuration
- Bucket Name: `private-audio`
- Privacy: `public = false`
- Allowed MIME Types: `audio/wav`, `audio/x-wav`, `audio/mpeg`, `audio/mp3`
- Size Limit: 100 MB max file size, 15 minutes max duration

### 2.2 Presigned Upload Intent & Verification
1. **Upload Intent:** Client calls `POST /api/v1/sessions/{session_id}/audio/upload-intent`.
   - Backend verifies active consent (`consent_status == "granted"`) and care team authorization.
   - Backend calls `SupabasePrivateStorageAdapter.create_signed_upload_intent()` generating a presigned URL expiring in 15 minutes.
   - Returns `SignedUploadIntent` schema containing `upload_url`, `object_key`, `expires_at`, and `expected_checksum_sha256`.
2. **Direct Upload Execution:** Client uploads file directly to Supabase Storage via `PUT` with presigned upload token.
3. **Ownership Verification:** Client posts `AudioUploadOwnershipReceipt` to `POST /api/v1/sessions/{session_id}/audio/verify-upload`.
   - Backend verifies file presence in storage, checks byte size, checks SHA-256 checksum, and links object key to `audio_file_metadata`.

---

## 3. Presigned Playback Stream & Consent Cleanup

### 3.1 Presigned Playback URL
- When playing audio in Therapist Workspace, client requests `GET /api/v1/sessions/{session_id}/audio/playback-url`.
- Backend checks active consent and care team membership, generating a short-lived presigned URL (`create_signed_url`) expiring in 5 minutes.
- Public URLs are never logged, stored, or exposed.

### 3.2 Bounded Download Stream for ASR Processing
- Local ASR processing engine downloads streams with strict byte caps (default 100 MB) via `SupabasePrivateStorageAdapter.download_stream()`.
- Exceeding size limit aborts the stream with `StorageProcessingError("storage_size_limit_exceeded")`.

### 3.3 Consent Withdrawal & Storage Remediation
- When `withdraw_consent()` is triggered, backend calls `adapter.remove([object_key])` for both staging and normalized assets.
- If deletion fails, `upload_cleanup_remediation` tracks retries until cleanup succeeds, guaranteeing total removal of raw audio files.

---

## 4. Verification & Testing Strategy

- **Adapter Unit Tests:** `pytest apps/api/tests/test_audio_storage_service.py` verifying upload/download signed URLs and bounded streaming.
- **Backend Identity Tests:** `pytest apps/api/tests/test_storage_backend_identity.py` verifying SHA-256 storage provenance.
- **Cleanup Reconciler Tests:** `pytest apps/api/tests/test_upload_cleanup_reconciler.py` verifying retry and escalation logic on transient storage failures.
- **Full Release Gate:** `bash scripts/check_v170_speech_pipeline.sh`
