import { describe, expect, it } from "vitest";

import {
  EVIDENCE_REVIEW_NOUN,
  EXTRACT_FEATURES_ACTION,
  FEATURE_EXTRACTION_NOUN,
  GENERATE_EVIDENCE_REVIEW_ACTION,
  GENERATE_REPORT_ACTION,
} from "@/lib/workflow-glossary";

describe("workflow glossary", () => {
  it("keeps one canonical action label for feature extraction", () => {
    expect(EXTRACT_FEATURES_ACTION).toBe("Extract language-sample features");
  });

  it("keeps one canonical noun for feature extraction", () => {
    expect(FEATURE_EXTRACTION_NOUN).toBe("Feature extraction");
  });

  it("keeps one canonical action label for the evidence review", () => {
    expect(GENERATE_EVIDENCE_REVIEW_ACTION).toBe("Generate evidence review");
  });

  it("keeps one canonical noun for the evidence review", () => {
    expect(EVIDENCE_REVIEW_NOUN).toBe("Evidence review");
  });

  it("keeps one canonical action label for the report draft", () => {
    expect(GENERATE_REPORT_ACTION).toBe("Generate report draft");
  });

  it("distinguishes the feature-extraction and evidence-review steps", () => {
    expect(EXTRACT_FEATURES_ACTION.toLowerCase()).not.toContain(EVIDENCE_REVIEW_NOUN.toLowerCase());
    expect(GENERATE_EVIDENCE_REVIEW_ACTION.toLowerCase()).toContain(EVIDENCE_REVIEW_NOUN.toLowerCase());
    expect(GENERATE_EVIDENCE_REVIEW_ACTION.toLowerCase()).not.toContain(FEATURE_EXTRACTION_NOUN.toLowerCase());
  });
});
