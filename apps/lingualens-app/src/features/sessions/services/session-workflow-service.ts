import {
  attestBackendTranscript,
  acknowledgeBackendLimitation,
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

export type AudioCapabilities = {
  milestone: "v1.7.0-testbed";
  max_size_bytes: number;
  max_duration_seconds: number;
  supported_formats: string[];
  processing_state: "available" | "unavailable";
  unavailable_reason?: string | null;
  normalization: {
    channels: 1;
    sample_rate_hz: number;
    format: "wav_pcm_s16le";
    source_min_sample_rate_hz: number;
    source_max_sample_rate_hz: number;
    source_max_channels: number;
    max_rational_factor: number;
    max_filter_taps: number;
    max_working_bytes: number;
  };
  browser_recording: {
    state: "experimental_unavailable";
    blocks_milestone: false;
  };
};

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
  replaceExisting?: boolean;
  expectedExistingTranscriptId?: string;
  expectedExistingTranscriptVersion?: number;
};

export type GenerateReportInput = {
  sessionId: string;
  providerId?: string;
  allowTemplateFallback?: boolean;
  therapistNotes?: string;
  sessionGoals?: string[];
};

export type AudioUploadIntent = {
  sessionId: string;
  audioFileId: string;
  sourceAssetVersion: number;
  uploadUrl: string;
  requiredHeaders: Record<string, string>;
};

