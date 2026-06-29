export type ExperimentalTranscriptionStatus = "queued" | "processing" | "completed" | "failed";

export type ExperimentalTranscriptionJob = {
  jobId: string;
  uploadId: string;
  status: ExperimentalTranscriptionStatus;
  message: string;
  label: "Draft transcript — therapist review required.";
  draftTranscript?: string;
  error?: string;
};

type AudioUpload = {
  blob: Blob;
  durationSeconds: number;
  mimeType: string;
};

type StoredJob = ExperimentalTranscriptionJob & {
  pollCount: number;
};

const uploads = new Map<string, AudioUpload>();
const jobs = new Map<string, StoredJob>();
let sequence = 0;

export async function uploadRecordedAudio(
  blob: Blob,
  metadata: { durationSeconds: number; mimeType: string }
) {
  if (blob.size === 0) {
    throw new Error("Recorded audio is empty.");
  }
  const uploadId = `local-audio-${++sequence}`;
  uploads.set(uploadId, {
    blob,
    durationSeconds: metadata.durationSeconds,
    mimeType: metadata.mimeType
  });
  return { uploadId };
}

export async function createExperimentalTranscriptionJob(uploadId: string): Promise<ExperimentalTranscriptionJob> {
  if (!uploads.has(uploadId)) {
    throw new Error("Uploaded recording was not found.");
  }
  const job: StoredJob = {
    jobId: `local-job-${++sequence}`,
    uploadId,
    status: "queued",
    message: "Experimental transcription job queued.",
    label: "Draft transcript — therapist review required.",
    pollCount: 0
  };
  jobs.set(job.jobId, job);
  return publicJob(job);
}

export async function getExperimentalTranscriptionJob(jobId: string): Promise<ExperimentalTranscriptionJob> {
  const job = jobs.get(jobId);
  if (!job) {
    throw new Error("Transcription job was not found.");
  }
  job.pollCount += 1;
  if (job.pollCount === 1) {
    job.status = "processing";
    job.message = "Experimental ASR is processing the recording.";
  } else if (job.status !== "failed") {
    job.status = "completed";
    job.message = "Draft transcript created. Therapist review and attestation are required before feature extraction.";
    job.draftTranscript = buildMockDraft();
  }
  return publicJob(job);
}

export function clearExperimentalTranscriptionMock() {
  uploads.clear();
  jobs.clear();
  sequence = 0;
}

export function releaseExperimentalAudioUpload(uploadId: string) {
  uploads.delete(uploadId);
}

function publicJob(job: StoredJob): ExperimentalTranscriptionJob {
  const { pollCount: _pollCount, ...result } = job;
  return { ...result };
}

function buildMockDraft() {
  return [
    "@Begin",
    "@Languages:\teng",
    "@Participants:\tUNK Unverified_Speaker Unknown",
    "@ID:\teng|local-mock|UNK|||||Unknown|||",
    "*UNK:\tMock ASR output for workflow testing. Listen to the recording and replace this text.",
    "@End"
  ].join("\n");
}
