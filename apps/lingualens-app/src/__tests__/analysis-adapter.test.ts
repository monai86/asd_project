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