export type AudioLineage = {
  audioFileId: string;
  sourceAssetVersion: number;
  sourceChecksumSha256: string;
  normalizedAssetVersion: number;
  normalizedChecksumSha256: string;
  providerId: "local_faster_whisper";
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
  session_id: string;
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

export type AudioWorkflowFailure = {
  code: string;
  message: string;
  retryable: boolean;
};

export type SpeakerMappingIssue = {
  code: string;
  severity: string;
  message: string;
  blocking?: boolean;
};

export type SpeakerMappingDisposition = "target" | "non_target" | "unknown" | "merged";

export type SpeakerMappingEntry = {
  temporary_speaker_id: string;
  confirmed_chat_code: string | null;
  participant_role: string;
  disposition: SpeakerMappingDisposition;
  merged_into_temporary_speaker_id: string | null;
  affected_utterance_ids: string[];
  source_speaker_label: string | null;
  source_provider: string | null;
  source_provider_metadata: Record<string, unknown>;
  reviewed_utterance_ids: string[];
};

export type SpeakerMappingResponse = {
  transcript_id: string;
  transcript_version: number;
  mapping_id: string | null;
  mapping_version: number;
  status: "draft" | "confirmed" | "stale";
  entries: SpeakerMappingEntry[];
  issues: SpeakerMappingIssue[];
  confirmed_by_user_id: string | null;
  confirmed_by_role: string | null;
  confirmed_at: string | null;
};

export class AudioWorkflowContractError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.name = "AudioWorkflowContractError";
    this.code = code;
  }
}

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

  saveTranscript: async (input: SaveTranscriptInput) => validateSavedTranscriptResponse(
    input.transcriptId && !input.replaceExisting
      ? await updateBackendTranscript(input.transcriptId, input.normalizedText, "Therapist saved transcript edits.")
      : await createBackendTranscript(
          input.sessionId,
          input.source,
          input.originalText,
          input.normalizedText,
          input.sourceFilename,
          {
            replaceExisting: input.replaceExisting === true,
            expectedExistingTranscriptId: input.expectedExistingTranscriptId,
            expectedExistingTranscriptVersion: input.expectedExistingTranscriptVersion,
          },
        ),
    input,
  ),

  runQa: async (transcriptId: string) => runBackendQa(transcriptId),

  acknowledgeLimitation: acknowledgeBackendLimitation,

  attest: async (transcriptId: string, acknowledgmentIds: string[] = []) => attestBackendTranscript(transcriptId, acknowledgmentIds),

  extractFindings: async (sessionId: string, transcriptId?: string) => runBackendAnalysis(sessionId, transcriptId),

  generateReport: async (input: GenerateReportInput) => generateBackendReport(
    input.sessionId,
    input.providerId ?? "template",
    input.allowTemplateFallback ?? false,
    input.therapistNotes,
    input.sessionGoals ?? [],
  ),

  getAudioCapabilities: async () => parseAudioCapabilities(
    await apiGet<unknown>("/audio/capabilities"),
  ),

  createAudioUploadIntent: async (
    sessionId: string,
    file: File,
    signal?: AbortSignal,
  ): Promise<AudioUploadIntent> => {
    const response = await apiRequest<unknown>(`/sessions/${encodeURIComponent(sessionId)}/audio/upload`, {
      method: "POST",
      signal,
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || contentTypeFromFilename(file.name),
        size_bytes: file.size,
      }),
    });
    const responseRecord = recordValue(response);
    const details = recordValue(responseRecord?.details);
    const audioFile = recordValue(details?.audio_file);
    const uploadIntent = recordValue(details?.upload_intent);
    const audioFileId = stringValue(audioFile?.audio_file_id);
    const sourceAssetVersion = audioFile?.source_asset_version;
    const audioSessionId = stringValue(audioFile?.session_id);
    const uploadAudioFileId = stringValue(uploadIntent?.audio_file_id);
    const uploadUrl = stringValue(uploadIntent?.upload_url);
    if (
      !audioFileId
      || !uploadIntent
      || !uploadUrl
      || responseRecord?.session_id !== sessionId
      || audioSessionId !== sessionId
      || uploadAudioFileId !== audioFileId
      || typeof sourceAssetVersion !== "number"
      || !Number.isSafeInteger(sourceAssetVersion)
      || sourceAssetVersion < 1
    ) {
      throw new Error("audio_upload_intent_incomplete");
    }
    return {
      sessionId,
      audioFileId,
      sourceAssetVersion,
      uploadUrl,
      requiredHeaders: optionalStringRecord(uploadIntent, "required_headers"),
    };
  },

  uploadAudioSource: async (intent: AudioUploadIntent, file: File, signal?: AbortSignal) => {
    const uploadUrl = intent.uploadUrl.startsWith("mock-signed-upload://")
      ? `/audio/${encodeURIComponent(intent.audioFileId)}/upload-file`
      : intent.uploadUrl;
    await uploadAudioFileBytes(uploadUrl, file, intent.requiredHeaders, signal);
  },

  completeAudioUpload: async (intent: AudioUploadIntent, file: File, signal?: AbortSignal) => {
    const response = await apiRequest<unknown>(
      `/audio/${encodeURIComponent(intent.audioFileId)}/complete-upload`,
      {
      method: "POST",
      signal,
      body: JSON.stringify({ size_bytes: file.size }),
      },
    );
    const record = recordValue(response);
    if (
      record?.audio_file_id !== intent.audioFileId
      || record.upload_status !== "uploaded"
      || record.source_asset_version !== intent.sourceAssetVersion
    ) {
      throw new AudioWorkflowContractError("audio_upload_completion_invalid");
    }
  },

  verifyAndNormalizeAudio: async (intent: AudioUploadIntent, signal?: AbortSignal) => parseNormalizedAudioVerification(
    await apiRequest<unknown>(
      `/audio/${encodeURIComponent(intent.audioFileId)}/verify-and-normalize`,
      { method: "POST", signal },
    ),
    intent,
  ),

  startAudioTranscription: async (
    sessionId: string,
    intent: AudioUploadIntent,
    normalized: NormalizedAudioVerification,
    signal?: AbortSignal,
  ) => parseAudioProcessingJob(
    await apiRequest<unknown>(`/sessions/${encodeURIComponent(sessionId)}/audio/process`, {
      method: "POST",
      signal,
      body: JSON.stringify({
        audio_file_id: intent.audioFileId,
        provider_id: "local_faster_whisper",
        expected_source_asset_version: normalized.source_asset_version,
        expected_normalized_asset_version: normalized.normalized_asset_version,
      }),
    }),
    { expectedSessionId: sessionId, expectedLineage: audioLineage(intent, normalized) },
  ),

  getAudioProcessingJob: async (
    jobId: string,
    signal?: AbortSignal,
    expectedSessionId?: string,
    expectedLineage?: AudioLineage,
  ) => parseAudioProcessingJob(
    await apiGet<unknown>(`/jobs/${encodeURIComponent(jobId)}`, { signal }),
    { expectedJobId: jobId, expectedSessionId, expectedLineage },
  ),

  retryAudioProcessingJob: async (
    jobId: string,
    expectedSessionId: string,
    expectedLineage: AudioLineage,
    signal?: AbortSignal,
  ) => parseAudioProcessingJob(
    await apiRequest<unknown>(
      `/jobs/${encodeURIComponent(jobId)}/retry`,
      { method: "POST", signal },
    ),
    { expectedSessionId, expectedLineage },
  ),

  cancelAudioProcessingJob: async (jobId: string) => apiRequest<unknown>(
    `/jobs/${encodeURIComponent(jobId)}/cancel`,
    { method: "POST" },
  ),

  getSpeakerMapping: async (
    transcriptId: string,
    signal?: AbortSignal,
  ) => parseSpeakerMappingResponse(
    await apiGet<unknown>(`/transcripts/${encodeURIComponent(transcriptId)}/speaker-mapping`, { signal }),
    { expectedTranscriptId: transcriptId },
  ),

  saveSpeakerMappingDraft: async (
    transcriptId: string,
    input: {
      transcriptVersion: number;
      mappingVersion: number;
      entries: SpeakerMappingEntry[];
    },
    signal?: AbortSignal,
  ) => parseSpeakerMappingResponse(
    await apiRequest<unknown>(`/transcripts/${encodeURIComponent(transcriptId)}/speaker-mapping`, {
      method: "PUT",
      signal,
      body: JSON.stringify({
        expected_transcript_version: input.transcriptVersion,
        expected_mapping_version: input.mappingVersion > 0 ? input.mappingVersion : null,
        entries: input.entries,
      }),
    }),
    {
      expectedTranscriptId: transcriptId,
      minimumMappingVersion: Math.max(1, input.mappingVersion + 1),
    },
  ),

  confirmSpeakerMapping: async (
    transcriptId: string,
    input: {
      transcriptVersion: number;
      mappingVersion: number;
    },
    signal?: AbortSignal,
  ) => parseSpeakerMappingResponse(
    await apiRequest<unknown>(`/transcripts/${encodeURIComponent(transcriptId)}/speaker-mapping/confirm`, {
      method: "POST",
      signal,
      body: JSON.stringify({
        expected_transcript_version: input.transcriptVersion,
        expected_mapping_version: input.mappingVersion,
      }),
    }),
    {
      expectedTranscriptId: transcriptId,
      expectedTranscriptVersion: input.transcriptVersion,
      minimumMappingVersion: input.mappingVersion + 1,
      expectedStatus: "confirmed",
    },
  ),
};

