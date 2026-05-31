import { describe, it, expect, beforeEach } from "vitest";
import { store } from "../store/state.js";
import { SAFETY_DISCLAIMER, MOCK_MODE } from "../constants.js";
import { getVisibleCases } from "../services/case-service.js";
import { createLinguisticFeatureSet } from "@shared/models";
import { extractAllFeatures } from "@shared/services/feature-extraction-service.js";

describe("Frontend Stabilization and Safety Verification", () => {
  beforeEach(() => {
    // Reset state before each test
    store.setState({
      currentUser: null,
      cases: [],
      selectedCaseId: null
    });
  });

  describe("Safety Disclaimer Presence", () => {
    it("should have a defined safety disclaimer containing essential warning elements", () => {
      expect(SAFETY_DISCLAIMER).toBeDefined();
      expect(SAFETY_DISCLAIMER).toContain("clinical decision-support prototype");
      expect(SAFETY_DISCLAIMER).toContain("does not diagnose ASD");
      expect(SAFETY_DISCLAIMER).toContain("does not replace qualified clinical judgment");
    });

    it("should run in mock mode by default", () => {
      expect(MOCK_MODE).toBe(true);
    });
  });

  describe("14-Feature Schema Label Consistency", () => {
    it("should default LinguisticFeatureSet feature_schema_version to '14-feature-schema'", () => {
      const featureSet = createLinguisticFeatureSet({
        feature_id: "FEATURE-001",
        session_id: "SESSION-001"
      });
      expect(featureSet.feature_schema_version).toBe("14-feature-schema");
    });

    it("should extract features with appropriate canonical schema mappings", () => {
      const utterances = [
        { speaker_label: "CHILD", text: "car .", start_time: 1.0, end_time: 2.0 },
        { speaker_label: "CHILD", text: "play train .", start_time: 2.5, end_time: 3.5 }
      ];
      const featureSet = extractAllFeatures(utterances, 48);
      
      expect(featureSet.feature_schema_version).toBe("14-feature-schema");
      
      const f = featureSet.features;
      // Core 14-feature schema fields must be present
      expect(f.age_months).toBe(48);
      expect(f.total_utterances).toBe(2);
      expect(f.total_words).toBe(3); // punctuation is excluded from canonical word tokens
      expect(f.mlu).toBeDefined();
      expect(f.ttr).toBeDefined();
      expect(f.unintelligible_count).toBeDefined();
      expect(f.unintelligible_ratio).toBeDefined();
      expect(f.zero_vocalization_count).toBeDefined();
      expect(f.nonverbal_vocalization_count).toBeDefined();
      expect(f.question_ratio).toBeDefined();
      expect(f.echolalia_count).toBeDefined();
      expect(f.echolalia_ratio).toBeDefined();
      expect(f.pronoun_reversal_count).toBeDefined();
      expect(featureSet.core_features).not.toHaveProperty("restricted_interest_words");
      expect(featureSet.optional_indicators).toHaveProperty("restricted_interest_words");
    });
  });

  describe("Case Ownership Filtering", () => {
    const mockCases = [
      { case_id: "CASE-001", owner_user_id: "therapist_a", anonymized_child_code: "CHI-A" },
      { case_id: "CASE-002", owner_user_id: "therapist_a", anonymized_child_code: "CHI-B" },
      { case_id: "CASE-003", owner_user_id: "therapist_b", anonymized_child_code: "CHI-C" }
    ];

    it("should return empty cases when no user is logged in", () => {
      store.setState({ cases: mockCases, currentUser: null });
      const visible = getVisibleCases();
      expect(visible.length).toBe(0);
    });

    it("should filter cases strictly by owner_user_id for therapists", () => {
      store.setState({
        cases: mockCases,
        currentUser: { user_id: "therapist_a", role: "therapist" }
      });
      const visible = getVisibleCases();
      expect(visible.length).toBe(2);
      expect(visible.every(c => c.owner_user_id === "therapist_a")).toBe(true);
    });

    it("should bypass filtering and return all cases for admin user", () => {
      store.setState({
        cases: mockCases,
        currentUser: { user_id: "admin_001", role: "admin" }
      });
      const visible = getVisibleCases();
      expect(visible.length).toBe(3);
    });
  });
});
