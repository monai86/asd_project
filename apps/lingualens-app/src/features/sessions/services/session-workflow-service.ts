import {
  attestBackendTranscript,
  createBackendTranscript,
  generateBackendReport,
  getBackendReport,
  getBackendSession,
  getBackendTranscript,
  runBackendAnalysis,
  runBackendQa,
  updateBackendCase,
  updateBackendTranscript,
  uploadAudioFileBytes,
  type WorkflowSource,
} from "@/lib/workflow";
import { apiGet, apiRequest, ApiError } from "@/lib/api";
import type { AudioCapabilities } from "@/features/sessions/intake/audio-file-upload-panel";

export type SessionIdentifiers = {
  sessionId: string;
  transcriptId?: string;
  reportId?: string;
};

export type SaveTranscriptInput = {
  sessionId: string;
  transcriptId?: string;
  source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">;
  originalText: string;
  normalizedText: string;
  sourceFilename?: string;
};

export type GenerateReportInput = {
  sessionId: string;
  providerId?: string;
  allowTemplateFallback?: boolean;
  therapistNotes?: string;
  sessionGoals?: string[];
};

export type AudioUploadIntent = {
  audioFileId: string;
  sourceAssetVersion: number;
  uploadUrl: string;
  requiredHeaders: Record<string, string>;
};

export type NormalizedAudioVerification = {
  source_audio_file_id: string;
  source_asset_version: number;
  normalized_asset_version: number;
  source_checksum_sha256: string;
  normalized_checksum_sha256: string;
  duration_ms: number;
  verification_status: "verified";
};

export type AudioProcessingJob = {
  job_id: string;
  status: "queued" | "processing" | "transcription_completed" | "needs_review" | "failed" | "cancelled";
  message: string;
  error_code?: string | null;
  details?: {
    asr_draft?: { transcript_id?: string | null };
    retry_allowed?: boolean;
    remediation?: string;
    provider_remediation?: string;
    [key: string]: unknown;
  };
};

type UploadIntentResponse = AudioProcessingJob & {
  details: {
    audio_file?: {
      audio_file_id?: string;
      source_asset_version?: number;
    };
    upload_intent?: {
      upload_url?: string;
      required_headers?: Record<string, string>;
    };
  };
};

export type AudioWorkflowFailure = {
  code: string;
  message: string;
  retryable: boolean;
};

export const sessionWorkflowService = {
  grantCaseConsent: async (caseId: string) => updateBackendCase(caseId, { consent_status: "granted" }),

  load: async (ids: SessionIdentifiers) => {
    const session = await getBackendSession(ids.sessionId);
    const resolvedTranscriptId = ids.transcriptId ?? session.transcript_id;
    const resolvedReportId = ids.reportId ?? session.report_id;
    const [transcript, report] = await Promise.all([
      resolvedTranscriptId ? getBackendTranscript(resolvedTranscriptId) : Promise.resolve(undefined),
      resolvedReportId ? getBackendReport(resolvedReportId) : Promise.resolve(undefined),
    ]);
    return { session, transcript, report };
  },

  saveTranscript: async (input: SaveTranscriptInput) => input.transcriptId
    ? updateBackendTranscript(input.transcriptId, input.normalizedText, "Therapist saved transcript edits.")
    : createBackendTranscript(
        input.sessionId,
        input.source,
        input.originalText,
        input.normalizedText,
        input.sourceFilename,
      ),

  runQa: async (transcriptId: string) => runBackendQa(transcriptId),

  attest: async (transcriptId: string) => attestBackendTranscript(transcriptId),

  extractFindings: async (sessionId: string, transcriptId?: string) => runBackendAnalysis(sessionId, transcriptId),

  generateReport: async (input: GenerateReportInput) => generateBackendReport(
    input.sessionId,
    input.providerId ?? "template",
    input.allowTemplateFallback ?? false,
    input.therapistNotes,
    input.sessionGoals ?? [],
  ),

  getAudioCapabilities: async () => apiGet<AudioCapabilities>("/audio/capabilities"),

  createAudioUploadIntent: async (sessionId: string, file: File): Promise<AudioUploadIntent> => {
    const response = await apiRequest<UploadIntentResponse>(`/sessions/${encodeURIComponent(sessionId)}/audio/upload`, {
      method: "POST",
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || contentTypeFromFilename(file.name),
        size_bytes: file.size,
      }),
    });
    const audioFileId = response.details.audio_file?.audio_file_id;
    const sourceAssetVersion = response.details.audio_file?.source_asset_version;
    const uploadUrl = response.details.upload_intent?.upload_url;
    if (
      !audioFileId
      || !uploadUrl
      || typeof sourceAssetVersion !== "number"
      || !Number.isSafeInteger(sourceAssetVersion)
      || sourceAssetVersion < 1
    ) {
      throw new Error("audio_upload_intent_incomplete");
    }
    return {
      audioFileId,
      sourceAssetVersion,
      uploadUrl,
      requiredHeaders: response.details.upload_intent?.required_headers ?? {},
    };
  },

  uploadAudioSource: async (intent: AudioUploadIntent, file: File) => {
    const uploadUrl = intent.uploadUrl.startsWith("mock-signed-upload://")
      ? `/audio/${encodeURIComponent(intent.audioFileId)}/upload-file`
      : intent.uploadUrl;
    await uploadAudioFileBytes(uploadUrl, file, intent.requiredHeaders);
  },

  completeAudioUpload: async (intent: AudioUploadIntent, file: File) => apiRequest(
    `/audio/${encodeURIComponent(intent.audioFileId)}/complete-upload`,
    {
      method: "POST",
      body: JSON.stringify({ size_bytes: file.size }),
    },
  ),

  verifyAndNormalizeAudio: async (audioFileId: string) => apiRequest<NormalizedAudioVerification>(
    `/audio/${encodeURIComponent(audioFileId)}/verify-and-normalize`,
    { method: "POST" },
  ),

  startAudioTranscription: async (
    sessionId: string,
    intent: AudioUploadIntent,
    normalized: NormalizedAudioVerification,
  ) => apiRequest<AudioProcessingJob>(`/sessions/${encodeURIComponent(sessionId)}/audio/process`, {
    method: "POST",
    body: JSON.stringify({
      audio_file_id: intent.audioFileId,
      provider_id: "local_faster_whisper",
      expected_source_asset_version: normalized.source_asset_version,
      expected_normalized_asset_version: normalized.normalized_asset_version,
    }),
  }),

  getAudioProcessingJob: async (jobId: string) => apiGet<AudioProcessingJob>(
    `/jobs/${encodeURIComponent(jobId)}`,
  ),

  retryAudioProcessingJob: async (jobId: string) => apiRequest<AudioProcessingJob>(
    `/jobs/${encodeURIComponent(jobId)}/retry`,
    { method: "POST" },
  ),
};

