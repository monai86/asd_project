import { apiGet, apiRequest, apiText, apiUploadBlob, ApiError, getMockAccessHeaders } from "@/lib/api";

export const WORKFLOW_STORAGE_KEY = "lingualens.therapist.workflow.v1";
export const SEEDED_TRANSCRIPT_SESSION_ID = "SESSION-001";

export type WorkflowSource = "recording" | "audio-upload" | "cha-upload" | "paste-transcript";
export type TranscriptReviewStatus = "not_started" | "draft" | "in_review" | "reviewed";
export type AnalysisStatus = "not_started" | "processing" | "completed" | "failed";
export type TranscriptionJobStatus = "queued" | "processing" | "completed" | "failed";
export type TranscriptQaStatus = "not_run" | "pass" | "warning" | "fail";
export type PersistenceStatus = "idle" | "unsaved" | "saving" | "saved" | "failed";
export type ChatParticipant = {
  code: string;
  name: string;
  role: string;
};
export type ChatId = {
  code: string;
  raw: string;
};
export type ChatMetadata = {
  languages: string[];
  participants: ChatParticipant[];
  ids: ChatId[];
  media?: {
    name: string;
    type: string;
  };
  headers: Record<string, string[]>;
};
export type ChatParseResult = {
  transcriptText: string;
  transcriptLines: TranscriptLine[];
  metadata: ChatMetadata;
  warnings: string[];
  validationIssues: string[];
};
export type TranscriptLine = {
  lineId: string;
  speaker: string;
  text: string;
  startMs?: number;
  endMs?: number;
  unclear?: boolean;
};

export type LanguageSampleFeatures = {
  totalUtterances: number;
  childUtterances: number;
  adultUtterances: number;
  totalWords: number;
  mluWords: number;
  ndw: number;
  ttr: number;
  questionRatio: number;
  unclearRatio: number;
  repetitionCue: number;
  echolaliaCue: number;
  pronounReversalCue: number;
};

export type FeatureDefinition = {
  featureName: string;
  displayName: string;
  description: string;
  valueType: string;
  unit: string;
  calculationMethod: string;
  requiredInputs: string[];
  numeratorDefinition?: string | null;
  denominatorDefinition?: string | null;
  defaultThresholds?: Record<string, string | number | boolean | null> | null;
  limitations: string[];
  clinicalInterpretationCaution: string;
  featureVersion?: string;
  providerName?: string;
  providerId?: string;
};

export type FeatureSignal = {
  featureName: string;
  displayName: string;
  description: string;
  valueType: string;
  unit: string;
  value: string;
  rawValue: string | number | boolean | null;
  calculationMethod: string;
  requiredInputs: string[];
  limitations: string[];
  clinicalInterpretationCaution: string;
  interpretationHint: string;
  referenceText: string;
};

export type EvidenceState =
  | "available"
  | "input_action_required"
  | "unsupported_scope"
  | "insufficient_reference_data"
  | "system_unavailable";

export type EvidenceAvailability = {
  state: EvidenceState;
  reasonCode?: string;
  message: string;
  workflowCanContinue: boolean;
  nextStep?: string;
};

export type AssociatedFeatureEvidence = {
  featureName: string;
  observedValue: number | null;
  position: "below_iqr" | "within_iqr" | "above_iqr" | "missing";
  q1?: number | null;
  median?: number | null;
  q3?: number | null;
  caveat: string;
};

export type EvidenceReviewState = {
  status: "unreviewed" | "reviewed" | "disagreement";
  therapistNote: string;
  reviewedBy?: string;
  reviewedByName?: string;
  reviewedAt?: string;
};

export type ProfileEvidence = {
  profileCode: "TD" | "DD" | "ASD" | "LT" | "STI" | "HL";
  presentationGroup: "TD" | "DD" | "ASD" | "OTHER";
  status: "comparable_patterns_observed" | "limited_comparison" | "not_available";
  availability: EvidenceAvailability;
  participantCount: number;
  corpusCount: number;
  associatedFeatures: AssociatedFeatureEvidence[];
  reviewState: EvidenceReviewState;
};

export type PatternEvidence = {
  status: "no_additional_pattern_cue" | "additional_evidence_review_suggested" | "not_available";
  availability: EvidenceAvailability;
  associatedFeatures: AssociatedFeatureEvidence[];
  reviewState: EvidenceReviewState;
};

export type MlDecisionSupport = {
  resultId: string;
  status: "completed" | "unavailable" | "insufficient_data" | "failed";
  providerName: string;
  providerVersion: string;
  featureSchemaVersion: string;
  generatedAt: string;
  cues: Array<{
    cueCode: string;
    title: string;
    severity: "info" | "review" | "caution";
    explanation: string;
    supportingFeatures: Record<string, string | number | boolean | null>;
    limitations: string[];
    recommendedNextReviewStep: string;
    reviewStatus: "unreviewed" | "acknowledged" | "dismissed";
  }>;
  patternEvidence?: PatternEvidence;
  profileEvidence: ProfileEvidence[];
  artifactProvenance: Record<string, string>;
  limitations: string[];
  notDiagnostic: true;
  decisionSupportOnly: true;
};

export type MlReadiness = {
  ready: boolean;
  providerId: string;
  reasonCodes: string[];
  reasons: string[];
};

export type WorkflowState = {
  sessionId?: string;
  sessionCreatedAt?: string;
  backendSessionId?: string;
  backendTranscriptId?: string;
  backendTranscriptSessionId?: string;
  backendReportId?: string;
  caseId?: string;
  caseInfo: {
    caseId?: string;
    clientLabel: string;
  };
  childName: string;
  reportPeriod: string;
  source?: WorkflowSource;
  recordingStatus: "idle" | "recording" | "paused" | "stopped" | "interrupted" | "error";
  recordingSeconds: number;
  mockAudioStored: boolean;
  audioMimeType?: string;
  recordingCreatedAt?: string;
  hasUnsavedRecording: boolean;
  recordingClearedForPrivacy: boolean;
  transcriptionJobId?: string;
  transcriptionJobStatus?: TranscriptionJobStatus;
  transcriptionJobMessage?: string;
  transcriptDraftLabel?: string;
  sourceFilename?: string;
  transcriptText: string;
  transcriptLines: TranscriptLine[];
  chatMetadata: ChatMetadata;
  chatWarnings: string[];
  chatValidationIssues: string[];
  transcriptReady: boolean;
  transcriptAttested: boolean;
  transcriptCompleteness: number;
  transcriptReviewStatus: TranscriptReviewStatus;
  qaStatus: TranscriptQaStatus;
  qaSummary?: string;
  qaIssues: string[];
  transcriptSaveStatus: PersistenceStatus;
  workflowLoading: boolean;
  analysisStatus: AnalysisStatus;
  featuresExtracted: boolean;
  featurePercent: number;
  featureSummary: Array<{ label: string; value: string }>;
  featureSignals: FeatureSignal[];
  mlReadiness?: MlReadiness;
  mlDecisionSupport?: MlDecisionSupport;
  reviewNeededCount: number;
  insights: Array<{ title: string; text: string; tone: "green" | "orange" }>;
  therapistNotes: string;
  therapyGoals: string[];
  reportId?: string;
  reportStatus: "Not started" | "Draft" | "Reviewed" | "Finalized";
  reportMarkdown?: string;
  reportSaveStatus: PersistenceStatus;
  shareStatus: "Not shared" | "Local demo share link copied" | "Caregiver share recorded locally";
  finalizeStatus?: string;
  statusMessage?: string;
  error?: string;
  updatedAt?: string;
};

