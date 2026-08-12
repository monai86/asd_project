# Browser Live Audio Recording Design Document

- **Date:** 2026-08-12
- **Milestone:** Phase 4 Pilot Hardening — Browser Live Audio Recording & Pipeline Integration
- **Target Surfaces:** `apps/lingualens-app/`, `docs/`, `scripts/`
- **Status:** Approved Design Spec

---

## 1. Overview & Goal

LinguaLens requires a seamless browser-based audio recording capability for therapists conducting live sessions. Therapists need the ability to record audio directly in the browser, preview the playback, and instantly submit the recorded audio into the verified LinguaLens ASR Pipeline (`Audio Intake` -> `Local Faster-Whisper` -> `Speaker Mapping` -> `CHAT Export`).

---

## 2. Component Architecture & Direct Pipeline Bridge

### 2.1 Feature Gate Configuration
- `browserRecordingEnabled` is active when `NEXT_PUBLIC_BROWSER_RECORDING_EXPERIMENTAL="true"` or when running in local development mode with MediaRecorder support.

### 2.2 UI & Controls (`BrowserAudioRecorder`)
- **Recorder Actions:** `Start recording`, `Pause recording`, `Resume recording`, `Stop recording`, and `Clear recording`.
- **Feedback Elements:**
  - Real-time timer formatted as `HH:MM:SS`.
  - Live Web Audio API (`AudioContext` / `AnalyserNode`) waveform visualization.
  - Audio playback preview (`<audio src={audioUrl}>`).
- **Direct Pipeline Bridge Button:**
  - Upon stopping recording, displays **"ส่งวิเคราะห์ด้วย ASR Pipeline"** (Submit to ASR Pipeline).
  - Clicking the button converts the recorded `Blob` (`audio/webm` or `audio/wav`) into a `File` object (`browser-recording-[timestamp].webm`).
  - Passes the file to `handleAudioFileSelected(file)` and triggers `handleAudioFileUpload()` to initiate backend ASR intake and job processing.

---

## 3. Privacy, Consent Gate & Resource Management

### 3.1 Consent Gate
- Browser recording controls remain disabled until caregiver/parental consent is verified (`caseConsent === "granted"`).

### 3.2 Unsaved Recording Warning & Privacy Notice
- If the therapist attempts to navigate away with an unsaved recording, a warning notice is displayed to prevent accidental loss of clinical audio.

### 3.3 Memory Cleanup
- Immediately revokes `URL.createObjectURL` and clears in-memory blob references when the recording is reset or after successful pipeline submission.

---

## 4. Verification & Testing Strategy

- **Frontend Unit Tests:** `vitest run src/__tests__/browser-audio-recorder.test.tsx` verifying MediaRecorder state transitions, playback URL creation, and direct pipeline submit action.
- **Intake Flow Integration Tests:** `vitest run src/__tests__/audio-file-upload-panel.test.tsx`.
- **Full Release Gate Script:** `bash scripts/check_v170_speech_pipeline.sh`
