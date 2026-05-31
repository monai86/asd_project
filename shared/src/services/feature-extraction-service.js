import { createLinguisticFeatureSet } from "../models/LinguisticFeatureSet.js";

export const CORE_14_FEATURE_KEYS = [
  "age_months",
  "total_utterances",
  "mlu",
  "mluw",
  "ttr",
  "total_words",
  "unintelligible_count",
  "unintelligible_ratio",
  "zero_vocalization_count",
  "nonverbal_vocalization_count",
  "question_ratio",
  "echolalia_count",
  "echolalia_ratio",
  "pronoun_reversal_count"
];

export const OPTIONAL_INDICATOR_KEYS = [
  "pause_count",
  "pause_ratio",
  "therapist_utterances",
  "caregiver_utterances",
  "turn_taking_count",
  "response_latency_avg",
  "restricted_interest_words"
];

const RESTRICTED_INTEREST_LEXICON = [
  "train",
  "trains",
  "wheel",
  "wheels",
  "number",
  "numbers",
  "letter",
  "letters",
  "map",
  "maps",
  "dinosaur",
  "dinosaurs",
  "schedule",
  "schedules"
];

export function tokenizeUtteranceText(text = "") {
  return String(text)
    .toLowerCase()
    .replace(/[^\p{L}\p{N}'-]+/gu, " ")
    .split(/\s+/)
    .filter(Boolean);
}

export function pickFeatureKeys(features = {}, keys = []) {
  return keys.reduce((rows, key) => {
    rows[key] = features[key] ?? 0;
    return rows;
  }, {});
}

export function extractUtteranceCounts(utterances) {
  const counts = { total: utterances.length, child: 0, therapist: 0, caregiver: 0, unknown: 0 };
  utterances.forEach(u => {
    if (u.speaker_label === "CHILD") counts.child++;
    else if (u.speaker_label === "THERAPIST") counts.therapist++;
    else if (u.speaker_label === "CAREGIVER") counts.caregiver++;
    else counts.unknown++;
  });
  return counts;
}

export function extractWordCounts(utterances) {
  let total = 0;
  let child_total = 0;
  utterances.forEach(u => {
    const words = tokenizeUtteranceText(u.text).length;
    total += words;
    if (u.speaker_label === "CHILD") {
      child_total += words;
    }
  });
  return { total, child_total };
}

export function extractMLU(childUtterances) {
  if (childUtterances.length === 0) return 0.0;
  let wordCount = 0;
  childUtterances.forEach(u => {
    wordCount += tokenizeUtteranceText(u.text).length;
  });
  return Number((wordCount / childUtterances.length).toFixed(3));
}

export function extractTTR(childUtterances) {
  const words = childUtterances.flatMap(u => tokenizeUtteranceText(u.text));
  if (words.length === 0) return 0.0;
  const uniqueWords = new Set(words);
  return Number((uniqueWords.size / words.length).toFixed(3));
}

export function extractRepeatedWords(childUtterances) {
  let count = 0;
  const candidates = [];
  childUtterances.forEach(u => {
    const words = tokenizeUtteranceText(u.text);
    for (let i = 0; i < words.length - 1; i++) {
      if (words[i] === words[i + 1]) {
        count++;
        candidates.push(words[i]);
      }
    }
  });
  return { count, candidates };
}

export function extractQuestionCount(utterances) {
  return utterances.filter(u => u.text.includes("?")).length;
}

export function extractResponseLatency(utterances) {
  const latencies = [];
  for (let i = 0; i < utterances.length - 1; i++) {
    const current = utterances[i];
    const next = utterances[i + 1];
    if (current.end_time !== null && next.start_time !== null) {
      latencies.push(Number((next.start_time - current.end_time).toFixed(2)));
    }
  }
  const avg = latencies.length ? Number((latencies.reduce((a, b) => a + b, 0) / latencies.length).toFixed(2)) : 0.0;
  return { avg, values: latencies };
}

export function extractTurnTaking(utterances) {
  let count = 0;
  for (let i = 0; i < utterances.length - 1; i++) {
    if (utterances[i].speaker_label !== utterances[i + 1].speaker_label) {
      count++;
    }
  }
  const counts = extractUtteranceCounts(utterances);
  const adultCount = counts.therapist + counts.caregiver;
  const childToAdultRatio = adultCount ? Number((counts.child / adultCount).toFixed(2)) : 0.0;

  return { count, childToAdultRatio };
}

export function extractPronounUsage(childUtterances) {
  let count = 0;
  const reversalCandidates = [];
  childUtterances.forEach(u => {
    const text = u.text.toLowerCase();
    if (text.startsWith("you want") || text.startsWith("you like")) {
      count++;
      reversalCandidates.push(u.text);
    }
  });
  return { count, reversalCandidates };
}

export function extractEcholaliaCandidates(utterances) {
  let count = 0;
  const candidates = [];

  for (let i = 1; i < utterances.length; i++) {
    const prev = utterances[i - 1];
    const curr = utterances[i];

    if (curr.speaker_label === "CHILD" && prev.speaker_label !== "CHILD") {
      const prevWords = new Set(tokenizeUtteranceText(prev.text));
      const currWords = tokenizeUtteranceText(curr.text);

      const overlapping = currWords.filter(w => prevWords.has(w));
      if (overlapping.length > 0 && currWords.length <= 3) {
        count++;
        candidates.push({ childText: curr.text, echoedWords: overlapping });
      }
    }
  }
  return { count, candidates };
}

export function extractPauses(utterances) {
  let count = 0;
  let totalDuration = 0.0;

  for (let i = 0; i < utterances.length - 1; i++) {
    const current = utterances[i];
    const next = utterances[i + 1];
    if (current.end_time !== null && next.start_time !== null) {
      const diff = next.start_time - current.end_time;
      if (diff > 1.5) {
        count++;
        totalDuration += diff;
      }
    }
  }

  return {
    count,
    avgDuration: count ? Number((totalDuration / count).toFixed(2)) : 0.0
  };
}

export function extractRestrictedInterestWords(childUtterances, lexicon = RESTRICTED_INTEREST_LEXICON) {
  const restrictedWords = new Set(lexicon.map(word => word.toLowerCase()));
  return childUtterances.reduce((count, utterance) => {
    return count + tokenizeUtteranceText(utterance.text).filter(word => restrictedWords.has(word)).length;
  }, 0);
}

export function extractAllFeatures(utterances, ageMonths = 48) {
  const childUtterances = utterances.filter(u => u.speaker_label === "CHILD");
  const mlu = extractMLU(childUtterances);
  const ttr = extractTTR(childUtterances);
  const turns = extractTurnTaking(utterances);
  const pronouns = extractPronounUsage(childUtterances);
  const echo = extractEcholaliaCandidates(utterances);
  const response = extractResponseLatency(utterances);
  const pauses = extractPauses(utterances);
  const uttCounts = extractUtteranceCounts(utterances);
  const wordCounts = extractWordCounts(utterances);
  const unintelligibleCount = childUtterances.filter(u => /\b(?:xxx|yyy)\b/i.test(u.text)).length;
  const zeroVocalizationCount = childUtterances.filter(u => /^(0|0\s+\.)$/.test(u.text.trim())).length;
  const questionCount = childUtterances.filter(u => u.text.includes("?")).length;

  const coreFeatures = {
    age_months: ageMonths,
    total_utterances: childUtterances.length,
    mlu: mlu,
    mluw: mlu,
    ttr: ttr,
    total_words: wordCounts.child_total,
    unintelligible_count: unintelligibleCount,
    unintelligible_ratio: childUtterances.length ? Number((unintelligibleCount / childUtterances.length).toFixed(3)) : 0.0,
    zero_vocalization_count: zeroVocalizationCount,
    nonverbal_vocalization_count: childUtterances.filter(u => u.text.includes("&=")).length,
    question_ratio: childUtterances.length ? Number((questionCount / childUtterances.length).toFixed(3)) : 0.0,
    echolalia_count: echo.count,
    echolalia_ratio: childUtterances.length ? Number((echo.count / childUtterances.length).toFixed(3)) : 0.0,
    pronoun_reversal_count: pronouns.count
  };
  const optionalIndicators = {
    pause_count: pauses.count,
    pause_ratio: childUtterances.length ? Number((pauses.count / childUtterances.length).toFixed(3)) : 0.0,
    therapist_utterances: uttCounts.therapist,
    caregiver_utterances: uttCounts.caregiver,
    turn_taking_count: turns.count,
    response_latency_avg: response.avg,
    restricted_interest_words: extractRestrictedInterestWords(childUtterances)
  };

  const featureId = `FEATURE-${String(Math.random()).slice(2, 6)}`;

  return createLinguisticFeatureSet({
    feature_id: featureId,
    session_id: utterances[0]?.session_id || "SESSION-NEW",
    core_features: pickFeatureKeys(coreFeatures, CORE_14_FEATURE_KEYS),
    optional_indicators: pickFeatureKeys(optionalIndicators, OPTIONAL_INDICATOR_KEYS)
  });
}