export type BackendCase = {
  case_id: string;
  child_code?: string;
  nickname?: string;
  consent_status?: string;
  display_label?: string;
  anonymized_child_code?: string;
  age_months?: number;
  language?: string;
  notes?: string;
  review_priority?: string;
  latest_session_date?: string;
  latest_session_status?: string;
  latest_report_status?: string;
  care_team_user_ids?: string[];
  primary_therapist_user_id?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type BackendSession = {
  session_id: string;
  case_id: string;
  session_date?: string;
  transcript_id?: string;
  feature_set_id?: string;
  report_id?: string;
  status?: string;
};

export type BackendTimelineEvent = {
  event_id: string;
  label: string;
  status: string;
  occurred_at: string;
  target_id: string;
};

export type BackendGoal = {
  goal_id: string;
  case_id: string;
  title: string;
  target?: string;
  status?: string;
  notes?: string;
};

export type BackendTranscript = {
  transcript_id: string;
  session_id?: string;
  case_id?: string;
  raw_text?: string;
  transcript_text?: string;
  review_status?: string;
  source?: string;
  therapist_attested?: boolean;
  qa_status?: string;
  qa_issues?: Array<{ message?: string } | string>;
  utterances?: Array<{
    utterance_id: string;
    speaker: string;
    text: string;
    start_ms?: number | null;
    end_ms?: number | null;
    unintelligible?: boolean;
  }>;
};

type BackendQa = {
  status?: string;
  qa_status?: string;
  quality_score?: number;
  qa_score?: number;
  summary?: string;
  issues?: string[];
  qa_issues?: string[];
};

type BackendFeatures = {
  feature_id?: string;
  schema_version?: string;
  insufficient_data?: boolean;
  features?: Record<string, string | number | boolean | null> | Array<{ name: string; value: string | number | boolean | null }>;
  core_features?: Record<string, string | number | boolean | null>;
  optional_indicators?: Record<string, string | number | boolean | null>;
};

type BackendFeatureDefinition = {
  feature_name: string;
  display_name: string;
  description: string;
  value_type: string;
  unit: string;
  calculation_method: string;
  required_inputs: string[];
  numerator_definition?: string | null;
  denominator_definition?: string | null;
  default_thresholds?: Record<string, string | number | boolean | null> | null;
  limitations: string[];
  clinical_interpretation_caution: string;
  feature_version?: string;
  provider_name?: string;
  provider_id?: string;
};

type BackendMlDecisionSupport = {
  result_id: string;
  status: "completed" | "unavailable" | "insufficient_data" | "failed";
  provider_name: string;
  provider_version: string;
  input_feature_schema_version: string;
  generated_at: string;
  cues: Array<{
    cue_code: string;
    title: string;
    severity: "info" | "review" | "caution";
    explanation: string;
    supporting_features: Record<string, string | number | boolean | null>;
    limitations: string[];
    recommended_next_review_step: string;
    review_state: { status: "unreviewed" | "acknowledged" | "dismissed" };
  }>;
  pattern_evidence?: BackendPatternEvidence | null;
  profile_evidence?: BackendProfileEvidence[];
  artifact_provenance?: Record<string, string>;
  limitations: string[];
  not_diagnostic: true;
  decision_support_only: true;
};

type BackendAvailability = {
  state: EvidenceState;
  reason_code?: string | null;
  message: string;
  workflow_can_continue: boolean;
  next_step?: string | null;
};

type BackendAssociatedFeature = {
  feature_name: string;
  observed_value: number | null;
  position: AssociatedFeatureEvidence["position"];
  q1?: number | null;
  median?: number | null;
  q3?: number | null;
  caveat: string;
};

type BackendEvidenceReviewState = {
  status: EvidenceReviewState["status"];
  therapist_note?: string;
  reviewed_by?: string | null;
  reviewed_by_name?: string | null;
  reviewed_at?: string | null;
};

type BackendPatternEvidence = {
  status: PatternEvidence["status"];
  availability: BackendAvailability;
  associated_features?: BackendAssociatedFeature[];
  review_state?: BackendEvidenceReviewState;
};

type BackendProfileEvidence = {
  profile_code: ProfileEvidence["profileCode"];
  presentation_group: ProfileEvidence["presentationGroup"];
  status: ProfileEvidence["status"];
  availability: BackendAvailability;
  participant_count: number;
  corpus_count: number;
  associated_features?: BackendAssociatedFeature[];
  review_state?: BackendEvidenceReviewState;
};

export type ReportSection = {
  section_id: string;
  title: string;
  content: string;
  not_diagnostic?: boolean;
  decision_support_only?: boolean;
};

export type ReportSafetyIssue = {
  issue_id: string;
  code: string;
  severity: "warning" | "error";
  message: string;
  section_id?: string;
  detected_text?: string;
  normalized_detected_text?: string;
  start_offset?: number;
  end_offset?: number;
  suggested_fix?: string;
  suggested_replacement?: string;
  blocking?: boolean;
  source: "generation" | "edit" | "finalization";
  rule_id?: string;
};

export type ReportSafetyResult = {
  status: "passed" | "warning" | "failed";
  validator_version: string;
  rule_set_version: string;
  checked_at: string;
  issues: ReportSafetyIssue[];
  required_disclaimers_present: boolean;
  missing_required_disclaimers: string[];
  prohibited_claims_found: boolean;
  prohibited_phrases_found: string[];
  checked_sections: string[];
  action_required?: string;
  finalization_blocked: boolean;
};

export type BackendReport = {
  report_id?: string;
  session_id?: string;
  case_id?: string;
  report_type?: string;
  title?: string;
  markdown?: string;
  html?: string;
  status?: string;
  therapist_signoff_status?: string;
  limitation_text?: string;
  export_timestamp?: string;
  created_at?: string;
  updated_at?: string;
  content_markdown?: string;

  // v1.0 metadata
  requested_provider?: string;
  actual_provider?: string;
  provider_version?: string;
  fallback_reason?: string;
  rewrite_attempted?: boolean;
  rewrite_succeeded?: boolean;
  safety_validation_result?: ReportSafetyResult;
  finalized_safety_result?: ReportSafetyResult;
  finalization_blocked?: boolean;
  validator_version?: string;
  rule_set_version?: string;
  input_hash?: string;
  version?: number;

  // input trace
  transcript_id?: string;
  feature_result_id?: string;
  ml_result_id?: string;
  ml_skipped_reason?: string;
  validation_summary?: string;
  feature_schema_version?: string;
  therapist_notes?: string;
  session_goals?: string[];
  generated_from_versions?: Record<string, string>;
  sections?: ReportSection[];
};

export type OrganizationMembership = {
  membership_id: string;
  organization_id: string;
  user_id: string;
  display_name: string;
  role: string;
  active: boolean;
  created_at?: string;
};

export type OrganizationInvitation = {
  invitation_id: string;
  organization_id: string;
  email: string;
  display_name: string;
  role: string;
  status: "pending" | "accepted" | "expired" | "revoked";
  invited_by: string;
  accepted_user_id?: string | null;
  expires_at: string;
  created_at?: string;
  accepted_at?: string | null;
};

export type CareTeamAssignment = {
  assignment_id: string;
  organization_id: string;
  case_id: string;
  user_id: string;
  role: string;
  active: boolean;
  is_primary: boolean;
  created_at?: string;
};

export const defaultTranscript = [
  "@Begin",
  "@Languages:\teng",
  "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
  "*THER:\tWhat do you see?",
  "*CHI:\tI see a big blue block.",
  "*THER:\tWhat color is it?",
  "*CHI:\tIt is blue.",
  "*THER:\tCan you ask me a question?",
  "*CHI:\tWhat color do you like?",
  "@End"
].join("\n");

export function createInitialWorkflowState(): WorkflowState {
  return {
    caseInfo: {
      clientLabel: "Ethan L."
    },
    childName: "Ethan L.",
    reportPeriod: "May 1 - May 13, 2026",
    recordingStatus: "idle",
    recordingSeconds: 0,
    mockAudioStored: false,
    hasUnsavedRecording: false,
    recordingClearedForPrivacy: false,
    transcriptText: defaultTranscript,
    transcriptLines: [],
    chatMetadata: createDefaultChatMetadata(),
    chatWarnings: [],
    chatValidationIssues: [],
    transcriptReady: false,
    transcriptAttested: false,
    transcriptCompleteness: 0,
    transcriptReviewStatus: "not_started",
    qaStatus: "not_run",
    qaIssues: [],
    transcriptSaveStatus: "idle",
    workflowLoading: false,
    analysisStatus: "not_started",
    featuresExtracted: false,
    featurePercent: 0,
    featureSummary: [],
    featureSignals: [],
    reviewNeededCount: 0,
    insights: [
      { title: "Transcript review required", text: "Review speaker labels and transcript quality before report use.", tone: "orange" }
    ],
    therapistNotes: "",
    therapyGoals: [],
    reportStatus: "Not started"
    ,
    reportSaveStatus: "idle",
    shareStatus: "Not shared"
  };
}

export async function generateBackendMlDecisionSupport(transcriptId: string): Promise<MlDecisionSupport> {
  const result = await apiRequest<BackendMlDecisionSupport>(`/transcripts/${transcriptId}/ml-review`, {
    method: "POST",
    body: JSON.stringify({ provider_id: "reference_evidence_review" })
  });
  return normalizeMlResult(result);
}

export async function getBackendMlDecisionSupport(sessionId: string): Promise<MlDecisionSupport> {
  return normalizeMlResult(await apiGet<BackendMlDecisionSupport>(`/sessions/${sessionId}/ml-review`));
}

export async function updateProfileEvidenceReview(
  resultId: string,
  profileCode: ProfileEvidence["profileCode"],
  status: "reviewed" | "disagreement",
  therapistNote = ""
): Promise<MlDecisionSupport> {
  const result = await apiRequest<BackendMlDecisionSupport>(
    `/ml-results/${resultId}/profiles/${profileCode}/review-state`,
    {
      method: "PATCH",
      body: JSON.stringify({
        status,
        therapist_note: therapistNote
      })
    }
  );
  return normalizeMlResult(result);
}

export async function getBackendMlReadiness(transcriptId: string): Promise<MlReadiness> {
  const result = await apiGet<{
    ready: boolean;
    provider_id: string;
    reason_codes: string[];
    reasons: string[];
  }>(`/transcripts/${transcriptId}/ml-readiness?provider_id=reference_evidence_review`);
  return {
    ready: result.ready,
    providerId: result.provider_id,
    reasonCodes: result.reason_codes,
    reasons: result.reasons
  };
}

function normalizeMlResult(result: BackendMlDecisionSupport): MlDecisionSupport {
  if (!result || !result.result_id) {
    return {
      resultId: "",
      status: "completed",
      providerName: "",
      providerVersion: "",
      featureSchemaVersion: "",
      generatedAt: "",
      cues: [],
      profileEvidence: [],
      artifactProvenance: {},
      limitations: [],
      notDiagnostic: true,
      decisionSupportOnly: true
    };
  }

  const normalizeAvailability = (availability: BackendAvailability): EvidenceAvailability => ({
    state: availability.state,
    reasonCode: availability.reason_code ?? undefined,
    message: availability.message,
    workflowCanContinue: availability.workflow_can_continue,
    nextStep: availability.next_step ?? undefined
  });
  const normalizeFeature = (feature: BackendAssociatedFeature): AssociatedFeatureEvidence => ({
    featureName: feature.feature_name,
    observedValue: feature.observed_value,
    position: feature.position,
    q1: feature.q1,
    median: feature.median,
    q3: feature.q3,
    caveat: feature.caveat
  });
  const normalizeReviewState = (review?: BackendEvidenceReviewState): EvidenceReviewState => ({
    status: review?.status ?? "unreviewed",
    therapistNote: review?.therapist_note ?? "",
    reviewedBy: review?.reviewed_by ?? undefined,
    reviewedByName: review?.reviewed_by_name ?? undefined,
    reviewedAt: review?.reviewed_at ?? undefined
  });
  return {
    resultId: result.result_id,
    status: result.status,
    providerName: result.provider_name,
    providerVersion: result.provider_version,
    featureSchemaVersion: result.input_feature_schema_version,
    generatedAt: result.generated_at,
    cues: result.cues.map((cue) => ({
      cueCode: cue.cue_code,
      title: cue.title,
      severity: cue.severity,
      explanation: cue.explanation,
      supportingFeatures: cue.supporting_features,
      limitations: cue.limitations,
      recommendedNextReviewStep: cue.recommended_next_review_step,
      reviewStatus: cue.review_state.status
    })),
    patternEvidence: result.pattern_evidence ? {
      status: result.pattern_evidence.status,
      availability: normalizeAvailability(result.pattern_evidence.availability),
      associatedFeatures: (result.pattern_evidence.associated_features ?? []).map(normalizeFeature),
      reviewState: normalizeReviewState(result.pattern_evidence.review_state)
    } : undefined,
    profileEvidence: (result.profile_evidence ?? []).map((profile) => ({
      profileCode: profile.profile_code,
      presentationGroup: profile.presentation_group,
      status: profile.status,
      availability: normalizeAvailability(profile.availability),
      participantCount: profile.participant_count,
      corpusCount: profile.corpus_count,
      associatedFeatures: (profile.associated_features ?? []).map(normalizeFeature),
      reviewState: normalizeReviewState(profile.review_state)
    })),
    artifactProvenance: result.artifact_provenance ?? {},
    limitations: result.limitations,
    notDiagnostic: result.not_diagnostic,
    decisionSupportOnly: result.decision_support_only
  };
}

export function loadWorkflowState(): WorkflowState {
  if (typeof window === "undefined") {
    return createInitialWorkflowState();
  }
  const stored = window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY);
  if (!stored) {
    return createInitialWorkflowState();
  }
  try {
    const parsed = JSON.parse(stored) as Partial<WorkflowState>;
    const initial = createInitialWorkflowState();
    const lostUnsavedRecording = parsed.hasUnsavedRecording === true;
    return {
      ...initial,
      ...parsed,
      mlDecisionSupport: undefined,
      recordingStatus: lostUnsavedRecording ? "idle" : parsed.recordingStatus ?? initial.recordingStatus,
      hasUnsavedRecording: false,
      recordingClearedForPrivacy: lostUnsavedRecording,
      caseInfo: {
        ...initial.caseInfo,
        ...parsed.caseInfo,
        caseId: parsed.caseInfo?.caseId ?? parsed.caseId,
        clientLabel: parsed.caseInfo?.clientLabel ?? parsed.childName ?? initial.childName
      }
    };
  } catch {
    return createInitialWorkflowState();
  }
}

