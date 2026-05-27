/**
 * scoring-service.js — Developmental Concern-Level Calculation
 *
 * Weighted scoring across three categories with age-based adjustment.
 * Produces a 0-100 concern score mapped to low / moderate / high levels.
 *
 * IMPORTANT: This is a screening support tool — results are "concern levels",
 * NOT diagnoses. All language must remain safe and non-clinical.
 */

// ─── Constants ──────────────────────────────────────────────────────────────

/** Category weights (must sum to 1.0) */
const WEIGHTS = {
  speech:     0.35,
  social:     0.40,
  repetitive: 0.25,
};

/** Maximum Likert value per question (5-point scale, 0-4 after adjustment) */
const MAX_PER_Q = 4;

/** Number of questions per category */
const Q_COUNTS = { speech: 5, social: 5, repetitive: 4 };

/** Concern-level thresholds on 0-100 scale */
const THRESHOLDS = { low: 33, moderate: 66 };

/**
 * Age-based adjustment multipliers.
 * Younger children naturally show more developmental variance,
 * so we reduce their scores slightly to avoid over-flagging.
 */
const AGE_ADJUSTMENTS = {
  under12: 0.70,
  m12_18:  0.78,
  m18_24:  0.85,
  m24_36:  0.92,
  m36_48:  0.96,
  m48_60:  0.98,
  over60:  1.00,
};

/** Question metadata (for feature breakdown) */
const QUESTION_META = {
  speech: [
    { nameEn: 'Verbal Communication',   nameTh: 'การสื่อสารด้วยคำพูด',   key: 'speechQ1' },
    { nameEn: 'Sentence Length',         nameTh: 'ความยาวประโยค',         key: 'speechQ2' },
    { nameEn: 'Word Variety',            nameTh: 'ความหลากหลายของคำ',     key: 'speechQ3' },
    { nameEn: 'Speech Intelligibility',  nameTh: 'ความชัดเจนของคำพูด',     key: 'speechQ4' },
    { nameEn: 'Verbal Responsiveness',   nameTh: 'การตอบสนองด้วยคำพูด',   key: 'speechQ5' },
  ],
  social: [
    { nameEn: 'Eye Contact',            nameTh: 'การสบตา',               key: 'socialQ1' },
    { nameEn: 'Name Response',          nameTh: 'การตอบชื่อ',             key: 'socialQ2' },
    { nameEn: 'Initiating Conversation', nameTh: 'การเริ่มบทสนทนา',       key: 'socialQ3' },
    { nameEn: 'Interest in Peers',       nameTh: 'ความสนใจในเด็กอื่น',     key: 'socialQ4' },
    { nameEn: 'Gesture Use',            nameTh: 'การใช้ท่าทาง',           key: 'socialQ5' },
  ],
  repetitive: [
    { nameEn: 'Echolalia',              nameTh: 'การพูดตาม (Echolalia)',  key: 'repetitiveQ1' },
    { nameEn: 'Pronoun Confusion',      nameTh: 'ความสับสนสรรพนาม',       key: 'repetitiveQ2' },
    { nameEn: 'Routine Attachment',     nameTh: 'การยึดติดกิจวัตร',        key: 'repetitiveQ3' },
    { nameEn: 'Repetitive Movements',   nameTh: 'การเคลื่อนไหวซ้ำๆ',     key: 'repetitiveQ4' },
  ],
};


// ─── Core Scoring ───────────────────────────────────────────────────────────

/**
 * Compute a raw 0-100 score for a single category.
 * Each question response is 1-5 (Likert); we convert to 0-4.
 *
 * @param {number[]} responses  Array of Likert values (1-5)
 * @param {number}   qCount     Expected number of questions
 * @returns {number} 0-100 normalised category score
 */
function categoryScore(responses, qCount) {
  if (!responses || responses.length === 0) return 0;
  const maxRaw = qCount * MAX_PER_Q;
  const raw = responses.reduce((sum, v) => sum + (Number(v) - 1), 0);
  return (raw / maxRaw) * 100;
}

/**
 * Get the concern level label for a given 0-100 score.
 * @param {number} score
 * @returns {'low'|'moderate'|'high'}
 */
function levelFromScore(score) {
  if (score <= THRESHOLDS.low) return 'low';
  if (score <= THRESHOLDS.moderate) return 'moderate';
  return 'high';
}

/**
 * Get the concern level label for a single question (0-4).
 * @param {number} raw  0-4 value
 * @returns {'low'|'moderate'|'high'}
 */
function questionLevel(raw) {
  if (raw <= 1) return 'low';
  if (raw <= 2) return 'moderate';
  return 'high';
}


// ─── Public API ─────────────────────────────────────────────────────────────

