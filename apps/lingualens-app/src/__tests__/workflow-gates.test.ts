import { describe, expect, it } from "vitest";

import {
  approveReviewedCuesBlockedReason,
  attestTranscriptBlockedReason,
  continueToSourceMaterialBlockedReason,
  exportTranscriptBlockedReason,
  extractFeaturesBlockedReason,
  generateEvidenceReviewBlockedReason,
  grantConsentBlockedReason,
  regenerateFindingsBlockedReason,
  startTranscriptReviewBlockedReason,
} from "@/lib/workflow-gates";
import { createInitialWorkflowState } from "@/lib/workflow";

describe("startTranscriptReviewBlockedReason", () => {
  const complete = {
    sessionDetailsComplete: true,
    transcriptSetupComplete: true,
    sourceReadyForReview: true,
    selectedSource: "paste" as const,
  };

  it("returns undefined when every prerequisite is satisfied", () => {
    expect(startTranscriptReviewBlockedReason(complete)).toBeUndefined();
  });

  it("explains when session details are incomplete", () => {
    const reason = startTranscriptReviewBlockedReason({
      ...complete,
      sessionDetailsComplete: false,
    });
    expect(reason).toContain("session details");
    expect(reason).toContain("child/client");
  });

  it("explains when transcript setup is incomplete", () => {
    const reason = startTranscriptReviewBlockedReason({
      ...complete,
      transcriptSetupComplete: false,
    });
    expect(reason).toContain("transcript setup");
  });

  it("explains when paste/cha source material is missing", () => {
    for (const selectedSource of ["paste", "cha"] as const) {
      const reason = startTranscriptReviewBlockedReason({
        ...complete,
        sourceReadyForReview: false,
        selectedSource,
      });
      expect(reason).toContain("Add transcript text in Source Material");
    }
  });

  it("explains when a draft transcript is not yet available for audio sources", () => {
    for (const selectedSource of ["recording", "audio"] as const) {
      const reason = startTranscriptReviewBlockedReason({
        ...complete,
        sourceReadyForReview: false,
        selectedSource,
      });
      expect(reason).toContain("draft transcript");
    }
  });
});

describe("continueToSourceMaterialBlockedReason", () => {
  it("returns undefined when session details are complete", () => {
    expect(continueToSourceMaterialBlockedReason({ sessionDetailsComplete: true })).toBeUndefined();
  });

  it("explains which fields are missing when details are incomplete", () => {
    const reason = continueToSourceMaterialBlockedReason({ sessionDetailsComplete: false });
    expect(reason).toContain("session details");
    expect(reason).toContain("child/client");
  });
});

describe("grantConsentBlockedReason", () => {
  it("returns undefined when the confirmation box is checked", () => {
    expect(grantConsentBlockedReason({ checked: true, busy: false })).toBeUndefined();
  });

  it("returns undefined while verification is in flight", () => {
    expect(grantConsentBlockedReason({ checked: true, busy: true })).toBeUndefined();
  });

  it("explains that the confirmation box must be checked", () => {
    expect(grantConsentBlockedReason({ checked: false, busy: false })).toBe(
      "Check the confirmation box to verify caregiver consent was obtained.",
    );
  });
});

describe("exportTranscriptBlockedReason", () => {
  it("returns undefined when there are transcript lines", () => {
    expect(exportTranscriptBlockedReason({ busy: false, linesCount: 2 })).toBeUndefined();
  });

  it("returns undefined while a request is in flight", () => {
    expect(exportTranscriptBlockedReason({ busy: true, linesCount: 0 })).toBeUndefined();
  });

  it("explains when there are no transcript lines", () => {
    expect(exportTranscriptBlockedReason({ busy: false, linesCount: 0 })).toBe(
      "Add transcript lines before exporting.",
    );
  });
});

describe("extractFeaturesBlockedReason", () => {
  const unlocked = {
    transcriptReady: true,
    transcriptAttested: true,
    transcriptReviewStatus: "reviewed" as const,
    backendTranscriptId: "T-1",
    backendTranscriptSessionId: "S-1",
  };

  it("returns undefined when the transcript is attested, reviewed, and persisted", () => {
    expect(extractFeaturesBlockedReason({ ...createInitialWorkflowState(), ...unlocked })).toBeUndefined();
  });

  it("does not treat workflow loading as a blocker", () => {
    expect(extractFeaturesBlockedReason({
      ...createInitialWorkflowState(),
      ...unlocked,
      workflowLoading: true,
    })).toBeUndefined();
  });

  it("points the therapist at saving a transcript first when nothing is ready", () => {
    const reason = extractFeaturesBlockedReason(createInitialWorkflowState());
    expect(reason).toBe("Save a transcript and review it before extracting features.");
  });

  it("explains the review and attestation gate", () => {
    const reason = extractFeaturesBlockedReason({
      ...createInitialWorkflowState(),
      transcriptReady: true,
      transcriptAttested: false,
      transcriptReviewStatus: "in_review",
    });
    expect(reason).toBe("Feature extraction requires a saved, reviewed, and attested transcript.");
  });

  it("explains when the transcript is not yet tied to a saved backend transcript", () => {
    const reason = extractFeaturesBlockedReason({
      ...createInitialWorkflowState(),
      ...unlocked,
      backendTranscriptId: undefined,
    });
    expect(reason).toContain("Save the transcript to the session");
  });

  it("explains when no persisted session exists", () => {
    const reason = extractFeaturesBlockedReason({
      ...createInitialWorkflowState(),
      ...unlocked,
      backendTranscriptSessionId: undefined,
      backendSessionId: undefined,
    });
    expect(reason).toContain("persisted session");
  });
});