const AUDIO_JOB_STATUSES = [
  "queued",
  "processing",
  "transcription_completed",
  "needs_review",
  "failed",
  "cancelled",
] as const;

function parseAudioCapabilities(value: unknown): AudioCapabilities {
  const record = recordValue(value);
  const browserRecording = recordValue(record?.browser_recording);
  const normalization = recordValue(record?.normalization);
  const supportedFormats = record?.supported_formats;
  const supportedFormatCount = Array.isArray(supportedFormats) ? supportedFormats.length : -1;
  const formats = Array.isArray(supportedFormats)
    ? supportedFormats.filter(
        (item): item is string => typeof item === "string" && /^[a-z0-9]+$/.test(item),
      )
    : undefined;
  if (
    record?.milestone !== "v1.7.0-testbed"
    || !positiveSafeInteger(record.max_size_bytes)
    || !positiveSafeInteger(record.max_duration_seconds)
    || !formats
    || formats.length !== supportedFormatCount
    || (record.processing_state !== "available" && record.processing_state !== "unavailable")
    || normalization?.channels !== 1
    || !positiveSafeInteger(normalization.sample_rate_hz)
    || normalization.format !== "wav_pcm_s16le"
    || !positiveSafeInteger(normalization.source_min_sample_rate_hz)
    || !positiveSafeInteger(normalization.source_max_sample_rate_hz)
    || !positiveSafeInteger(normalization.source_max_channels)
    || !positiveSafeInteger(normalization.max_rational_factor)
    || !positiveSafeInteger(normalization.max_filter_taps)
    || !positiveSafeInteger(normalization.max_working_bytes)
    || browserRecording?.state !== "experimental_unavailable"
    || browserRecording.blocks_milestone !== false
    || (record.unavailable_reason !== undefined
      && record.unavailable_reason !== null
      && typeof record.unavailable_reason !== "string")
  ) {
    throw new AudioWorkflowContractError("audio_capabilities_response_invalid");
  }
  return {
    milestone: "v1.7.0-testbed",
    max_size_bytes: record.max_size_bytes,
    max_duration_seconds: record.max_duration_seconds,
    supported_formats: formats,
    processing_state: record.processing_state,
    unavailable_reason: record.unavailable_reason,
    normalization: {
      channels: 1,
      sample_rate_hz: normalization.sample_rate_hz,
      format: "wav_pcm_s16le",
      source_min_sample_rate_hz: normalization.source_min_sample_rate_hz,
      source_max_sample_rate_hz: normalization.source_max_sample_rate_hz,
      source_max_channels: normalization.source_max_channels,
      max_rational_factor: normalization.max_rational_factor,
      max_filter_taps: normalization.max_filter_taps,
      max_working_bytes: normalization.max_working_bytes,
    },
    browser_recording: {
      state: "experimental_unavailable",
      blocks_milestone: false,
    },
  };
}

