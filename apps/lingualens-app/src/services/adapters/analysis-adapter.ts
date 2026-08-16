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
import type {
  AssociatedFeatureEvidence,
  EvidenceAvailability,
  EvidenceReviewState,
  MlDecisionSupport,
  MlReadiness,
  PatternEvidence,
  ProfileEvidence,
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
};