export function saveWorkflowState(state: WorkflowState): WorkflowState {
  const next = { ...state, updatedAt: new Date().toISOString() };
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(WORKFLOW_STORAGE_KEY, JSON.stringify(next, (_key, value) => (
      value instanceof Blob ? undefined : value
    )));
  }
  return next;
}

export function ensureWorkflowSession(
  state: WorkflowState,
  source: WorkflowSource,
  overrides: Partial<WorkflowState> = {}
): WorkflowState {
  const shouldCreate = !state.sessionId || state.reportStatus === "Finalized";
  const now = new Date().toISOString();
  const sessionId = shouldCreate ? createLocalSessionId() : state.sessionId;
  const caseId = overrides.caseId ?? state.caseId ?? state.caseInfo.caseId;
  const childName = overrides.childName ?? state.childName;

  return {
    ...(shouldCreate ? createInitialWorkflowState() : state),
    ...overrides,
    sessionId,
    sessionCreatedAt: shouldCreate ? now : state.sessionCreatedAt ?? now,
    caseId,
    caseInfo: {
      caseId,
      clientLabel: childName
    },
    childName,
    source
  };
}

export function prepareTranscriptIntake(
  source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">,
  input: string
): ChatParseResult {
  return source === "cha-upload" ? parseChaTranscript(input) : parsePastedTranscript(input);
}

