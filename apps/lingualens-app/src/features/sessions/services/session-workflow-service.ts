import {
  attestBackendTranscript,
  createBackendTranscript,
  confirmSpeakerMapping,
  backendTranscriptRequiresSpeakerMapping,
  generateBackendReport,
  getBackendReport,
  getBackendSession,
  getSpeakerMapping,
  getBackendTranscript,
  runBackendQa,
  saveSpeakerMappingDraft,
  updateBackendCase,
  updateBackendTranscript,
  type SpeakerMapping,
  type SpeakerMappingEntry,
  type WorkflowSource,
} from "@/lib/workflow";
import { runBackendAnalysis } from "@/services/adapters/analysis-adapter";

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

export type SaveSpeakerMappingDraftInput = {
  expected_transcript_version: number;
  expected_mapping_version?: number;
  entries: Array<Pick<SpeakerMappingEntry,
    "temporary_speaker_id" | "confirmed_chat_code" | "participant_role" | "reviewed_utterance_ids"
  >>;
};

export type ConfirmSpeakerMappingInput = {
  expected_transcript_version: number;
  expected_mapping_version: number;
};

export const sessionWorkflowService = {
  grantCaseConsent: async (
    caseId: string,
    verification?: { signer: string; date: string; notes: string; existingNotes?: string },
  ) => {
    const verifiedOn = verification?.date ?? new Date().toISOString().slice(0, 10);
    const verifiedBy = verification?.signer ?? "Parent";
    const record = `Consent verified on ${verifiedOn} by ${verifiedBy}.${verification?.notes ? ` Notes: ${verification.notes}` : ""}`;
    return updateBackendCase(caseId, {
      consent_status: "granted",
      notes: `${verification?.existingNotes ? `${verification.existingNotes}\n` : ""}${record}`,
    });
  },

  load: async (ids: SessionIdentifiers) => {
    const session = await getBackendSession(ids.sessionId);
    const resolvedTranscriptId = ids.transcriptId ?? session.transcript_id;
    const resolvedReportId = ids.reportId ?? session.report_id;
    const [transcript, report] = await Promise.all([
      resolvedTranscriptId ? getBackendTranscript(resolvedTranscriptId) : Promise.resolve(undefined),
      resolvedReportId ? getBackendReport(resolvedReportId) : Promise.resolve(undefined),
    ]);
    const speakerMapping = transcript && backendTranscriptRequiresSpeakerMapping(transcript)
      ? await getSpeakerMapping(transcript.transcript_id)
      : undefined;
    return { session, transcript, report, speakerMapping };
  },

  saveSpeakerMappingDraft: async (
    transcriptId: string,
    input: SaveSpeakerMappingDraftInput,
  ): Promise<SpeakerMapping> => saveSpeakerMappingDraft(transcriptId, input),

  confirmSpeakerMapping: async (
    transcriptId: string,
    input: ConfirmSpeakerMappingInput,
  ): Promise<SpeakerMapping> => confirmSpeakerMapping(transcriptId, input),

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
};