function validateSavedTranscriptResponse(
  transcript: Awaited<ReturnType<typeof createBackendTranscript>>,
  input: SaveTranscriptInput,
) {
  const expectedSource = input.source === "paste-transcript" ? "manual_entry" : "cha_upload:";
  const sourceMatches = expectedSource === "manual_entry"
    ? transcript.source === expectedSource
    : transcript.source?.startsWith(expectedSource) === true;
  if (
    !stringValue(transcript.transcript_id)
    || transcript.session_id !== input.sessionId
    || !positiveSafeInteger(transcript.version)
    || !sourceMatches
    || (input.transcriptId && !input.replaceExisting && transcript.transcript_id !== input.transcriptId)
    || (input.replaceExisting && transcript.transcript_id === input.expectedExistingTranscriptId)
  ) {
    throw new AudioWorkflowContractError("transcript_save_response_invalid");
  }
  return transcript;
}

function parseNormalizedAudioVerification(
  value: unknown,
  intent: AudioUploadIntent,
): NormalizedAudioVerification {
  const record = recordValue(value);
  if (
    record?.source_audio_file_id !== intent.audioFileId
    || record.source_asset_version !== intent.sourceAssetVersion
    || !positiveSafeInteger(record.normalized_asset_version)
    || !sha256Value(record.source_checksum_sha256)
    || !sha256Value(record.normalized_checksum_sha256)
    || !positiveSafeInteger(record.duration_ms)
    || record.verification_status !== "verified"
  ) {
    throw new AudioWorkflowContractError("audio_normalization_response_invalid");
  }
  return {
    source_audio_file_id: intent.audioFileId,
    source_asset_version: record.source_asset_version,
    normalized_asset_version: record.normalized_asset_version,
    source_checksum_sha256: record.source_checksum_sha256,
    normalized_checksum_sha256: record.normalized_checksum_sha256,
    duration_ms: record.duration_ms,
    verification_status: "verified",
  };
}

