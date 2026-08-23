/**
 * Single source of truth for the workflow step names shared across the Session
 * workspace views (intake → transcript → findings → report). Views import these
 * constants so one action or concept always carries one label, instead of each
 * view inventing its own phrasing for the same step.
 *
 * Canonical step vocabulary:
 * - Feature extraction: the therapist action that derives language-sample
 *   features from the reviewed, attested transcript.
 * - Evidence review: the optional reference-evidence review generated after
 *   feature extraction and surfaced on the Findings view.
 * - Findings: the view where extracted features, evidence review, and review
 *   cues are examined before report drafting.
 */

/** The therapist action that runs language-sample feature extraction. */
export const EXTRACT_FEATURES_ACTION = "Extract language-sample features";

/** The noun for the feature-extraction step and its status. */
export const FEATURE_EXTRACTION_NOUN = "Feature extraction";

/** The therapist action that generates the evidence review. */
export const GENERATE_EVIDENCE_REVIEW_ACTION = "Generate evidence review";

/** The noun for the optional evidence-review step. */
export const EVIDENCE_REVIEW_NOUN = "Evidence review";

/** The therapist action that generates the editable report draft. */
export const GENERATE_REPORT_ACTION = "Generate report draft";