export function describeAudioWorkflowFailure(error: unknown): AudioWorkflowFailure {
  if (error instanceof ApiError) {
    const detail = parseApiErrorDetail(error.body);
    const code = typeof detail?.error_code === "string" ? detail.error_code : `http_${error.status}`;
    const remediation = typeof detail?.remediation === "string" ? detail.remediation : undefined;
    return {
      code,
      message: remediation ?? failureMessage(code),
      retryable: false,
    };
  }
  const code = error instanceof Error && /^[a-z0-9_]+$/.test(error.message)
    ? error.message
    : "audio_workflow_unavailable";
  return { code, message: failureMessage(code), retryable: false };
}

export function describeFailedAudioJob(job: AudioProcessingJob): AudioWorkflowFailure {
  const code = job.error_code || "transcription_failed";
  const remediation = typeof job.details?.provider_remediation === "string"
    ? job.details.provider_remediation
    : typeof job.details?.remediation === "string"
      ? job.details.remediation
      : undefined;
  return {
    code,
    message: remediation ?? failureMessage(code),
    retryable: job.details?.retry_allowed === true,
  };
}

function parseApiErrorDetail(body: string): Record<string, unknown> | undefined {
  try {
    const payload = JSON.parse(body) as { detail?: unknown };
    const detail = payload.detail ?? payload;
    return detail && typeof detail === "object" && !Array.isArray(detail)
      ? detail as Record<string, unknown>
      : undefined;
  } catch {
    return undefined;
  }
}

function failureMessage(code: string): string {
  const messages: Record<string, string> = {
    audio_duration_limit_exceeded: "Audio is longer than 15 minutes. Choose a shorter file and upload it again.",
    audio_size_limit_exceeded: "Audio is larger than 100 MB. Choose a smaller file and upload it again.",
    audio_format_unavailable: "This audio format is not supported by the verified decoder. Choose one of the formats shown above.",
    unsupported_audio_profile: "The decoded audio profile is unsupported. Convert the source to a supported WAV or MP3 file without truncating it.",
    audio_decode_failed: "The server could not decode this audio file. Verify the source file and upload it again.",
    audio_normalization_failed: "The server could not create the verified normalized working copy. Ask an administrator to inspect the pinned audio runtime.",
    provider_unavailable: "Local faster-whisper is unavailable. Install or restore the pinned provider runtime before retrying.",
    model_artifact_missing: "The pinned faster-whisper model is missing. Install the verified model artifact before retrying.",
    runtime_profile_unavailable: "The verified ASR runtime profile is unavailable. Generate or restore the pinned benchmark profile before retrying.",
    transcription_failed: "Transcription failed without producing a complete draft. Review the provider status before retrying.",
    audio_upload_intent_incomplete: "The backend did not return a complete private upload intent. Retry after the storage capability is restored.",
    audio_workflow_unavailable: "The verified audio workflow is unavailable. Check the backend connection and retry from this file.",
  };
  return messages[code] ?? "The verified audio workflow stopped. Use the error code to remediate the backend capability, then retry.";
}

function contentTypeFromFilename(filename: string): string {
  const extension = filename.split(".").pop()?.toLowerCase();
  return extension === "wav"
    ? "audio/wav"
    : extension === "mp3"
      ? "audio/mpeg"
      : extension === "m4a"
        ? "audio/mp4"
        : extension === "webm"
          ? "audio/webm"
          : "application/octet-stream";
}