export function serializeTranscriptLines(lines: TranscriptLine[]): string {
  return buildBasicChatExport({
    lines,
    metadata: createDefaultChatMetadata()
  }).trimEnd();
}

export function evaluateTranscriptQa(
  lines: TranscriptLine[],
  metadata?: ChatMetadata,
  importValidationIssues: string[] = []
): {
  status: TranscriptQaStatus;
  issues: string[];
  summary: string;
} {
  const issues: string[] = [];
  const childCount = lines.filter((line) => line.speaker === "CHI").length;
  const unknownCount = lines.filter((line) => line.speaker === "UNK").length;
  const unclearCount = lines.filter((line) => line.unclear || /\b(?:xxx|yyy|www|\[unclear\])\b/i.test(line.text)).length;
  const emptyCount = lines.filter((line) => !line.text.trim()).length;
  const declaredSpeakers = new Set(metadata?.participants.map((participant) => participant.code) ?? []);

  if (lines.length === 0) issues.push("Transcript has no utterance lines.");
  if (emptyCount > 0) issues.push(`${emptyCount} transcript line${emptyCount === 1 ? " is" : "s are"} empty.`);
  if (childCount === 0) issues.push("No child speaker lines are marked CHI.");
  if (childCount > 0 && childCount < 3) issues.push("Child sample has fewer than 3 utterances.");
  if (unknownCount / Math.max(lines.length, 1) > 0.25) issues.push("More than 25% of utterances have unknown speaker labels.");
  if (unclearCount / Math.max(lines.length, 1) > 0.2) issues.push("More than 20% of utterances are marked unclear.");
  if (metadata && metadata.participants.length === 0) issues.push("Missing @Participants header.");
  if (metadata && metadata.languages.length === 0) issues.push("Missing @Languages header.");
  if (metadata && declaredSpeakers.size > 0) {
    for (const speaker of new Set(lines.map((line) => line.speaker))) {
      if (!declaredSpeakers.has(speaker)) issues.push(`Speaker ${speaker} is not declared in @Participants.`);
    }
  }
  for (const issue of importValidationIssues) {
    if (!issues.includes(issue)) issues.push(issue);
  }

  const status: TranscriptQaStatus = lines.length === 0 || emptyCount > 0 || childCount === 0
    ? "fail"
    : issues.length > 0
      ? "warning"
      : "pass";
  return {
    status,
    issues,
    summary: status === "pass" ? "Transcript QA completed with no flagged issues." : `Transcript QA completed with ${issues.length} review item${issues.length === 1 ? "" : "s"}.`
  };
}