function parseAudioProcessingJob(
  value: unknown,
  expected: {
    expectedJobId?: string;
    expectedSessionId?: string;
    expectedLineage?: AudioLineage;
  } = {},
): AudioProcessingJob {
  const record = recordValue(value);
  const jobId = stringValue(record?.job_id);
  const sessionId = stringValue(record?.session_id);
  const message = stringValue(record?.message);
  const status = record?.status;
  const details = record?.details === undefined ? {} : recordValue(record.details);
  const asrDraft = recordValue(details?.asr_draft);
  if (
    !jobId
    || !sessionId
    || !message
    || !AUDIO_JOB_STATUSES.some((candidate) => candidate === status)
    || (expected.expectedJobId && jobId !== expected.expectedJobId)
    || (expected.expectedSessionId && sessionId !== expected.expectedSessionId)
    || (expected.expectedLineage && (!details || !jobLineageMatches(details, expected.expectedLineage)))
    || (record?.error_code !== undefined
      && record.error_code !== null
      && typeof record.error_code !== "string")
    || !details
    || (status === "needs_review" && !stringValue(asrDraft?.transcript_id))
    || (details.retry_allowed !== undefined && typeof details.retry_allowed !== "boolean")
    || (details.remediation !== undefined && typeof details.remediation !== "string")
    || (details.provider_remediation !== undefined && typeof details.provider_remediation !== "string")
  ) {
    throw new AudioWorkflowContractError("audio_job_response_invalid");
  }
  return {
    job_id: jobId,
    session_id: sessionId,
    status: status as AudioProcessingJob["status"],
    message,
    error_code: record?.error_code as string | null | undefined,
    details: details as AudioProcessingJob["details"],
  };
}

function parseSpeakerMappingResponse(
  value: unknown,
  expected: {
    expectedTranscriptId: string;
    expectedTranscriptVersion?: number;
    minimumMappingVersion?: number;
    expectedStatus?: SpeakerMappingResponse["status"];
  },
): SpeakerMappingResponse {
  const record = recordValue(value);
  const transcriptId = stringValue(record?.transcript_id);
  const transcriptVersion = record?.transcript_version;
  const mappingId = record?.mapping_id;
  const mappingVersion = record?.mapping_version;
  const status = record?.status;
  const entries = record?.entries;
  const issues = record?.issues;
  const confirmedByUserId = record?.confirmed_by_user_id;
  const confirmedByRole = record?.confirmed_by_role;
  const confirmedAt = record?.confirmed_at;
  if (
    transcriptId !== expected.expectedTranscriptId
    || !positiveSafeInteger(transcriptVersion)
    || (expected.expectedTranscriptVersion !== undefined && transcriptVersion !== expected.expectedTranscriptVersion)
    || (mappingId !== null && mappingId !== undefined && !stringValue(mappingId))
    || !nonNegativeSafeInteger(mappingVersion)
    || (expected.minimumMappingVersion !== undefined && mappingVersion < expected.minimumMappingVersion)
    || (status !== "draft" && status !== "confirmed" && status !== "stale")
    || (expected.expectedStatus !== undefined && status !== expected.expectedStatus)
    || !Array.isArray(entries)
    || !Array.isArray(issues)
    || (confirmedByUserId !== undefined
      && confirmedByUserId !== null
      && !stringValue(confirmedByUserId))
    || (confirmedByRole !== undefined
      && confirmedByRole !== null
      && !stringValue(confirmedByRole))
    || (confirmedAt !== undefined
      && confirmedAt !== null
      && !stringValue(confirmedAt))
  ) {
    throw new AudioWorkflowContractError("speaker_mapping_response_invalid");
  }
  return {
    transcript_id: transcriptId,
    transcript_version: transcriptVersion,
    mapping_id: mappingId === undefined ? null : mappingId as string | null,
    mapping_version: mappingVersion,
    status,
    entries: entries.map(parseSpeakerMappingEntry),
    issues: issues.map(parseSpeakerMappingIssue),
    confirmed_by_user_id: confirmedByUserId === undefined ? null : confirmedByUserId as string | null,
    confirmed_by_role: confirmedByRole === undefined ? null : confirmedByRole as string | null,
    confirmed_at: confirmedAt === undefined ? null : confirmedAt as string | null,
  };
}

