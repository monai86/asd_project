import { createLinguisticFeatureSet } from "../models/LinguisticFeatureSet.js";

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
    const words = u.text.split(/\s+/).filter(Boolean).length;
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
    wordCount += u.text.split(/\s+/).filter(Boolean).length;
  });
  return Number((wordCount / childUtterances.length).toFixed(3));
}

export function extractTTR(childUtterances) {
  const words = childUtterances.flatMap(u =>
    u.text.toLowerCase().split(/\s+/).map(w => w.replace(/[.,?!]/g, "")).filter(Boolean)
  );
  if (words.length === 0) return 0.0;
  const uniqueWords = new Set(words);
  return Number((uniqueWords.size / words.length).toFixed(3));
}

export function extractRepeatedWords(childUtterances) {
  let count = 0;
  const candidates = [];
  childUtterances.forEach(u => {
    const words = u.text.toLowerCase().split(/\s+/).map(w => w.replace(/[.,?!]/g, "")).filter(Boolean);
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
      const prevWords = new Set(prev.text.toLowerCase().split(/\s+/).map(w => w.replace(/[.,?!]/g, "")).filter(Boolean));
      const currWords = curr.text.toLowerCase().split(/\s+/).map(w => w.replace(/[.,?!]/g, "")).filter(Boolean);

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

export function extractAllFeatures(utterances, ageMonths = 48) {
  const childUtterances = utterances.filter(u => u.speaker_label === "CHILD");
  const mlu = extractMLU(childUtterances);
  const ttr = extractTTR(childUtterances);
  const repeated = extractRepeatedWords(childUtterances);
  const turns = extractTurnTaking(utterances);
  const pronouns = extractPronounUsage(childUtterances);
  const echo = extractEcholaliaCandidates(utterances);
  const response = extractResponseLatency(utterances);
  const pauses = extractPauses(utterances);
  const uttCounts = extractUtteranceCounts(utterances);
  const wordCounts = extractWordCounts(utterances);

  const features = {
    age_months: ageMonths,
    total_utterances: childUtterances.length,
    mlu: mlu,
    mluw: mlu,
    ttr: ttr,
    total_words: wordCounts.child_total,
    unintelligible_count: childUtterances.filter(u => u.text.includes("xxx") || u.text.includes("yyy")).length,
    unintelligible_ratio: childUtterances.length ? Number((childUtterances.filter(u => u.text.includes("xxx") || u.text.includes("yyy")).length / childUtterances.length).toFixed(3)) : 0.0,
    zero_vocalization_count: childUtterances.filter(u => u.text.trim() === "0 ." || u.text.trim() === "0").length,
    nonverbal_vocalization_count: childUtterances.filter(u => u.text.includes("&=")).length,
    question_ratio: childUtterances.length ? Number((childUtterances.filter(u => u.text.includes("?")).length / childUtterances.length).toFixed(3)) : 0.0,
    echolalia_count: echo.count,
    echolalia_ratio: childUtterances.length ? Number((echo.count / childUtterances.length).toFixed(3)) : 0.0,
    pronoun_reversal_count: pronouns.count,
    pause_count: pauses.count,
    pause_ratio: childUtterances.length ? Number((pauses.count / childUtterances.length).toFixed(3)) : 0.0,
    therapist_utterances: uttCounts.therapist,
    caregiver_utterances: uttCounts.caregiver,
    turn_taking_count: turns.count,
    response_latency_avg: response.avg
  };

  const featureId = `FEATURE-${String(Math.random()).slice(2, 6)}`;

  return createLinguisticFeatureSet({
    feature_id: featureId,
    session_id: utterances[0]?.session_id || "SESSION-NEW",
    features
  });
}