export function extractLanguageSampleFeatures(
  lines: TranscriptLine[],
  metadata: ChatMetadata = createDefaultChatMetadata()
): LanguageSampleFeatures {
  const childLines = lines.filter((line) => line.speaker.toUpperCase() === "CHI");
  const declaredAdults = new Set(
    metadata.participants
      .filter((participant) => participant.code.toUpperCase() !== "CHI" && participant.code.toUpperCase() !== "UNK")
      .map((participant) => participant.code.toUpperCase())
  );
  const adultLines = lines.filter((line) => {
    const speaker = line.speaker.toUpperCase();
    if (speaker === "CHI" || speaker === "UNK") return false;
    return declaredAdults.size === 0 || declaredAdults.has(speaker);
  });
  const childTokens = childLines.flatMap((line) => tokenizeLanguageSample(line.text));
  const uniqueChildTokens = new Set(childTokens);
  const unclearCount = lines.filter((line) => (
    line.unclear || /\b(?:xxx|yyy|www|\[unclear\])\b/iu.test(line.text)
  )).length;
  const repetitionCue = childLines.reduce((count, line) => (
    count
    + (line.text.match(/\[\/\]/gu)?.length ?? 0)
    + (line.text.match(/\b([\p{L}\p{N}']+)\s+\1\b/giu)?.length ?? 0)
  ), 0);
  let previousAdult = "";
  let echolaliaCue = 0;
  for (const line of lines) {
    const normalized = normalizeCueText(line.text);
    if (line.speaker.toUpperCase() === "CHI") {
      if (previousAdult && normalized && normalized === previousAdult) echolaliaCue += 1;
    } else if (line.speaker.toUpperCase() !== "UNK") {
      previousAdult = normalized;
    }
  }
  const pronounReversalCue = childLines.reduce((count, line) => (
    count + (line.text.match(/\b(?:you am|me am|my want|i are)\b/giu)?.length ?? 0)
  ), 0);

  return {
    totalUtterances: lines.length,
    childUtterances: childLines.length,
    adultUtterances: adultLines.length,
    totalWords: childTokens.length,
    mluWords: roundFeature(childLines.length ? childTokens.length / childLines.length : 0),
    ndw: uniqueChildTokens.size,
    ttr: roundFeature(childTokens.length ? uniqueChildTokens.size / childTokens.length : 0),
    questionRatio: roundFeature(childLines.length ? childLines.filter((line) => line.text.includes("?")).length / childLines.length : 0),
    unclearRatio: roundFeature(lines.length ? unclearCount / lines.length : 0),
    repetitionCue,
    echolaliaCue,
    pronounReversalCue
  };
}

export function languageSampleFeatureSummary(features: LanguageSampleFeatures): WorkflowState["featureSummary"] {
  return [
    { label: "Total utterances", value: String(features.totalUtterances) },
    { label: "Child utterances", value: String(features.childUtterances) },
    { label: "Adult utterances", value: String(features.adultUtterances) },
    { label: "Total words", value: String(features.totalWords) },
    { label: "MLU words", value: formatFeatureNumber(features.mluWords) },
    { label: "NDW", value: String(features.ndw) },
    { label: "TTR", value: formatFeatureNumber(features.ttr) },
    { label: "Question ratio", value: formatFeatureRatio(features.questionRatio) },
    { label: "Unclear / unintelligible ratio", value: formatFeatureRatio(features.unclearRatio) },
    { label: "Repetition cue", value: String(features.repetitionCue) },
    { label: "Echolalia cue", value: String(features.echolaliaCue) },
    { label: "Pronoun reversal cue", value: String(features.pronounReversalCue) }
  ];
}

export function parseChaTranscript(input: string): ChatParseResult {
  const normalized = normalizeLineEndings(input).trim();
  const sourceLines = normalized.split("\n");
  const hasBegin = sourceLines.some((line) => line.trim() === "@Begin");
  const hasEnd = sourceLines.some((line) => line.trim() === "@End");

  if (!hasBegin || !hasEnd || !sourceLines.some((line) => line.trim().startsWith("*"))) {
    throw new Error("Invalid .cha file: expected @Begin, @End, and at least one speaker line such as *CHI:.");
  }

  const metadata = parseChatMetadata(sourceLines);
  const warnings: string[] = [];
  const validationIssues: string[] = [];
  const transcriptLines: TranscriptLine[] = [];
  const declaredSpeakers = new Set(metadata.participants.map((participant) => participant.code));

  if (metadata.participants.length === 0) {
    validationIssues.push("Missing @Participants header.");
  }

  sourceLines.forEach((rawLine, index) => {
    const trimmed = rawLine.trim();
    if (!trimmed || trimmed === "@Begin" || trimmed === "@End" || trimmed === "@UTF8") return;
    if (trimmed.startsWith("@")) return;
    if (trimmed.startsWith("%")) {
      const tier = trimmed.match(/^(%[^:\s]+):/)?.[1] ?? trimmed.split(/\s/, 1)[0];
      const warning = `Unsupported dependent tier ${tier} was not imported.`;
      if (!warnings.includes(warning)) warnings.push(warning);
      return;
    }

    const speakerMatch = rawLine.match(/^\*([A-Za-z0-9_]{1,8}):\s*(.*)$/);
    if (speakerMatch) {
      const speaker = speakerMatch[1].toUpperCase();
      const parsed = parseTimestamp(speakerMatch[2]);
      transcriptLines.push({
        lineId: `line-${transcriptLines.length + 1}`,
        speaker,
        text: parsed.text,
        ...(parsed.startMs !== undefined ? { startMs: parsed.startMs, endMs: parsed.endMs } : {})
      });
      if (!parsed.text) {
        validationIssues.push(`Line ${index + 1} has an empty utterance.`);
      }
      if (!declaredSpeakers.has(speaker)) {
        validationIssues.push(`Speaker ${speaker} is not declared in @Participants.`);
      }
      return;
    }

    if (/^\s+/.test(rawLine) && transcriptLines.length > 0) {
      const previous = transcriptLines[transcriptLines.length - 1];
      const parsed = parseTimestamp(trimmed);
      transcriptLines[transcriptLines.length - 1] = {
        ...previous,
        text: `${previous.text} ${parsed.text}`.trim(),
        ...(parsed.startMs !== undefined ? { startMs: parsed.startMs, endMs: parsed.endMs } : {})
      };
      return;
    }

    validationIssues.push(`Line ${index + 1} is malformed and was not imported.`);
  });

  return {
    transcriptText: normalized,
    transcriptLines,
    metadata,
    warnings,
    validationIssues
  };
}

export function parsePastedTranscript(input: string): ChatParseResult {
  const normalized = normalizeLineEndings(input).trim();
  if (!normalized) {
    throw new Error("Paste transcript text before saving.");
  }

  if (normalized.includes("@Begin") || normalized.split("\n").some((line) => /^\*[A-Za-z0-9_]+:/.test(line))) {
    return parseChaTranscript(normalized);
  }

  const transcriptLines = normalized
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const labelled = line.match(/^([^:]{1,40}):\s*(.+)$/);
      const speaker = labelled ? normalizeSpeakerLabel(labelled[1]) : "UNK";
      const parsed = parseTimestamp(labelled ? labelled[2] : line);
      return {
        lineId: `line-${index + 1}`,
        speaker,
        text: parsed.text,
        ...(parsed.startMs !== undefined ? { startMs: parsed.startMs, endMs: parsed.endMs } : {})
      };
    })
    .filter((line) => line.text);

  if (transcriptLines.length === 0) {
    throw new Error("Paste transcript text with at least one speaker line.");
  }

  const speakers = [...new Set(transcriptLines.map((line) => line.speaker))];
  const participantText = speakers.map((speaker) => `${speaker} ${speaker}`).join(", ");
  const speakerTiers = transcriptLines.map((line) => {
    const timestamp = line.startMs !== undefined && line.endMs !== undefined
      ? ` \u0015${line.startMs}_${line.endMs}\u0015`
      : "";
    return `*${line.speaker}:\t${line.text}${timestamp}`;
  });

  const transcriptText = [
      "@Begin",
      "@Languages:\teng",
      `@Participants:\t${participantText}`,
      ...speakerTiers,
      "@End"
    ].join("\n");
  return parseChaTranscript(transcriptText);
}

export function buildBasicChatExport({
  lines,
  metadata,
  includeMedia = false,
  fallbackMediaName,
  allowInvalid = false
}: {
  lines: TranscriptLine[];
  metadata: ChatMetadata;
  includeMedia?: boolean;
  fallbackMediaName?: string;
  allowInvalid?: boolean;
}): string {
  const emptyLine = lines.findIndex((line) => !line.text.trim());
  if (!allowInvalid && emptyLine >= 0) throw new Error(`Line ${emptyLine + 1} has an empty utterance.`);
  const unknownLine = lines.findIndex((line) => !isValidSpeakerCode(line.speaker) || line.speaker === "UNK");
  if (!allowInvalid && unknownLine >= 0) throw new Error(`Line ${unknownLine + 1} has an unknown speaker.`);

  const languages = metadata.languages.length > 0 ? metadata.languages : ["eng"];
  const speakerCodes = [...new Set(lines.map((line) => line.speaker.toUpperCase()))];
  const participants = speakerCodes.map((code) => (
    metadata.participants.find((participant) => participant.code === code) ?? defaultParticipant(code)
  ));
  const existingIds = new Map(metadata.ids.map((id) => [id.code, id.raw]));
  const primaryLanguage = languages[0] || "eng";
  const media = metadata.media ?? (fallbackMediaName ? { name: fallbackMediaName, type: "audio" } : undefined);
  const output = [
    "@UTF8",
    "@Begin",
    `@Languages:\t${languages.join(", ")}`,
    `@Participants:\t${participants.map((participant) => `${participant.code} ${participant.name} ${participant.role}`).join(", ")}`,
    ...participants.map((participant) => (
      `@ID:\t${existingIds.get(participant.code) ?? `${primaryLanguage}|TherapistAppV2|${participant.code}|||||${participant.role}|||`}`
    )),
    ...(includeMedia && media ? [`@Media:\t${sanitizeMediaName(media.name)}, ${media.type || "audio"}`] : []),
    ...lines.map(renderChatSpeakerLine),
    "@End",
    ""
  ];
  return output.join("\n");
}

export async function getUsableCase(): Promise<BackendCase> {
  const cases = await apiGet<BackendCase[]>("/cases");
  const granted = cases.find((item) => item.consent_status === "granted");
  if (granted ?? cases[0]) {
    return granted ?? cases[0];
  }
  return apiRequest<BackendCase>("/cases", {
    method: "POST",
    body: JSON.stringify({
      child_code: `DEMO-${Date.now().toString().slice(-5)}`,
      nickname: "Demo child",
      age_months: 62,
      language: "English",
      consent_status: "granted",
      notes: "Local demo case; do not use real child data."
    })
  });
}

export async function createBackendSession(source: WorkflowSource): Promise<BackendSession> {
  const childCase = await getUsableCase();
  const session = await apiRequest<BackendSession>(`/cases/${childCase.case_id}/sessions`, {
    method: "POST",
    body: JSON.stringify({
      session_date: new Date().toISOString().slice(0, 10),
      session_type: "therapy_session",
      notes: `Simplified therapist workflow: ${source}. Audio/ASR remains experimental unless separately processed.`
    })
  });
  return session;
}

export async function getBackendCase(caseId: string): Promise<BackendCase> {
  return apiGet<BackendCase>(`/cases/${caseId}`);
}

export async function listBackendCases(): Promise<BackendCase[]> {
  return apiGet<BackendCase[]>("/cases");
}

export async function getBackendCaseTimeline(caseId: string): Promise<BackendTimelineEvent[]> {
  return apiGet<BackendTimelineEvent[]>(`/cases/${caseId}/timeline`);
}

export async function listBackendCaseGoals(caseId: string): Promise<BackendGoal[]> {
  return apiGet<BackendGoal[]>(`/cases/${caseId}/goals`);
}

export async function getBackendSession(sessionId: string): Promise<BackendSession> {
  return apiGet<BackendSession>(`/sessions/${sessionId}`);
}

export async function getBackendSessionFeatures(sessionId: string): Promise<BackendFeatures> {
  return apiGet<BackendFeatures>(`/sessions/${sessionId}/features`);
}

export async function getBackendFeatureDefinitions(): Promise<FeatureDefinition[]> {
  const definitions = await apiGet<BackendFeatureDefinition[]>("/features/definitions");
  return definitions.map((definition) => ({
    featureName: definition.feature_name,
    displayName: definition.display_name,
    description: definition.description,
    valueType: definition.value_type,
    unit: definition.unit,
    calculationMethod: definition.calculation_method,
    requiredInputs: definition.required_inputs,
    numeratorDefinition: definition.numerator_definition,
    denominatorDefinition: definition.denominator_definition,
    defaultThresholds: definition.default_thresholds,
    limitations: definition.limitations,
    clinicalInterpretationCaution: definition.clinical_interpretation_caution,
    featureVersion: definition.feature_version,
    providerName: definition.provider_name,
    providerId: definition.provider_id
  }));
}

export async function getBackendTranscript(transcriptId: string): Promise<BackendTranscript> {
  return apiGet<BackendTranscript>(`/transcripts/${transcriptId}`);
}

export async function getBackendSessionTranscript(sessionId: string): Promise<BackendTranscript> {
  return apiGet<BackendTranscript>(`/sessions/${sessionId}/transcript`);
}

export async function getBackendReport(reportId: string): Promise<BackendReport> {
  return apiGet<BackendReport>(`/reports/${reportId}`);
}

export async function listBackendReports(): Promise<BackendReport[]> {
  return apiGet<BackendReport[]>("/reports");
}

export async function listOrganizationMemberships(): Promise<OrganizationMembership[]> {
  return apiRequest<OrganizationMembership[]>("/organizations/current/memberships", {
    headers: getMockAccessHeaders()
  });
}

export async function listOrganizationInvitations(): Promise<OrganizationInvitation[]> {
  return apiRequest<OrganizationInvitation[]>("/organizations/current/invitations", {
    headers: getMockAccessHeaders()
  });
}

export async function createOrganizationInvitation(payload: {
  email: string;
  display_name: string;
  role: string;
}): Promise<OrganizationInvitation> {
  return apiRequest<OrganizationInvitation>("/organizations/current/invitations", {
    method: "POST",
    headers: getMockAccessHeaders(),
    body: JSON.stringify(payload)
  });
}

export async function acceptOrganizationInvitation(
  invitationId: string,
  payload: {
    user_id: string;
  }
): Promise<OrganizationInvitation> {
  return apiRequest<OrganizationInvitation>(`/organizations/current/invitations/${invitationId}/accept`, {
    method: "POST",
    headers: getMockAccessHeaders(),
    body: JSON.stringify(payload)
  });
}

export async function revokeOrganizationMembership(membershipId: string): Promise<OrganizationMembership> {
  return apiRequest<OrganizationMembership>(`/organizations/current/memberships/${membershipId}/revoke`, {
    method: "POST",
    headers: getMockAccessHeaders()
  });
}

export async function listCaseCareTeamAssignments(caseId: string): Promise<CareTeamAssignment[]> {
  return apiRequest<CareTeamAssignment[]>(`/cases/${caseId}/care-team`, {
    headers: getMockAccessHeaders()
  });
}

export async function assignCaseCareTeamMember(
  caseId: string,
  payload: {
    user_id: string;
    role: string;
    active?: boolean;
    is_primary?: boolean;
  }
): Promise<CareTeamAssignment> {
  return apiRequest<CareTeamAssignment>(`/cases/${caseId}/care-team`, {
    method: "POST",
    headers: getMockAccessHeaders(),
    body: JSON.stringify({
      user_id: payload.user_id,
      role: payload.role,
      active: payload.active ?? true,
      is_primary: payload.is_primary ?? false,
    })
  });
}

export function backendTranscriptLines(transcript: BackendTranscript): TranscriptLine[] {
  return (transcript.utterances ?? []).map((utterance) => ({
    lineId: utterance.utterance_id,
    speaker: String(utterance.speaker),
    text: utterance.text,
    ...(utterance.start_ms == null ? {} : { startMs: utterance.start_ms }),
    ...(utterance.end_ms == null ? {} : { endMs: utterance.end_ms }),
    unclear: Boolean(utterance.unintelligible)
  }));
}

export async function createBackendTranscript(
  sessionId: string,
  source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">,
  sourceText: string,
  transcriptText: string,
  filename?: string
): Promise<BackendTranscript> {
  if (source === "cha-upload") {
    return apiRequest<BackendTranscript>(`/sessions/${sessionId}/transcripts/upload-cha`, {
      method: "POST",
      body: JSON.stringify({
        filename: filename || "transcript.cha",
        cha_text: transcriptText
      })
    });
  }
  return apiRequest<BackendTranscript>(`/sessions/${sessionId}/transcripts/manual`, {
    method: "POST",
    body: JSON.stringify({
      text: sourceText,
      language: "English"
    })
  });
}

export async function updateBackendTranscript(
  transcriptId: string,
  transcriptText: string,
  reviewerNote: string
): Promise<BackendTranscript> {
  return apiRequest<BackendTranscript>(`/transcripts/${transcriptId}`, {
    method: "PATCH",
    body: JSON.stringify({
      raw_text: transcriptText,
      reviewer_note: reviewerNote
    })
  });
}

export async function runBackendQa(transcriptId: string): Promise<BackendQa> {
  const response = await apiRequest<{
    overall_status: string;
    issues: any[];
    transcript_id: string;
  }>(`/transcripts/${transcriptId}/qa`, { method: "POST" });

  const status = normalizeQaStatus(response.overall_status);
  const issues = response.issues.map((issue) => typeof issue === "string" ? issue : issue?.message ?? "Transcript QA issue");
  const summary = issues.length > 0
    ? `QA detected ${issues.length} issue(s): ${issues.join("; ")}`
    : "Transcript QA completed successfully.";

  return {
    status,
    qa_status: status,
    issues,
    summary
  };
}

export async function attestBackendTranscript(transcriptId: string): Promise<void> {
  await apiText(`/transcripts/${transcriptId}/attest`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      attested_by: "Demo Therapist",
      reason: "Therapist attested transcript quality after transcript QA.",
      override_qa_failure: false
    })
  });
}