function parseSpeakerMappingEntry(value: unknown): SpeakerMappingEntry {
  const record = recordValue(value);
  const temporarySpeakerId = stringValue(record?.temporary_speaker_id);
  const chatCode = record?.confirmed_chat_code;
  const role = stringValue(record?.participant_role);
  const disposition = record?.disposition;
  const mergedInto = record?.merged_into_temporary_speaker_id;
  const affectedUtteranceIds = stringArray(record?.affected_utterance_ids);
  const sourceSpeakerLabel = record?.source_speaker_label;
  const sourceProvider = record?.source_provider;
  const sourceProviderMetadata = record?.source_provider_metadata === undefined
    ? {}
    : recordValue(record.source_provider_metadata);
  const reviewedUtteranceIds = record?.reviewed_utterance_ids === undefined
    ? []
    : stringArray(record.reviewed_utterance_ids);
  if (
    !temporarySpeakerId
    || (chatCode !== null && chatCode !== undefined && !stringValue(chatCode))
    || !role
    || !isSpeakerMappingDisposition(disposition)
    || (mergedInto !== null && mergedInto !== undefined && !stringValue(mergedInto))
    || !affectedUtteranceIds
    || (sourceSpeakerLabel !== null && sourceSpeakerLabel !== undefined && !stringValue(sourceSpeakerLabel))
    || (sourceProvider !== null && sourceProvider !== undefined && !stringValue(sourceProvider))
    || !sourceProviderMetadata
    || !reviewedUtteranceIds
  ) {
    throw new AudioWorkflowContractError("speaker_mapping_response_invalid");
  }
  return {
    temporary_speaker_id: temporarySpeakerId,
    confirmed_chat_code: chatCode === undefined ? null : chatCode as string | null,
    participant_role: role,
    disposition,
    merged_into_temporary_speaker_id: mergedInto === undefined ? null : mergedInto as string | null,
    affected_utterance_ids: affectedUtteranceIds,
    source_speaker_label: sourceSpeakerLabel === undefined ? null : sourceSpeakerLabel as string | null,
    source_provider: sourceProvider === undefined ? null : sourceProvider as string | null,
    source_provider_metadata: sourceProviderMetadata,
    reviewed_utterance_ids: reviewedUtteranceIds,
  };
}

function parseSpeakerMappingIssue(value: unknown): SpeakerMappingIssue {
  const record = recordValue(value);
  const code = stringValue(record?.code);
  const severity = stringValue(record?.severity);
  const message = stringValue(record?.message);
  const blocking = record?.blocking;
  if (
    !code
    || !severity
    || !message
    || (blocking !== undefined && typeof blocking !== "boolean")
  ) {
    throw new AudioWorkflowContractError("speaker_mapping_response_invalid");
  }
  return {
    code,
    severity,
    message,
    ...(blocking === undefined ? {} : { blocking }),
  };
}

