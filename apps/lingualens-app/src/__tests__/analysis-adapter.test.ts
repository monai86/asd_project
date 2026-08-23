import { afterEach, describe, expect, it, vi } from "vitest";

import { analysisAdapter } from "@/services/adapters/analysis-adapter";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const mlResponse = {
  result_id: "MLR-1",
  status: "completed",
  provider_name: "ReferenceEvidenceProvider",
  provider_version: "0.9.0",
  input_feature_schema_version: "features-basic-v0.7",
  generated_at: "2026-06-20T00:00:00Z",
  cues: [{
    cue_code: "cue-01",
    title: "Repetitive language",
    severity: "review",
    explanation: "Repeated forms detected.",
    supporting_features: { repetition_cue: 3 },
    limitations: ["Descriptive cue only."],
    recommended_next_review_step: "Review in context.",
    review_state: { status: "unreviewed" },
  }],
  pattern_evidence: {
    status: "no_additional_pattern_cue",
    availability: {
      state: "available",
      message: "Pattern evidence available.",
      workflow_can_continue: true,
    },
    associated_features: [{
      feature_name: "repetition_cue",
      observed_value: 3,
      position: "within_iqr",
      caveat: "Interpret descriptively.",
    }],
    review_state: { status: "unreviewed", therapist_note: "" },
  },
  profile_evidence: [{
    profile_code: "TD",
    presentation_group: "TD",
    status: "comparable_patterns_observed",
    availability: {
      state: "available",
      message: "Reference evidence available.",
      workflow_can_continue: true,
    },
    participant_count: 124,
    corpus_count: 3,
    associated_features: [],
    review_state: { status: "unreviewed", therapist_note: "" },
  }],
  artifact_provenance: { schema: "features-basic-v0.7" },
  limitations: ["Not diagnostic."],
  not_diagnostic: true,
  decision_support_only: true,
};