export async function runBackendAnalysis(
  sessionId: string,
  transcriptId?: string,
  qa: BackendQa = { status: "pass", summary: "Transcript QA and therapist attestation completed." }
): Promise<Pick<WorkflowState, "qaStatus" | "qaSummary" | "transcriptAttested" | "transcriptCompleteness" | "featuresExtracted" | "featurePercent" | "featureSummary" | "reviewNeededCount" | "insights">> {
  let features: BackendFeatures;
  try {
    const extractionPath = transcriptId
      ? `/transcripts/${transcriptId}/extract-features`
      : `/sessions/${sessionId}/features/extract`;
    features = await apiRequest<BackendFeatures>(extractionPath, { method: "POST" });
  } catch (error) {
    if (!(error instanceof ApiError)) {
      throw error;
    }
    features = await apiGet<BackendFeatures>(`/sessions/${sessionId}/features`);
  }
  return summarizeAnalysis(qa, features);
}

export async function generateBackendReport(
  sessionId: string,
  providerId: string = "template",
  allowFallback: boolean = false,
  therapistNotes?: string,
  sessionGoals: string[] = []
): Promise<BackendReport> {
  const report = await apiRequest<any>(`/sessions/${sessionId}/reports/draft`, {
    method: "POST",
    body: JSON.stringify({
      provider_id: providerId,
      allow_fallback_to_template: allowFallback,
      therapist_notes: therapistNotes,
      session_goals: sessionGoals
    })
  });
  return {
    ...report,
    content_markdown: report.markdown
  };
}

export async function updateBackendReport(reportId: string, markdown: string, therapistNotes: string): Promise<BackendReport> {
  return apiRequest<BackendReport>(`/reports/${reportId}`, {
    method: "PATCH",
    body: JSON.stringify({ markdown, therapist_notes: therapistNotes })
  });
}