describe("attestTranscriptBlockedReason", () => {
  const base = { busy: false, attested: false, linesCount: 2, qaStatus: "pass" as const };

  it("returns undefined when QA passed and lines exist", () => {
    expect(attestTranscriptBlockedReason(base)).toBeUndefined();
  });

  it("returns undefined when the transcript is already attested", () => {
    expect(attestTranscriptBlockedReason({ ...base, attested: true })).toBeUndefined();
  });

  it("returns undefined while a request is in flight", () => {
    expect(attestTranscriptBlockedReason({ ...base, busy: true })).toBeUndefined();
  });

  it("explains when there are no transcript lines", () => {
    expect(attestTranscriptBlockedReason({ ...base, linesCount: 0 })).toContain("Add transcript lines");
  });

  it("explains that QA must run first", () => {
    expect(attestTranscriptBlockedReason({ ...base, qaStatus: "not_run" })).toBe(
      "Run transcript QA before attesting.",
    );
  });

  it("explains that QA failures must be resolved", () => {
    expect(attestTranscriptBlockedReason({ ...base, qaStatus: "fail" })).toContain("QA failures");
  });
});

describe("regenerateFindingsBlockedReason", () => {
  it("returns undefined when the transcript is reviewed and attested", () => {
    const state = createInitialWorkflowState();
    expect(regenerateFindingsBlockedReason({ ...state, transcriptAttested: true, transcriptReviewStatus: "reviewed" })).toBeUndefined();
  });

  it("explains that transcript review and attestation must be complete", () => {
    const reason = regenerateFindingsBlockedReason(createInitialWorkflowState());
    expect(reason).toContain("transcript review and attestation");
  });

  it("explains when the transcript is reviewed but not attested", () => {
    const state = createInitialWorkflowState();
    const reason = regenerateFindingsBlockedReason({ ...state, transcriptReviewStatus: "reviewed" });
    expect(reason).toContain("attestation");
  });
});

describe("generateEvidenceReviewBlockedReason", () => {
  it("returns undefined when readiness is ready and the backend is available", () => {
    expect(generateEvidenceReviewBlockedReason({ readiness: { ready: true, providerId: "p", reasonCodes: [], reasons: [] } })).toBeUndefined();
  });

  it("returns undefined when no readiness check has run", () => {
    expect(generateEvidenceReviewBlockedReason({})).toBeUndefined();
  });

  it("explains when the backend is unavailable", () => {
    const reason = generateEvidenceReviewBlockedReason({ backendUnavailable: true });
    expect(reason).toContain("backend is unavailable");
  });

  it("surfaces the backend's own readiness reasons when present", () => {
    const reason = generateEvidenceReviewBlockedReason({
      readiness: {
        ready: false,
        providerId: "reference_evidence_review",
        reasonCodes: ["features_missing"],
        reasons: ["Feature extraction has not been completed."],
      },
    });
    expect(reason).toContain("Feature extraction has not been completed.");
  });

  it("falls back to a generic explanation when the backend gives no reason", () => {
    const reason = generateEvidenceReviewBlockedReason({
      readiness: { ready: false, providerId: "reference_evidence_review", reasonCodes: [], reasons: [] },
    });
    expect(reason).toContain("evidence readiness check is blocked");
  });

  it("treats backend unavailability as the primary blocker", () => {
    const reason = generateEvidenceReviewBlockedReason({
      backendUnavailable: true,
      readiness: { ready: false, providerId: "p", reasonCodes: [], reasons: ["Feature extraction has not been completed."] },
    });
    expect(reason).toContain("backend is unavailable");
  });
});

describe("approveReviewedCuesBlockedReason", () => {
  it("returns undefined when cues are reviewable and nothing is stale", () => {
    expect(approveReviewedCuesBlockedReason({ busy: false, findingsStale: false, hasReviewableCues: true })).toBeUndefined();
  });

  it("returns undefined while a request is in flight", () => {
    expect(approveReviewedCuesBlockedReason({ busy: true, findingsStale: false, hasReviewableCues: true })).toBeUndefined();
  });

  it("explains when findings are stale", () => {
    const reason = approveReviewedCuesBlockedReason({ busy: false, findingsStale: true, hasReviewableCues: true });
    expect(reason).toContain("Regenerate findings");
  });

  it("explains when there are no extracted signals or evidence review to approve", () => {
    const reason = approveReviewedCuesBlockedReason({ busy: false, findingsStale: false, hasReviewableCues: false });
    expect(reason).toContain("extracted signals");
    expect(reason).toContain("extract features");
  });
});
