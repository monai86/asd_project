import { beforeEach, describe, expect, it } from "vitest";

import {
  clearExperimentalTranscriptionMock,
  createExperimentalTranscriptionJob,
  getExperimentalTranscriptionJob,
  uploadRecordedAudio
} from "@/lib/experimental-transcription-service";

beforeEach(() => {
  clearExperimentalTranscriptionMock();
});

describe("experimental transcription local mock API", () => {
  it("uploads audio in memory and advances a processing job to a review-gated draft", async () => {
    const upload = await uploadRecordedAudio(
      new Blob(["recorded-audio"], { type: "audio/webm" }),
      { durationSeconds: 14, mimeType: "audio/webm" }
    );
    const queued = await createExperimentalTranscriptionJob(upload.uploadId);

    expect(queued.status).toBe("queued");
    expect((await getExperimentalTranscriptionJob(queued.jobId)).status).toBe("processing");

    const completed = await getExperimentalTranscriptionJob(queued.jobId);
    expect(completed.status).toBe("completed");
    expect(completed.draftTranscript).toContain("@Begin");
    expect(completed.draftTranscript).toContain("*UNK:");
    expect(completed.label).toBe("Draft transcript — therapist review required.");
  });

  it("fails clearly when the uploaded recording is empty", async () => {
    await expect(
      uploadRecordedAudio(new Blob([], { type: "audio/webm" }), {
        durationSeconds: 0,
        mimeType: "audio/webm"
      })
    ).rejects.toThrow("Recorded audio is empty.");
  });
});