export async function finalizeBackendReport(
  reportId: string,
  confirmationChecked: boolean = false,
  finalNotes?: string
): Promise<BackendReport> {
  return apiRequest<BackendReport>(`/reports/${reportId}/sign-off`, {
    method: "POST",
    body: JSON.stringify({
      confirmation_checked: confirmationChecked,
      final_notes: finalNotes,
      attestation: "I reviewed and accept responsibility for this report."
    })
  });
}

export async function exportBackendReport(reportId: string, format: "markdown" | "html"): Promise<{
  filename: string;
  content: string;
  content_type: string;
}> {
  return apiGet(`/reports/${reportId}/export?format=${format}`);
}

export async function exportReviewedCha(transcriptId: string): Promise<{
  filename: string;
  cha_text: string;
}> {
  return apiGet(`/transcripts/${transcriptId}/export-cha`);
}

export function buildFeatureSignals(
  backendFeatures?: BackendFeatures,
  definitions: FeatureDefinition[] = []
): FeatureSignal[] {
  if (!backendFeatures) return [];

  const definitionMap = new Map(definitions.map((definition) => [definition.featureName, definition]));
  const arrayValues = Array.isArray(backendFeatures.features) ? backendFeatures.features : [];
  const objectValues = Array.isArray(backendFeatures.features) ? {} : backendFeatures.features ?? {};
  const mergedValues = [
    ...arrayValues,
    ...Object.entries({
      ...objectValues,
      ...(backendFeatures.core_features ?? {}),
      ...(backendFeatures.optional_indicators ?? {})
    }).map(([name, value]) => ({ name, value }))
  ];
  const seen = new Set<string>();

  return mergedValues
    .filter((feature) => {
      if (seen.has(feature.name)) return false;
      seen.add(feature.name);
      return true;
    })
    .map((feature) => {
      const definition = definitionMap.get(feature.name);
      return {
        featureName: feature.name,
        displayName: definition?.displayName ?? featureLabelFromName(feature.name),
        description: definition?.description ?? "Descriptive language-sample feature.",
        valueType: definition?.valueType ?? inferValueType(feature.value),
        unit: definition?.unit ?? "",
        value: formatSignalValue(feature.value, definition?.valueType),
        rawValue: feature.value,
        calculationMethod: definition?.calculationMethod ?? "Backend-derived feature value.",
        requiredInputs: definition?.requiredInputs ?? [],
        limitations: definition?.limitations ?? [],
        clinicalInterpretationCaution: definition?.clinicalInterpretationCaution ?? "Therapist interpretation required.",
        interpretationHint: "Therapist-editable descriptive draft. Do not treat as a diagnosis or final conclusion.",
        referenceText: hasReferenceThresholds(definition)
          ? "Reference details available in the backend definition catalog."
          : "Reference comparison unavailable"
      };
    });
}

export function summarizeAnalysis(qa: BackendQa, backendFeatures?: BackendFeatures): Pick<WorkflowState, "qaStatus" | "qaSummary" | "transcriptAttested" | "transcriptCompleteness" | "featuresExtracted" | "featurePercent" | "featureSummary" | "reviewNeededCount" | "insights"> {
  const score = Number(qa.quality_score ?? qa.qa_score ?? 0.92);
  const issues = qa.issues ?? qa.qa_issues ?? [];
  const directFeatures = Array.isArray(backendFeatures?.features)
    ? Object.fromEntries(backendFeatures.features.map((item) => [item.name, item.value]))
    : backendFeatures?.features ?? {};
  const features = {
    ...directFeatures,
    ...(backendFeatures?.core_features ?? {}),
    ...(backendFeatures?.optional_indicators ?? {})
  };
  const mlu = pickFeature(features, ["mlu_words", "mean_length_of_utterance_words", "mean_length_utterance_words"], "3.2");
  const ndw = pickFeature(features, ["ndw", "number_of_different_words"], "78");
  const questionRatio = pickFeature(features, ["question_ratio", "reciprocal_question_ratio"], "6%");
  const featureSummary = [
    { label: "MLU words", value: String(mlu) },
    { label: "Different words", value: String(ndw) },
    { label: "Question ratio", value: String(questionRatio) }
  ];
  const reviewNeededCount = Math.max(issues.length, score < 0.9 ? 1 : 0);
  return {
    qaStatus: normalizeQaStatus(qa.status ?? qa.qa_status),
    qaSummary: qa.summary ?? "Transcript QA completed. Therapist review remains required before final report use.",
    transcriptAttested: true,
    transcriptCompleteness: Math.round(Math.max(0, Math.min(1, score)) * 100),
    featuresExtracted: Boolean(backendFeatures),
    featurePercent: Boolean(backendFeatures) ? 88 : 72,
    featureSummary,
    reviewNeededCount,
    insights: [
      { title: "Transcript ready for review", text: "Transcript QA ran and therapist attestation was recorded for this workflow.", tone: "green" },
      { title: "Feature summary available", text: "Language feature values are available for therapist interpretation.", tone: "green" },
      {
        title: reviewNeededCount > 0 ? "Review item present" : "Review before report",
        text: reviewNeededCount > 0 ? "Check QA notes before using this draft in a report." : "Confirm wording before generating an exportable progress report.",
        tone: reviewNeededCount > 0 ? "orange" : "green"
      }
    ]
  };
}

function inferValueType(value: string | number | boolean | null | undefined) {
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return Number.isInteger(value) ? "integer" : "float";
  return "string";
}

function formatSignalValue(value: string | number | boolean | null | undefined, valueType?: string) {
  if (value == null || value === "") return "Unavailable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    if (valueType === "ratio") return `${Math.round(value * 100)}%`;
    if (Number.isInteger(value)) return String(value);
    return value.toFixed(2).replace(/\.?0+$/, "");
  }
  return String(value);
}

function hasReferenceThresholds(definition?: FeatureDefinition) {
  return Boolean(definition?.defaultThresholds && Object.keys(definition.defaultThresholds).length > 0);
}

