export function createLinguisticFeatureSet({
  feature_id,
  session_id,
  feature_schema_version = "14-feature-schema",
  features = {},
  core_features = null,
  optional_indicators = null,
  created_at = new Date().toISOString()
}) {
  const defaultFeatures = {
    age_months: 0,
    total_utterances: 0,
    mlu: 0.0,
    mluw: 0.0,
    ttr: 0.0,
    total_words: 0,
    unintelligible_count: 0,
    unintelligible_ratio: 0.0,
    zero_vocalization_count: 0,
    nonverbal_vocalization_count: 0,
    question_ratio: 0.0,
    echolalia_count: 0,
    echolalia_ratio: 0.0,
    pronoun_reversal_count: 0
  };

  const defaultOptionalIndicators = {
    pause_count: 0,
    pause_ratio: 0.0,
    therapist_utterances: 0,
    caregiver_utterances: 0,
    turn_taking_count: 0,
    response_latency_avg: 0.0,
    restricted_interest_words: 0
  };
  const sourceCore = core_features || features;
  const sourceOptional = optional_indicators || features;
  const normalizedCore = Object.keys(defaultFeatures).reduce((rows, key) => {
    rows[key] = sourceCore[key] ?? defaultFeatures[key];
    return rows;
  }, {});
  const normalizedOptional = Object.keys(defaultOptionalIndicators).reduce((rows, key) => {
    rows[key] = sourceOptional[key] ?? defaultOptionalIndicators[key];
    return rows;
  }, {});

  return {
    feature_id,
    session_id,
    feature_schema_version,
    core_features: normalizedCore,
    optional_indicators: normalizedOptional,
    features: { ...normalizedCore, ...normalizedOptional },
    created_at
  };
}
