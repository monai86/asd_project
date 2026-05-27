import { describe, it, expect, beforeEach } from "vitest";
import { store } from "../store/state.js";
import { getChildProgress } from "../services/progress-service.js";

describe("Longitudinal Progress Tracking", () => {
  beforeEach(() => {
    store.setState({
      currentUser: { role: "admin", user_id: "admin" },
      cases: [{ case_id: "CASE-T", anonymized_child_code: "CHI-T", age_months: 48, sex: "male", latest_score: 0.5, score_trend: [0.4, 0.5], owner_user_id: "admin" }],
      sessions: [
        { session_id: "SESSION-T1", case_id: "CASE-T", owner_user_id: "admin", session_date: "2026-05-01", session_type: "free_play", therapist_review_status: "reviewed" },
        { session_id: "SESSION-T2", case_id: "CASE-T", owner_user_id: "admin", session_date: "2026-05-05", session_type: "free_play", therapist_review_status: "reviewed" }
      ],
      extractedFeatureOutputs: {
        "SESSION-T1": { features: { mlu: 2.0, ttr: 0.5 } },
        "SESSION-T2": { features: { mlu: 2.5, ttr: 0.6 } }
      },
      aiDecisionOutputs: {
        "SESSION-T1": { screening_support_score: 0.4 },
        "SESSION-T2": { screening_support_score: 0.5 }
      },
      goals: [{ goal_id: "G-1", case_id: "CASE-T", text: "Spontaneous requests", status: "active" }]
    });
  });

  it("should extract chronological session trends and caseload goal mappings", () => {
    const progress = getChildProgress("CASE-T");
    expect(progress.sessions.length).toBe(2);
    expect(progress.sessions[0].mlu).toBe(2.0);
    expect(progress.sessions[1].mlu).toBe(2.5); // increased MLU
    expect(progress.goals.length).toBe(1);
    expect(progress.wording).toContain("requires clinical interpretation");
  });
});