/**
 * Calculate the developmental concern level from screening answers.
 *
 * @param {Object} answers
 * @param {string} answers.ageRange        e.g. 'under12', 'm24_36'
 * @param {Object} answers.questions
 * @param {number[]} answers.questions.speech      5 values, each 1-5
 * @param {number[]} answers.questions.social      5 values, each 1-5
 * @param {number[]} answers.questions.repetitive  4 values, each 1-5
 * @param {string}  [answers.notes]        Optional free-text notes
 *
 * @returns {Object} result
 */
export function calculateConcernLevel(answers) {
  const { ageRange, questions, notes } = answers;

  // 1. Category scores (0-100 each)
  const speechScore     = categoryScore(questions.speech,     Q_COUNTS.speech);
  const socialScore     = categoryScore(questions.social,     Q_COUNTS.social);
  const repetitiveScore = categoryScore(questions.repetitive, Q_COUNTS.repetitive);

  // 2. Weighted composite score
  let composite =
    speechScore     * WEIGHTS.speech +
    socialScore     * WEIGHTS.social +
    repetitiveScore * WEIGHTS.repetitive;

  // 3. Age adjustment
  const ageFactor = AGE_ADJUSTMENTS[ageRange] ?? 1.0;
  composite *= ageFactor;

  // Clamp to 0-100
  const overallScore = Math.round(Math.min(100, Math.max(0, composite)));

  // 4. Determine concern level
  const concernLevel = levelFromScore(overallScore);

  // 5. Category score objects
  const categoryScores = {
    speech:     Math.round(speechScore),
    social:     Math.round(socialScore),
    repetitive: Math.round(repetitiveScore),
  };

  // 6. Feature breakdown (per question)
  const featureBreakdown = [];
  for (const cat of ['speech', 'social', 'repetitive']) {
    const meta = QUESTION_META[cat];
    const resps = questions[cat] || [];
    meta.forEach((m, i) => {
      const raw = Math.max(0, Number(resps[i] || 1) - 1); // 0-4
      featureBreakdown.push({
        name:        m.nameEn,
        nameTh:      m.nameTh,
        key:         m.key,
        category:    cat,
        score:       raw,
        maxScore:    MAX_PER_Q,
        level:       questionLevel(raw),
        description: '',
      });
    });
  }

  // 7. Recommendations
  const recommendations = getRecommendations(concernLevel, categoryScores);

  return {
    overallScore,
    concernLevel,
    categoryScores,
    featureBreakdown,
    recommendations,
    ageRange: ageRange || 'unknown',
    notes: notes || '',
  };
}

/**
 * Generate an array of recommendation strings based on concern level
 * and per-category scores. Uses safe, non-diagnostic language throughout.
 *
 * @param {'low'|'moderate'|'high'} concernLevel
 * @param {{ speech: number, social: number, repetitive: number }} catScores
 * @returns {string[]}
 */
export function getRecommendations(concernLevel, catScores) {
  const recs = [];

  // ── Universal recommendation ──
  recs.push(
    'If you have any concerns about your child\'s development, consulting with a qualified professional is always a positive step.'
  );

  // ── Level-specific ──
  if (concernLevel === 'low') {
    recs.push(
      'This result suggests that the observed patterns are generally within typical developmental ranges.'
    );
    recs.push(
      'You may want to continue monitoring your child\'s communication development and revisit this tool periodically.'
    );
  }

  if (concernLevel === 'moderate') {
    recs.push(
      'This result suggests some areas that may benefit from further professional evaluation.'
    );
    recs.push(
      'We recommend discussing your observations with a developmental pediatrician or speech-language pathologist.'
    );
  }

  if (concernLevel === 'high') {
    recs.push(
      'This result suggests several areas of developmental concern that may indicate the need for a comprehensive professional evaluation.'
    );
    recs.push(
      'We strongly recommend scheduling an appointment with a developmental specialist, such as a developmental pediatrician, speech-language pathologist, or child psychologist.'
    );
    recs.push(
      'Early consultation and support can make a meaningful difference in a child\'s development.'
    );
  }

  // ── Category-specific guidance ──
  if (catScores.speech > THRESHOLDS.moderate) {
    recs.push(
      'Speech and language scores suggest this may be an area to discuss with a speech-language pathologist.'
    );
  } else if (catScores.speech > THRESHOLDS.low) {
    recs.push(
      'Some speech and language observations may benefit from monitoring or professional input.'
    );
  }

  if (catScores.social > THRESHOLDS.moderate) {
    recs.push(
      'Social communication scores suggest that a professional evaluation of social interaction skills may be beneficial.'
    );
  } else if (catScores.social > THRESHOLDS.low) {
    recs.push(
      'Some social communication observations may warrant further discussion with a professional.'
    );
  }

  if (catScores.repetitive > THRESHOLDS.moderate) {
    recs.push(
      'Observed repetitive behaviors may indicate the need for professional consultation to better understand your child\'s behavior patterns.'
    );
  }

  return recs;
}
