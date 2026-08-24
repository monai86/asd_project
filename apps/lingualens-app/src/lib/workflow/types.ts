/**
 * LinguaLens Domain Models and Type Definitions
 *
 * Core domain contracts for cases, sessions, transcripts, acoustic/linguistic features,
 * normative developmental bands, decision support, safety audits, and reports.
 */

export type WorkflowSource = "recording" | "audio-upload" | "cha-upload" | "paste-transcript";
export type TranscriptReviewStatus = "not_started" | "draft" | "in_review" | "reviewed";
export type AnalysisStatus = "not_started" | "processing" | "completed" | "failed" | "stale";
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
  temporarySpeakerId?: string | null;
  sourceSpeakerLabel?: string | null;
};

export type SpeakerMappingEntry = {
  temporary_speaker_id: string;
  confirmed_chat_code?: "CHI" | "THER" | "OTH" | null;
  participant_role?: "target_child" | "therapist" | "other" | null;
  source_speaker_label?: string | null;
  provider_metadata: Record<string, string>;
  affected_utterance_ids: string[];
  reviewed_utterance_ids: string[];
};

export type SpeakerMapping = {
  mapping_id: string;
  organization_id: string;
  transcript_id: string;
  source_transcript_version: number;
  applied_transcript_version: number | null;
  mapping_version: number;
  status: "draft" | "confirmed";
  entries: SpeakerMappingEntry[];
  confirmed_by_user_id: string | null;
  confirmed_by_role: string | null;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
  required: boolean;
  persisted: boolean;
  effective_status: "not_required" | "draft" | "confirmed" | "stale";
  issue_code?: string | null;
  issue_message?: string | null;
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

export type AiAssistanceArea = {
  area: string;
  summary: string;
  contributingFactors: string[];
  recommendedActions: string[];
};

export type AiReview = {
  aiReviewId: string;
  sessionId: string;
  summary: string;
  assistanceAreas: AiAssistanceArea[];
  keyFindings: string[];
  concerns: string[];
  strengths: string[];
  limitations: string[];
  recommendedReviewActions: string[];
  confidenceLevel: string;
  reviewPriority: string;
  inputTranscriptVersion: number;
  featureSetId?: string;
  featureSchemaVersion?: string;
  therapistReviewStatus: string;
};

export type WorkflowState = {
  sessionId?: string;
  sessionCreatedAt?: string;
  backendSessionId?: string;
  backendTranscriptId?: string;
  backendTranscriptVersion?: number;
  backendTranscriptSessionId?: string;
  backendReportId?: string;
  backendReportVersion?: number;
  featureSetId?: string;
  featureTranscriptVersion?: number;
  featureSchemaVersion?: string;
  reportGeneratedFromVersions?: Record<string, string>;
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
  aiReview?: AiReview;
  cuesAcknowledgedAt?: string;
  cuesAcknowledgedBy?: string;
  reviewNeededCount: number;
  insights: Array<{ title: string; text: string; tone: "green" | "orange" }>;
  therapistNotes: string;
  therapyGoals: string[];
  reportId?: string;
  reportStatus: "not_started" | "draft" | "reviewed" | "finalized" | "stale";
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
  cues_acknowledged_at?: string;
  cues_acknowledged_by?: string;
};

export type DashboardRecentSession = {
  session_id: string;
  case_id: string;
  case_label: string;
  session_date: string;
  status: string;
  has_transcript: boolean;
  has_features: boolean;
  has_ml_review: boolean;
  has_report: boolean;
};

export type DashboardTrendFeature = {
  key: string;
  label: string;
  unit: string;
};

export type DashboardTrendPoint = {
  session_id: string;
  session_date: string;
  values: Record<string, number>;
};

export type DashboardTrendReference = {
  age_band: string;
  task_type: string;
  features: Record<string, { q1: number; median: number; q3: number }>;
};

export type DashboardTrendCase = {
  case_id: string;
  case_label: string;
  points: DashboardTrendPoint[];
  reference?: DashboardTrendReference | null;
};

export type DashboardFeatureTrends = {
  features: DashboardTrendFeature[];
  cases: DashboardTrendCase[];
};

export type DashboardSummary = {
  organization_id: string;
  generated_at: string;
  cases: {
    total: number;
    consent_counts: Record<string, number>;
    with_latest_reviewed_session: number;
  };
  sessions: {
    total: number;
    status_counts: Record<string, number>;
    with_transcript: number;
    with_features: number;
    with_ml_review: number;
    with_report: number;
  };
  reports: {
    total: number;
    signoff_counts: Record<string, number>;
  };
  recent_sessions: DashboardRecentSession[];
  feature_trends: {
    features: DashboardTrendFeature[];
    cases: DashboardTrendCase[];
  };
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
  version?: number;
  utterances?: Array<{
    utterance_id: string;
    speaker: string;
    text: string;
    start_ms?: number | null;
    end_ms?: number | null;
    unintelligible?: boolean;
    temporary_speaker_id?: string | null;
    source_speaker_label?: string | null;
  }>;
};

export type BackendQa = {
  status?: string;
  qa_status?: string;
  quality_score?: number;
  qa_score?: number;
  summary?: string;
  issues?: string[];
  qa_issues?: string[];
};

export type BackendFeatures = {
  feature_set_id?: string;
  feature_id?: string;
  transcript_version?: number;
  review_status?: string;
  schema_version?: string;
  insufficient_data?: boolean;
  features?: Record<string, string | number | boolean | null> | Array<{ name: string; value: string | number | boolean | null }>;
  core_features?: Record<string, string | number | boolean | null>;
  optional_indicators?: Record<string, string | number | boolean | null>;
};

export type BackendFeatureDefinition = {
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
  signed_by?: string;
  signed_at?: string;
  signed_snapshot_version?: number;
  signed_snapshot_hash?: string;
  signed_snapshot?: Record<string, unknown>;
  supersedes_report_id?: string;
  revision_number?: number;

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
  created_at: string;
  expires_at: string;
  accepted_at?: string | null;
  revoked_at?: string | null;
};
