/**
 * Analysis adapter: the transport boundary for model-informed decision support
 * and evidence review (ML readiness, ML decision support, cues acknowledgement,
 * and profile evidence disposition).
 *
 * Per DESIGN.md, "new transport behavior should first be added to the
 * service/adapter boundary" — feature controllers and views import from here,
 * not from the monolithic `lib/workflow.ts`. Domain types (MlDecisionSupport,
 * EvidenceAvailability, ProfileEvidence, …) live in `lib/workflow.ts`; this
 * module owns the backend wire shapes and their normalization to those types.
 */
import { apiGet, apiRequest } from "@/lib/api";
import { summarizeAnalysis } from "@/lib/workflow";
import type {
  AiAssistanceArea,
  AiReview,
  AssociatedFeatureEvidence,
  BackendFeatureDefinition,
  BackendFeatures,
  BackendQa,
  EvidenceAvailability,
  EvidenceReviewState,
  FeatureDefinition,
  MlDecisionSupport,
  MlReadiness,
  PatternEvidence,
  ProfileEvidence,
  WorkflowState,
} from "@/lib/workflow";

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
  state: EvidenceAvailability["state"];
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

export type SessionCuesAcknowledgement = {
  sessionId: string;
  acknowledged: boolean;
  acknowledgedAt: string;
  acknowledgedBy: string;
};

type BackendAiAssistanceArea = {
  area: string;
  summary: string;
  contributing_factors?: string[];
  recommended_actions?: string[];
};

type BackendAiReview = {
  ai_review_id: string;
  session_id: string;
  summary: string;
  assistance_areas?: BackendAiAssistanceArea[];
  key_findings?: string[];
  concerns?: string[];
  strengths?: string[];
  limitations?: string[];
  recommended_review_actions?: string[];
  confidence_level: string;
  review_priority: string;
  input_transcript_version: number;
  feature_set_id?: string | null;
  feature_schema_version?: string | null;
  therapist_review_status: string;
};

const REFERENCE_EVIDENCE_PROVIDER = "reference_evidence_review";

export async function generateMlDecisionSupport(transcriptId: string): Promise<MlDecisionSupport> {
  const result = await apiRequest<BackendMlDecisionSupport>(`/transcripts/${transcriptId}/ml-review`, {
    method: "POST",
    body: JSON.stringify({ provider_id: REFERENCE_EVIDENCE_PROVIDER })
  });
  return normalizeMlResult(result);
}

export async function getMlDecisionSupport(sessionId: string): Promise<MlDecisionSupport> {
  return normalizeMlResult(await apiGet<BackendMlDecisionSupport>(`/sessions/${sessionId}/ml-review`));
}

/**
 * Records the therapist's acknowledgement of the reviewed cues for a session.
 * The backend writes an immutable, actor-attributed audit event; the returned
 * timestamp is persisted in the workflow state so the acknowledgement survives
 * reloads.
 */
export async function acknowledgeSessionCues(sessionId: string): Promise<SessionCuesAcknowledgement> {
  const result = await apiRequest<{
    session_id: string;
    acknowledged: boolean;
    acknowledged_at: string;
    acknowledged_by: string;
  }>(`/sessions/${encodeURIComponent(sessionId)}/acknowledge-cues`, {
    method: "POST",
  });
  return {
    sessionId: result.session_id,
    acknowledged: result.acknowledged,
    acknowledgedAt: result.acknowledged_at,
    acknowledgedBy: result.acknowledged_by,
  };
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

/**
 * Runs the feature-extraction transport (POST extract-features) and folds the
 * resulting feature set plus QA context into the workflow summary via
 * `summarizeAnalysis` (domain logic that lives in `lib/workflow.ts`).
 */
export async function runBackendAnalysis(
  sessionId: string,
  transcriptId?: string,
  qa: BackendQa = { status: "pass", summary: "Transcript QA and therapist attestation completed." }
): Promise<Pick<WorkflowState, "qaStatus" | "qaSummary" | "transcriptAttested" | "transcriptCompleteness" | "featuresExtracted" | "featurePercent" | "featureSummary" | "reviewNeededCount" | "insights"> & Pick<WorkflowState, "featureSetId" | "featureTranscriptVersion">> {
  const extractionPath = transcriptId
    ? `/transcripts/${transcriptId}/extract-features`
    : `/sessions/${sessionId}/features/extract`;
  const features = await apiRequest<BackendFeatures>(extractionPath, { method: "POST" });
  return summarizeAnalysis(qa, features);
}

export async function getAiReview(sessionId: string): Promise<AiReview> {
  return normalizeAiReview(await apiGet<BackendAiReview>(`/sessions/${sessionId}/ai-review`));
}

export async function generateAiReview(sessionId: string): Promise<AiReview> {
  const result = await apiRequest<BackendAiReview>(`/sessions/${sessionId}/ai-review`, {
    method: "POST",
  });
  return normalizeAiReview(result);
}

function normalizeAiReview(result: BackendAiReview): AiReview {
  const normalizeArea = (area: BackendAiAssistanceArea): AiAssistanceArea => ({
    area: area.area,
    summary: area.summary,
    contributingFactors: area.contributing_factors ?? [],
    recommendedActions: area.recommended_actions ?? [],
  });
  return {
    aiReviewId: result.ai_review_id,
    sessionId: result.session_id,
    summary: result.summary,
    assistanceAreas: (result.assistance_areas ?? []).map(normalizeArea),
    keyFindings: result.key_findings ?? [],
    concerns: result.concerns ?? [],
    strengths: result.strengths ?? [],
    limitations: result.limitations ?? [],
    recommendedReviewActions: result.recommended_review_actions ?? [],
    confidenceLevel: result.confidence_level,
    reviewPriority: result.review_priority,
    inputTranscriptVersion: result.input_transcript_version,
    featureSetId: result.feature_set_id ?? undefined,
    featureSchemaVersion: result.feature_schema_version ?? undefined,
    therapistReviewStatus: result.therapist_review_status,
  };
}

export async function getMlReadiness(transcriptId: string): Promise<MlReadiness> {
  const result = await apiGet<{
    ready: boolean;
    provider_id: string;
    reason_codes: string[];
    reasons: string[];
  }>(`/transcripts/${transcriptId}/ml-readiness?provider_id=${REFERENCE_EVIDENCE_PROVIDER}`);
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

export const analysisAdapter = {
  generateMlDecisionSupport,
  getMlDecisionSupport,
  acknowledgeSessionCues,
  updateProfileEvidenceReview,
  getMlReadiness,
  getAiReview,
  generateAiReview,
  getBackendSessionFeatures,
  getBackendFeatureDefinitions,
  runBackendAnalysis,
};
