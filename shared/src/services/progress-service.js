export function getChildProgressFromData({ caseItem, sessions, extractedFeatureOutputs, aiDecisionOutputs, goals }) {
  if (!caseItem) return null;

  const sortedSessions = sessions.sort((a, b) => a.session_date.localeCompare(b.session_date));

  const sessionTrend = sortedSessions.map(s => {
    const features = extractedFeatureOutputs[s.session_id]?.features || {};
    const aiOutput = aiDecisionOutputs[s.session_id] || {};
    return {
      session_id: s.session_id,
      date: s.date || s.session_date,
      score: aiOutput.screening_support_score ?? 0.0,
      mlu: features.mlu ?? 0.0,
      ttr: features.ttr ?? 0.0,
      total_utterances: features.total_utterances ?? 0,
      echolalia_ratio: features.echolalia_ratio ?? 0.0,
      turn_taking_count: features.turn_taking_count ?? 0,
      review_status: s.therapist_review_status
    };
  });

  const caseGoals = goals.filter(g => g.case_id === caseItem.case_id);

  return {
    caseItem,
    sessions: sessionTrend,
    goals: caseGoals,
    wording: "language sample trend, requires clinical interpretation"
  };
}
