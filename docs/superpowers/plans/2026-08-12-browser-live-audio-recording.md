# Browser Live Audio Recording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable browser live audio recording for therapists with MediaRecorder controls, playback preview, consent verification, and direct submit bridge to the ASR pipeline.

**Architecture:** Connect `BrowserAudioRecorder` component in `session-intake-steps.tsx` to `recordedAudio` state in `session-workspace-model.tsx`, adding a direct action button that converts recorded `Blob` into a `File` object and triggers `handleAudioFileUpload()` for seamless ASR processing.

**Tech Stack:** React, TypeScript, Next.js, MediaRecorder API, Web Audio API, Vitest, Testing Library.

---

### Task 1: Add Direct Pipeline Submit Bridge to Browser Audio Recorder Panel

**Files:**
- Modify: `apps/lingualens-app/src/features/sessions/intake/session-intake-steps.tsx:200-225`
- Modify: `apps/lingualens-app/src/features/sessions/components/session-workspace-model.tsx:168-178`
- Test: `apps/lingualens-app/src/__tests__/browser-audio-recorder.test.tsx`

- [ ] **Step 1: Write failing test for direct pipeline submission of recorded audio blob**

```typescript
it("converts recorded blob and submits directly to audio pipeline", async () => {
  const onRecordingReady = vi.fn();
  render(
    <BrowserAudioRecorder
      initialDurationSeconds={0}
      hadUnsavedRecording={false}
      onMetadataChange={vi.fn()}
      onRecordingReady={onRecordingReady}
    />
  );
  // Test start -> stop -> ready callback with recorded blob
});
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/browser-audio-recorder.test.tsx`
Expected: PASS

- [ ] **Step 3: Connect recorded audio submit button in session intake step panel**

```tsx
{recordedAudio && (
  <ActionButton
    type="button"
    onClick={() => {
      const file = new File(
        [recordedAudio.blob],
        `recorded-audio-${Date.now()}.webm`,
        { type: recordedAudio.metadata.mimeType || "audio/webm" }
      );
      handleAudioFileSelected(file);
      void handleAudioFileUpload();
    }}
  >
    ส่งวิเคราะห์ด้วย ASR Pipeline
  </ActionButton>
)}
```

- [ ] **Step 4: Run frontend unit tests to verify pass**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/browser-audio-recorder.test.tsx src/__tests__/audio-file-upload-panel.test.tsx`
Expected: PASS (100%)

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/src/features/sessions/intake/session-intake-steps.tsx apps/lingualens-app/src/features/sessions/components/session-workspace-model.tsx apps/lingualens-app/src/__tests__/browser-audio-recorder.test.tsx
git commit -m "feat(recorder): connect browser live audio recording directly to ASR pipeline"
```

---

### Task 2: Complete Pipeline Verification under Full Release Gate

**Files:**
- Test: `scripts/check_v170_speech_pipeline.sh`

- [ ] **Step 1: Execute release gate script**

Run: `bash scripts/check_v170_speech_pipeline.sh`
Expected: All 416 API unit tests and 16 frontend unit tests PASS.

- [ ] **Step 2: Commit plan completion**

```bash
git add docs/superpowers/plans/2026-08-12-browser-live-audio-recording.md
git commit -m "docs(plan): complete Browser Live Audio Recording plan"
```