function featureLabelFromName(name: string) {
  return name
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function normalizeQaStatus(status?: string): TranscriptQaStatus {
  const normalized = status?.toLowerCase();
  if (normalized === "pass" || normalized === "passed" || normalized === "reviewed") return "pass";
  if (normalized === "fail" || normalized === "failed" || normalized === "error") return "fail";
  if (normalized === "warning" || normalized === "warn" || normalized === "needs_review") return "warning";
  return "warning";
}

export function createMockAnalysisSummary(): Pick<WorkflowState, "qaStatus" | "qaSummary" | "transcriptAttested" | "transcriptCompleteness" | "featuresExtracted" | "featurePercent" | "featureSummary" | "reviewNeededCount" | "insights"> {
  return {
    qaStatus: "warning",
    qaSummary: "Backend transcript data was unavailable, so this is a local decision-support preview only.",
    transcriptAttested: false,
    transcriptCompleteness: 82,
    featuresExtracted: true,
    featurePercent: 76,
    featureSummary: [
      { label: "Transcript source", value: "Local preview" },
      { label: "Feature status", value: "Preview" },
      { label: "Review gate", value: "Required" }
    ],
    reviewNeededCount: 1,
    insights: [
      { title: "Experimental audio workflow", text: "Recording and ASR are simulated until real processing is enabled.", tone: "orange" },
      { title: "Therapist review required", text: "Use this preview only to continue the therapist review workflow.", tone: "orange" }
    ]
  };
}

function pickFeature(features: Record<string, string | number | boolean | null>, names: string[], fallback: string): string | number | boolean {
  for (const name of names) {
    const value = features[name];
    if (value !== undefined && value !== null && value !== "") {
      return value;
    }
  }
  return fallback;
}

function createLocalSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `local_${crypto.randomUUID()}`;
  }
  return `local_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeLineEndings(value: string): string {
  return value.replace(/\r\n?/g, "\n");
}

function tokenizeLanguageSample(value: string): string[] {
  return (value.toLowerCase().match(/[\p{L}\p{N}']+/gu) ?? [])
    .filter((token) => !["xxx", "yyy", "www", "unclear"].includes(token));
}

function normalizeCueText(value: string): string {
  return tokenizeLanguageSample(value).join(" ");
}

function roundFeature(value: number): number {
  return Number(value.toFixed(4));
}

function formatFeatureNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function formatFeatureRatio(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function createDefaultChatMetadata(): ChatMetadata {
  return {
    languages: ["eng"],
    participants: [],
    ids: [],
    headers: {}
  };
}

function parseChatMetadata(lines: string[]): ChatMetadata {
  const headers: Record<string, string[]> = {};
  for (const rawLine of lines) {
    const match = rawLine.match(/^(@[^:\s]+):\s*(.*)$/);
    if (!match) continue;
    headers[match[1]] = [...(headers[match[1]] ?? []), match[2].trim()];
  }

  const languages = (headers["@Languages"] ?? [])
    .flatMap((value) => value.split(/[,;\s]+/))
    .map((value) => value.trim())
    .filter(Boolean);
  const participants = (headers["@Participants"] ?? [])
    .flatMap((value) => value.split(","))
    .map(parseParticipant)
    .filter((participant): participant is ChatParticipant => participant !== undefined);
  const ids = (headers["@ID"] ?? [])
    .map((raw) => {
      const code = raw.split("|")[2]?.trim().toUpperCase();
      return code ? { code, raw } : undefined;
    })
    .filter((id): id is ChatId => id !== undefined);
  const mediaValue = headers["@Media"]?.[0];
  const mediaParts = mediaValue?.split(",").map((value) => value.trim());

  return {
    languages,
    participants,
    ids,
    ...(mediaParts?.[0] ? { media: { name: mediaParts[0], type: mediaParts[1] || "audio" } } : {}),
    headers
  };
}

function parseParticipant(value: string): ChatParticipant | undefined {
  const parts = value.trim().split(/\s+/);
  const code = parts.shift()?.toUpperCase();
  if (!code) return undefined;
  return {
    code,
    name: parts.shift() || defaultParticipant(code).name,
    role: parts.join(" ") || defaultParticipant(code).role
  };
}

function defaultParticipant(code: string): ChatParticipant {
  const defaults: Record<string, Omit<ChatParticipant, "code">> = {
    CHI: { name: "Child", role: "Target_Child" },
    INV: { name: "Investigator", role: "Investigator" },
    THER: { name: "Therapist", role: "Investigator" },
    PAR: { name: "Parent", role: "Adult" },
    MOT: { name: "Mother", role: "Adult" },
    FAT: { name: "Father", role: "Adult" }
  };
  return { code, ...(defaults[code] ?? { name: code, role: "Adult" }) };
}

function renderChatSpeakerLine(line: TranscriptLine): string {
  const text = line.unclear && !/\b(?:xxx|\[unclear\])\b/i.test(line.text)
    ? `${line.text.trim()} [unclear]`
    : line.text.trim();
  const terminator = /[.?!]$/.test(text) || /\]$/.test(text) ? "" : " .";
  const timestamp = line.startMs !== undefined && line.endMs !== undefined
    ? ` \u0015${line.startMs}_${line.endMs}\u0015`
    : "";
  return `*${line.speaker.toUpperCase()}:\t${text}${terminator}${timestamp}`;
}

function isValidSpeakerCode(value: string): boolean {
  return /^[A-Za-z][A-Za-z0-9_]{0,7}$/.test(value);
}

function sanitizeMediaName(value: string): string {
  return value.replace(/\.[A-Za-z0-9]+$/, "").replace(/[^A-Za-z0-9_-]/g, "_") || "session_audio";
}

function parseTimestamp(value: string): { text: string; startMs?: number; endMs?: number } {
  const timestamp = value.match(/\u0015(\d+)_(\d+)\u0015/);
  const text = value.replace(/\s*\u0015\d+_\d+\u0015\s*/g, " ").trim();
  if (!timestamp) return { text };
  return {
    text,
    startMs: Number(timestamp[1]),
    endMs: Number(timestamp[2])
  };
}

function normalizeSpeakerLabel(value: string): string {
  const compact = value.trim().toUpperCase().replace(/[^A-Z0-9_]/g, "");
  const aliases: Record<string, string> = {
    CHILD: "CHI",
    KID: "CHI",
    THERAPIST: "THER",
    CLINICIAN: "THER",
    INVESTIGATOR: "INV",
    PARENT: "PAR",
    CAREGIVER: "PAR",
    MOTHER: "MOT",
    MOM: "MOT",
    FATHER: "FAT",
    DAD: "FAT"
  };
  return aliases[compact] ?? (compact.slice(0, 8) || "UNK");
}

export type BackendAudioFileMetadata = {
  audio_file_id: string;
  session_id: string;
  case_id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  upload_status: string;
};

export async function uploadAudioFileBytes(uploadUrl: string, blob: Blob): Promise<void> {
  await apiUploadBlob(uploadUrl, blob);
}

export async function getSessionAudioFiles(sessionId: string): Promise<BackendAudioFileMetadata[]> {
  return apiGet<BackendAudioFileMetadata[]>(`/sessions/${sessionId}/audio`);
}

export async function uploadAudioBlobToBackend(
  sessionId: string,
  blob: Blob,
  metadata: { durationSeconds: number; mimeType: string }
): Promise<{ audioFileId: string }> {
  const ext = metadata.mimeType.split("/")[1] ?? "webm";
  const job = await apiRequest<any>(`/sessions/${sessionId}/audio/upload`, {
    method: "POST",
    body: JSON.stringify({
      filename: `recording-${Date.now()}.${ext}`,
      content_type: metadata.mimeType,
      size_bytes: blob.size,
      duration_seconds: metadata.durationSeconds,
    }),
  });
  const audioFileId: string = job.details?.audio_file?.audio_file_id;
  if (!audioFileId) throw new Error("Backend did not return audio_file_id.");

  let uploadUrl = job.details?.upload_intent?.upload_url;
  if (!uploadUrl || uploadUrl.startsWith("mock-signed-upload://")) {
    uploadUrl = `/audio/${audioFileId}/upload-file`;
  }

  await uploadAudioFileBytes(uploadUrl, blob);
  return { audioFileId };
}

export async function startBackendTranscriptionJob(
  sessionId: string,
  audioId: string,
  provider: string = "mock"
): Promise<{ jobId: string }> {
  const job = await apiRequest<any>(`/sessions/${sessionId}/audio/process`, {
    method: "POST",
    body: JSON.stringify({ audio_id: audioId, provider, draft_text: "" }),
  });
  return { jobId: job.job_id };
}

export async function pollTranscriptionJob(jobId: string): Promise<{
  status: string;
  transcriptId?: string;
  message: string;
  requestedProvider?: string;
  actualProvider?: string;
}> {
  const job = await apiGet<any>(`/jobs/${jobId}`);
  return {
    status: job.status,
    transcriptId: job.details?.asr_draft?.transcript_id,
    message: job.message ?? "",
    requestedProvider: job.details?.requested_provider,
    actualProvider: job.details?.actual_provider,
  };
}

export async function createBackendCase(payload: Partial<BackendCase>): Promise<BackendCase> {
  return apiRequest<BackendCase>("/cases", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateBackendCase(caseId: string, payload: Partial<BackendCase>): Promise<BackendCase> {
  return apiRequest<BackendCase>(`/cases/${caseId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function withdrawBackendCaseConsent(
  caseId: string,
  reason: string,
  redactNotes: boolean
): Promise<{ status: string; message: string }> {
  return apiRequest<{ status: string; message: string }>(`/cases/${caseId}/withdraw-consent`, {
    method: "POST",
    body: JSON.stringify({
      reason,
      redact_notes: redactNotes
    })
  });
}