describe("analysis adapter transport boundary", () => {
  it("normalizes backend ML decision support into the domain shape", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json(mlResponse)));

    const result = await analysisAdapter.generateMlDecisionSupport("TRANSCRIPT-ML");

    expect(result.resultId).toBe("MLR-1");
    expect(result.cues[0]).toEqual(expect.objectContaining({
      cueCode: "cue-01",
      severity: "review",
      reviewStatus: "unreviewed",
    }));
    expect(result.patternEvidence?.status).toBe("no_additional_pattern_cue");
    expect(result.patternEvidence?.associatedFeatures[0]).toEqual(expect.objectContaining({
      featureName: "repetition_cue",
      position: "within_iqr",
    }));
    expect(result.profileEvidence[0]).toEqual(expect.objectContaining({
      profileCode: "TD",
      participantCount: 124,
    }));
    expect(result.notDiagnostic).toBe(true);
    expect(result.decisionSupportOnly).toBe(true);
  });

  it("returns a defensive empty result when the backend payload lacks a result id", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ status: "completed" })));

    const result = await analysisAdapter.getMlDecisionSupport("SESSION-ML");

    expect(result.resultId).toBe("");
    expect(result.cues).toEqual([]);
    expect(result.profileEvidence).toEqual([]);
  });

  it("maps the cues acknowledgement response to the domain shape", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({
      session_id: "SESSION-ACK",
      acknowledged: true,
      acknowledged_at: "2026-07-17T00:00:00Z",
      acknowledged_by: "therapist-demo",
    })));

    const acknowledgement = await analysisAdapter.acknowledgeSessionCues("SESSION-ACK");

    expect(acknowledgement).toEqual({
      sessionId: "SESSION-ACK",
      acknowledged: true,
      acknowledgedAt: "2026-07-17T00:00:00Z",
      acknowledgedBy: "therapist-demo",
    });
  });

  it("maps the readiness response to the domain shape", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({
      ready: true,
      provider_id: "reference_evidence_review",
      reason_codes: [],
      reasons: [],
    })));

    const readiness = await analysisAdapter.getMlReadiness("TRANSCRIPT-ML");

    expect(readiness).toEqual({
      ready: true,
      providerId: "reference_evidence_review",
      reasonCodes: [],
      reasons: [],
    });
  });

  it("fetches backend session features", async () => {
    const requested: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      requested.push(String(input));
      return Response.json({
        feature_set_id: "FS-1",
        transcript_version: 2,
        features: [{ name: "mlu_words", value: 3.4 }],
        core_features: { ndw: 78 },
      });
    }));

    const features = await analysisAdapter.getBackendSessionFeatures("SESSION-FX");

    expect(requested[0]).toBe("http://localhost:8000/api/v1/sessions/SESSION-FX/features");
    expect(features.feature_set_id).toBe("FS-1");
    expect(features.core_features).toEqual({ ndw: 78 });
  });

  it("maps backend feature definitions into the domain shape", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json([{
      feature_name: "mlu_words",
      display_name: "MLU words",
      description: "Mean length of utterance in words.",
      value_type: "float",
      unit: "words",
      calculation_method: "Derived from child utterances.",
      required_inputs: ["child_utterances"],
      numerator_definition: "Total words / total utterances",
      denominator_definition: null,
      default_thresholds: null,
      limitations: ["Not diagnostic."],
      clinical_interpretation_caution: "Therapist interpretation required.",
      feature_version: "v1",
      provider_name: "ReferenceProvider",
      provider_id: "reference",
    }])));

    const definitions = await analysisAdapter.getBackendFeatureDefinitions();

    expect(definitions).toHaveLength(1);
    expect(definitions[0]).toEqual(expect.objectContaining({
      featureName: "mlu_words",
      displayName: "MLU words",
      valueType: "float",
      unit: "words",
      requiredInputs: ["child_utterances"],
      numeratorDefinition: "Total words / total utterances",
      clinicalInterpretationCaution: "Therapist interpretation required.",
      providerId: "reference",
    }));
  });

  it("runs feature extraction via the transcript path and summarizes analysis", async () => {
    const requested: Array<{ url: string; init?: RequestInit }> = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      requested.push({ url: String(input), init });
      return Response.json({
        feature_set_id: "FS-EXTRACT",
        transcript_version: 1,
        features: { mlu_words: 3.2, ndw: 78, question_ratio: 0.06 },
      });
    }));

    const summary = await analysisAdapter.runBackendAnalysis("SESSION-FX", "TRANSCRIPT-FX");

    expect(requested[0].url).toBe("http://localhost:8000/api/v1/transcripts/TRANSCRIPT-FX/extract-features");
    expect(requested[0].init?.method).toBe("POST");
    expect(summary.featuresExtracted).toBe(true);
    expect(summary.featureSetId).toBe("FS-EXTRACT");
    expect(summary.featureSummary).toEqual(expect.arrayContaining([
      { label: "MLU words", value: "3.2" },
      { label: "Different words", value: "78" },
    ]));
    expect(summary.transcriptAttested).toBe(true);
  });

  it("runs feature extraction via the session path when no transcript id is given", async () => {
    const requested: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      requested.push(String(input));
      return Response.json({ feature_set_id: "FS-SESSION", features: {} });
    }));

    await analysisAdapter.runBackendAnalysis("SESSION-FX");

    expect(requested[0]).toBe("http://localhost:8000/api/v1/sessions/SESSION-FX/features/extract");
  });

  it("records profile evidence review disposition", async () => {
    const requested: Array<{ url: string; init?: RequestInit }> = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      requested.push({ url: String(input), init });
      return Response.json({ ...mlResponse, profile_evidence: [{
        ...mlResponse.profile_evidence[0],
        review_state: { status: "reviewed", therapist_note: "Checked" },
      }] });
    }));

    const result = await analysisAdapter.updateProfileEvidenceReview("MLR-1", "TD", "reviewed", "Checked");

    expect(requested[0].url).toBe("http://localhost:8000/api/v1/ml-results/MLR-1/profiles/TD/review-state");
    expect(requested[0].init?.method).toBe("PATCH");
    expect(JSON.parse(String(requested[0].init?.body))).toEqual({
      status: "reviewed",
      therapist_note: "Checked",
    });
    expect(result.profileEvidence[0].reviewState).toEqual(expect.objectContaining({
      status: "reviewed",
      therapistNote: "Checked",
    }));
  });
});