function recordValue(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined;
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function optionalStringRecord(parent: Record<string, unknown>, key: string): Record<string, string> {
  if (!(key in parent) || parent[key] === undefined) return {};
  const record = recordValue(parent[key]);
  if (!record) throw new AudioWorkflowContractError("audio_upload_intent_incomplete");
  if (Object.values(record).some((item) => typeof item !== "string")) {
    throw new AudioWorkflowContractError("audio_upload_intent_incomplete");
  }
  return record as Record<string, string>;
}

export function audioLineage(
  intent: AudioUploadIntent,
  normalized: NormalizedAudioVerification,
): AudioLineage {
  return {
    audioFileId: intent.audioFileId,
    sourceAssetVersion: intent.sourceAssetVersion,
    sourceChecksumSha256: normalized.source_checksum_sha256,
    normalizedAssetVersion: normalized.normalized_asset_version,
    normalizedChecksumSha256: normalized.normalized_checksum_sha256,
    providerId: "local_faster_whisper",
  };
}

function jobLineageMatches(details: Record<string, unknown>, expected: AudioLineage): boolean {
  return details.audio_file_id === expected.audioFileId
    && details.source_asset_version === expected.sourceAssetVersion
    && details.source_checksum_sha256 === expected.sourceChecksumSha256
    && details.normalized_asset_version === expected.normalizedAssetVersion
    && details.normalized_checksum_sha256 === expected.normalizedChecksumSha256
    && details.provider_id === expected.providerId;
}

function positiveSafeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0;
}

function nonNegativeSafeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function sha256Value(value: unknown): value is string {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
}

function stringArray(value: unknown): string[] | undefined {
  return Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value
    : undefined;
}

function isSpeakerMappingDisposition(value: unknown): value is SpeakerMappingDisposition {
  return value === "target" || value === "non_target" || value === "unknown" || value === "merged";
}

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
  const code = error instanceof AudioWorkflowContractError
    ? error.code
    : error instanceof Error && /^[a-z0-9_]+$/.test(error.message)
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
    if (typeof detail === "string" && detail.length > 0) {
      return { remediation: detail };
    }
    return detail && typeof detail === "object" && !Array.isArray(detail)
      ? detail as Record<string, unknown>
      : undefined;
  } catch {
    return undefined;
  }
}

function failureMessage(code: string): string {
  const messages: Record<string, string> = {
    audio_duration_limit_exceeded: "Audio exceeds the configured duration limit shown above. Choose a shorter file and upload it again.",
    audio_size_limit_exceeded: "Audio exceeds the configured size limit shown above. Choose a smaller file and upload it again.",
    audio_format_unavailable: "This audio format is not supported by the verified decoder. Choose one of the formats shown above.",
    unsupported_audio_profile: "The decoded audio profile is unsupported. Convert the source to a supported WAV or MP3 file without truncating it.",
    audio_decode_failed: "The server could not decode this audio file. Verify the source file and upload it again.",
    audio_normalization_failed: "The server could not create the verified normalized working copy. Ask an administrator to inspect the pinned audio runtime.",
    provider_unavailable: "Local faster-whisper is unavailable. Install or restore the pinned provider runtime before retrying.",
    model_artifact_missing: "The pinned faster-whisper model is missing. Install the verified model artifact before retrying.",
    runtime_profile_unavailable: "The verified ASR runtime profile is unavailable. Generate or restore the pinned benchmark profile before retrying.",
    transcription_failed: "Transcription failed without producing a complete draft. Review the provider status before retrying.",
    audio_upload_intent_incomplete: "The backend did not return a complete private upload intent. Retry after the storage capability is restored.",
    audio_upload_completion_invalid: "The backend did not confirm the expected uploaded source version. No normalization or transcription job was started.",
    audio_capabilities_response_invalid: "The backend returned an invalid audio capability contract. Audio upload remains unavailable until the deployment is repaired.",
    audio_normalization_response_invalid: "The backend returned invalid normalized-asset provenance. No transcription job was created.",
    audio_job_response_invalid: "The backend returned an invalid transcription job contract. Monitoring stopped without creating a draft.",
    transcript_lineage_mismatch: "The returned transcript does not belong to the active session. Nothing was persisted; ask an administrator to inspect the job lineage.",
    transcript_save_response_invalid: "The backend returned a transcript that does not match the requested session, source, or replacement version. Nothing was accepted locally.",
    speaker_mapping_response_invalid: "The backend returned an invalid speaker-mapping contract. Confirmed participant roles were not accepted locally.",
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
