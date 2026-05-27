/**
 * screening-form.js — Multi-step Screening Questionnaire
 *
 * Manages the 5-step form flow, Likert question rendering,
 * validation, and sessionStorage handoff to the results page.
 *
 * Safety: All text uses non-diagnostic screening support language.
 */

import { getCurrentLang, t, applyTranslations } from './i18n.js';
import { calculateConcernLevel } from '@shared/services/scoring-service.js';
import { VoiceRecorder, getVoiceErrorMessage } from './voice-recorder.js';
import { analyzeTranscript } from '@shared/services/speech-analysis-service.js';

// ─── Question definitions ───────────────────────────────────────────────────

const LIKERT_LABELS = [
  { value: 1, en: 'Never',         th: 'ไม่เคย' },
  { value: 2, en: 'Rarely',        th: 'นานๆ ครั้ง' },
  { value: 3, en: 'Sometimes',     th: 'บางครั้ง' },
  { value: 4, en: 'Often',         th: 'บ่อย' },
  { value: 5, en: 'Almost Always', th: 'เกือบตลอด' },
];

/** Speech & Language questions (Step 2) */
const SPEECH_QUESTIONS = [
  {
    id: 'speechQ1',
    en: 'How much does your child communicate verbally?',
    th: 'บุตรหลานของคุณสื่อสารด้วยคำพูดมากน้อยเพียงใด?',
    // Reversed: "a lot" = low concern (1), "very little" = high concern (5)
    reversed: true,
    likertEn: ['A lot', 'Quite a bit', 'Moderately', 'A little', 'Very little'],
    likertTh: ['มาก', 'ค่อนข้างมาก', 'ปานกลาง', 'น้อย', 'น้อยมาก'],
  },
  {
    id: 'speechQ2',
    en: 'How long are your child\'s typical sentences?',
    th: 'ประโยคที่บุตรหลานของคุณพูดโดยทั่วไปยาวเท่าใด?',
    reversed: true,
    likertEn: ['4+ words', '3 words', '2 words', 'Single words', 'No words yet'],
    likertTh: ['4 คำขึ้นไป', '3 คำ', '2 คำ', 'คำเดียว', 'ยังไม่พูดเป็นคำ'],
  },
  {
    id: 'speechQ3',
    en: 'Does your child use a variety of different words?',
    th: 'บุตรหลานของคุณใช้คำศัพท์หลากหลายหรือไม่?',
    reversed: true,
    likertEn: ['Wide variety', 'Good variety', 'Some variety', 'Limited', 'Very limited'],
    likertTh: ['หลากหลายมาก', 'หลากหลายดี', 'หลากหลายพอสมควร', 'จำกัด', 'จำกัดมาก'],
  },
  {
    id: 'speechQ4',
    en: 'How often is your child\'s speech difficult to understand?',
    th: 'คำพูดของบุตรหลานของคุณเข้าใจยากบ่อยแค่ไหน?',
    reversed: false,
  },
  {
    id: 'speechQ5',
    en: 'Does your child sometimes not respond verbally when spoken to?',
    th: 'บุตรหลานของคุณบางครั้งไม่ตอบสนองด้วยคำพูดเมื่อถูกพูดด้วยหรือไม่?',
    reversed: false,
  },
];

/** Social Communication questions (Step 3) */
const SOCIAL_QUESTIONS = [
  {
    id: 'socialQ1',
    en: 'Does your child make eye contact during conversations?',
    th: 'บุตรหลานของคุณสบตาระหว่างการสนทนาหรือไม่?',
    reversed: true,
    likertEn: ['Always', 'Often', 'Sometimes', 'Rarely', 'Never'],
    likertTh: ['เสมอ', 'บ่อย', 'บางครั้ง', 'นานๆ ครั้ง', 'ไม่เคย'],
  },
  {
    id: 'socialQ2',
    en: 'Does your child respond to their name being called?',
    th: 'บุตรหลานของคุณตอบสนองเมื่อถูกเรียกชื่อหรือไม่?',
    reversed: true,
    likertEn: ['Always', 'Often', 'Sometimes', 'Rarely', 'Never'],
    likertTh: ['เสมอ', 'บ่อย', 'บางครั้ง', 'นานๆ ครั้ง', 'ไม่เคย'],
  },
  {
    id: 'socialQ3',
    en: 'Does your child ask questions or start conversations?',
    th: 'บุตรหลานของคุณถามคำถามหรือเริ่มบทสนทนาเองหรือไม่?',
    reversed: true,
    likertEn: ['Frequently', 'Often', 'Sometimes', 'Rarely', 'Never'],
    likertTh: ['บ่อยมาก', 'บ่อย', 'บางครั้ง', 'นานๆ ครั้ง', 'ไม่เคย'],
  },
  {
    id: 'socialQ4',
    en: 'Does your child show interest in other children?',
    th: 'บุตรหลานของคุณแสดงความสนใจในเด็กคนอื่นหรือไม่?',
    reversed: true,
    likertEn: ['Very interested', 'Interested', 'Somewhat', 'Little interest', 'No interest'],
    likertTh: ['สนใจมาก', 'สนใจ', 'สนใจบ้าง', 'สนใจน้อย', 'ไม่สนใจ'],
  },
  {
    id: 'socialQ5',
    en: 'Does your child use gestures (pointing, waving) to communicate?',
    th: 'บุตรหลานของคุณใช้ท่าทาง (ชี้, โบกมือ) ในการสื่อสารหรือไม่?',
    reversed: true,
    likertEn: ['Frequently', 'Often', 'Sometimes', 'Rarely', 'Never'],
    likertTh: ['บ่อยมาก', 'บ่อย', 'บางครั้ง', 'นานๆ ครั้ง', 'ไม่เคย'],
  },
];

/** Repetitive Behavior questions (Step 4) */
const REPETITIVE_QUESTIONS = [
  {
    id: 'repetitiveQ1',
    en: 'Does your child repeat words or phrases others say (echo)?',
    th: 'บุตรหลานของคุณพูดซ้ำคำหรือวลีที่คนอื่นพูด (พูดตาม) หรือไม่?',
    reversed: false,
  },
  {
    id: 'repetitiveQ2',
    en: 'Does your child mix up pronouns (I/you, me/you)?',
    th: 'บุตรหลานของคุณสับสนการใช้สรรพนาม (ฉัน/คุณ) หรือไม่?',
    reversed: false,
  },
  {
    id: 'repetitiveQ3',
    en: 'Does your child show strong attachment to routines or specific objects?',
    th: 'บุตรหลานของคุณยึดติดกับกิจวัตรหรือสิ่งของเฉพาะอย่างมากหรือไม่?',
    reversed: false,
  },
  {
    id: 'repetitiveQ4',
    en: 'Does your child have repetitive movements (hand flapping, rocking)?',
    th: 'บุตรหลานของคุณมีการเคลื่อนไหวซ้ำๆ (สะบัดมือ, โยกตัว) หรือไม่?',
    reversed: false,
  },
];

// ─── AGE RANGE MAPPING ──────────────────────────────────────────────────────

const AGE_MAP = {
  '0-12':  'under12',
  '12-18': 'm12_18',
  '18-24': 'm18_24',
  '24-36': 'm24_36',
  '36-48': 'm36_48',
  '48-60': 'm48_60',
  '60+':   'over60',
};

// ─── State ──────────────────────────────────────────────────────────────────

let currentStep = 1;
const TOTAL_STEPS = 5;
let voiceObservations = null;

// ─── DOM Helpers ────────────────────────────────────────────────────────────

/**
 * Render a set of Likert questions into a container.
 */
function renderQuestions(containerId, questions) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const lang = getCurrentLang();
  container.innerHTML = '';

  questions.forEach((q, idx) => {
    const group = document.createElement('div');
    group.className = 'question-item';
    group.setAttribute('data-question-id', q.id);

    // Question text
    const label = document.createElement('p');
    label.className = 'question-text';
    label.textContent = `${idx + 1}. ${lang === 'th' ? q.th : q.en}`;
    label.setAttribute('data-q-en', q.en);
    label.setAttribute('data-q-th', q.th);
    label.setAttribute('data-q-idx', idx + 1);
    group.appendChild(label);

    // Likert options
    const likertGroup = document.createElement('div');
    likertGroup.className = 'likert-group';
    likertGroup.setAttribute('role', 'radiogroup');
    likertGroup.setAttribute('aria-label', lang === 'th' ? q.th : q.en);

    LIKERT_LABELS.forEach((opt, optIdx) => {
      const optLabel = document.createElement('label');
      optLabel.className = 'likert-option';

      const radio = document.createElement('input');
      radio.type = 'radio';
      radio.name = q.id;
      radio.value = opt.value;
      radio.className = 'likert-radio';
      radio.setAttribute('aria-label', lang === 'th' ? opt.th : opt.en);

      const text = document.createElement('span');
      text.className = 'likert-text';

      // Use custom labels if available, else default Likert
      if (q.likertEn && q.likertTh) {
        text.textContent = lang === 'th' ? q.likertTh[optIdx] : q.likertEn[optIdx];
        text.setAttribute('data-likert-en', q.likertEn[optIdx]);
        text.setAttribute('data-likert-th', q.likertTh[optIdx]);
      } else {
        text.textContent = lang === 'th' ? opt.th : opt.en;
        text.setAttribute('data-likert-en', opt.en);
        text.setAttribute('data-likert-th', opt.th);
      }

      optLabel.appendChild(radio);
      
      const emojiSpan = document.createElement('span');
      emojiSpan.className = 'likert-emoji';
      const emojis = ['😊', '🙂', '😐', '🙁', '😢'];
      emojiSpan.textContent = emojis[optIdx];
      optLabel.appendChild(emojiSpan);
      
      optLabel.appendChild(text);
      likertGroup.appendChild(optLabel);

      // Selection visual feedback
      radio.addEventListener('change', () => {
        likertGroup.querySelectorAll('.likert-option').forEach(o => o.classList.remove('selected'));
        optLabel.classList.add('selected');
        // Remove any error styling
        group.classList.remove('has-error');
      });
    });

    group.appendChild(likertGroup);
    container.appendChild(group);
  });
}

/**
 * Show a specific step and hide others.
 */
function showStep(step) {
  currentStep = step;

  // Toggle step panels
  document.querySelectorAll('.form-step').forEach(el => {
    const s = parseInt(el.dataset.step);
    el.classList.toggle('active', s === step);
  });

  // Update progress bar
  const fill = document.getElementById('progress-fill');
  const fillLeft = document.getElementById('progress-fill-left');
  const percentText = document.getElementById('progress-percent');
  const percent = Math.round((step / TOTAL_STEPS) * 100);
  if (fill) {
    fill.style.width = `${percent}%`;
  }
  if (fillLeft) {
    fillLeft.style.width = `${percent}%`;
  }
  if (percentText) {
    percentText.textContent = `${percent}% completed`;
  }

  // Show/hide child summary card based on step
  const childCard = document.getElementById('child-summary-card');
  if (childCard) {
    if (step > 1) {
      childCard.style.display = 'block';
      const ageSelect = document.getElementById('age-range');
      const sexRadio = document.querySelector('input[name="sex"]:checked');
      
      const ageText = ageSelect ? ageSelect.options[ageSelect.selectedIndex].text : '';
      const sexVal = sexRadio ? sexRadio.value : '';
      const sexLabel = sexVal === 'male' ? 'Male' : sexVal === 'female' ? 'Female' : '';
      
      const ageEl = document.getElementById('summary-child-age');
      if (ageEl) {
        ageEl.textContent = `${ageText} ${sexLabel ? '• ' + sexLabel : ''}`;
      }
    } else {
      childCard.style.display = 'none';
    }
  }

  // Update step dots
  document.querySelectorAll('.step-dot').forEach(dot => {
    const s = parseInt(dot.dataset.step);
    dot.classList.toggle('active', s === step);
    dot.classList.toggle('completed', s < step);
  });

  // Toggle prev/next/submit buttons
  const prevBtn = document.getElementById('btn-prev');
  const nextBtn = document.getElementById('btn-next');
  const submitBtn = document.getElementById('btn-submit');

  if (prevBtn) prevBtn.disabled = step === 1;
  if (nextBtn) nextBtn.style.display = step === TOTAL_STEPS ? 'none' : '';
  if (submitBtn) submitBtn.style.display = step === TOTAL_STEPS ? '' : 'none';

  // Scroll to top of form
  document.querySelector('.screening-main')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Validate the current step. Returns true if valid.
 */
function validateStep(step) {
  if (step === 1) {
    const ageSelect = document.getElementById('age-range');
    if (!ageSelect || !ageSelect.value) {
      ageSelect?.classList.add('error');
      document.getElementById('age-error')?.classList.add('visible');
      return false;
    }
    ageSelect.classList.remove('error');
    document.getElementById('age-error')?.classList.remove('visible');
    return true;
  }

  if (step >= 2 && step <= 4) {
    const containerMap = { 2: 'speech-questions', 3: 'social-questions', 4: 'repetitive-questions' };
    const container = document.getElementById(containerMap[step]);
    if (!container) return true;

    const questions = container.querySelectorAll('.question-item');
    let allValid = true;

    questions.forEach(q => {
      const qId = q.dataset.questionId;
      const checked = q.querySelector(`input[name="${qId}"]:checked`);
      if (!checked) {
        q.classList.add('has-error');
        allValid = false;
      } else {
        q.classList.remove('has-error');
      }
    });

    if (!allValid) {
      // Show validation message
      showValidationError(container);
    }

    return allValid;
  }

  // Step 5 (notes) always valid
  return true;
}

/**
 * Show a temporary validation error message.
 */
function showValidationError(container) {
  // Remove existing error
  container.querySelectorAll('.validation-message').forEach(m => m.remove());

  const msg = document.createElement('div');
  msg.className = 'validation-message';
  const lang = getCurrentLang();
  msg.textContent = lang === 'th'
    ? 'กรุณาตอบคำถามทุกข้อก่อนดำเนินการต่อ'
    : 'Please answer all questions before continuing.';

  container.prepend(msg);

  setTimeout(() => msg.remove(), 4000);
}

/**
 * Collect all form responses.
 */
function collectAnswers() {
  const ageSelect = document.getElementById('age-range');
  const ageRange = AGE_MAP[ageSelect?.value] || 'unknown';

  const sexRadio = document.querySelector('input[name="sex"]:checked');
  const sex = sexRadio?.value || 'unspecified';

  // Helper: collect Likert answers for a question set
  function collectCategory(questions) {
    return questions.map(q => {
      const checked = document.querySelector(`input[name="${q.id}"]:checked`);
      let val = checked ? parseInt(checked.value) : 1;
      // For reversed questions (where 1=good, 5=bad is already the scale direction),
      // the Likert labels display from "good" to "bad" (1-5).
      // For non-reversed questions, standard Likert (Never=1 to Always=5) maps directly.
      // Both store raw 1-5; scoring.js handles the interpretation.
      return val;
    });
  }

  const speech = collectCategory(SPEECH_QUESTIONS);
  const social = collectCategory(SOCIAL_QUESTIONS);
  const repetitive = collectCategory(REPETITIVE_QUESTIONS);

  const notes = document.getElementById('observation-notes')?.value || '';
  const transcript = document.getElementById('transcript-input')?.value || '';

  return {
    ageRange,
    ageRangeRaw: ageSelect?.value || '',
    sex,
    questions: { speech, social, repetitive },
    notes,
    transcript,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Handle form submission.
 */
function handleSubmit(e) {
  e.preventDefault();

  // Validate all steps (just the current one — others were validated on advance)
  if (!validateStep(currentStep)) return;

  // Collect answers
  const answers = collectAnswers();

  // Calculate concern level
  const result = calculateConcernLevel(answers);
  if (voiceObservations) {
    result.voiceObservations = voiceObservations;
  }

  // Store the raw answers and result in sessionStorage
  sessionStorage.setItem('screening-answers', JSON.stringify(answers));
  sessionStorage.setItem('screening-result', JSON.stringify(result));

  // Redirect to results view
  window.location.hash = '#results';
}

/**
 * Re-render questions when language changes.
 */
function onLangChange() {
  // Save current selections
  const savedSelections = {};
  document.querySelectorAll('.likert-radio:checked').forEach(radio => {
    savedSelections[radio.name] = radio.value;
  });

  // Re-render
  renderQuestions('speech-questions', SPEECH_QUESTIONS);
  renderQuestions('social-questions', SOCIAL_QUESTIONS);
  renderQuestions('repetitive-questions', REPETITIVE_QUESTIONS);

  // Restore selections
  Object.entries(savedSelections).forEach(([name, value]) => {
    const radio = document.querySelector(`input[name="${name}"][value="${value}"]`);
    if (radio) {
      radio.checked = true;
      radio.closest('.likert-option')?.classList.add('selected');
    }
  });

  // Update question text lang
  document.querySelectorAll('.question-text').forEach(el => {
    const lang = getCurrentLang();
    const idx = el.dataset.qIdx;
    const text = lang === 'th' ? el.dataset.qTh : el.dataset.qEn;
    el.textContent = `${idx}. ${text}`;
  });
}

// ─── Public API ─────────────────────────────────────────────────────────────

export function initScreeningForm() {
  // Render questions
  renderQuestions('speech-questions', SPEECH_QUESTIONS);
  renderQuestions('social-questions', SOCIAL_QUESTIONS);
  renderQuestions('repetitive-questions', REPETITIVE_QUESTIONS);

  // Set initial step
  showStep(1);

  // Edit child info trigger on progress sidebar
  document.getElementById('btn-change-child-info')?.addEventListener('click', () => {
    showStep(1);
  });

  // Next button
  document.getElementById('btn-next')?.addEventListener('click', () => {
    if (validateStep(currentStep)) {
      showStep(currentStep + 1);
    }
  });

  // Previous button
  document.getElementById('btn-prev')?.addEventListener('click', () => {
    if (currentStep > 1) {
      showStep(currentStep - 1);
    }
  });

  // Submit
  document.getElementById('screening-form')?.addEventListener('submit', handleSubmit);

  // Language change listener
  window.addEventListener('langchange', onLangChange);

  // Step dot click navigation
  document.querySelectorAll('.step-dot').forEach(dot => {
    dot.addEventListener('click', () => {
      const target = parseInt(dot.dataset.step);
      // Only allow going back, or forward if current step is valid
      if (target < currentStep || validateStep(currentStep)) {
        showStep(target);
      }
    });
  });

  // Set up voice observer logic
  const recorder = new VoiceRecorder();
  const btnStart = document.getElementById('btn-voice-start');
  const btnStop = document.getElementById('btn-voice-stop');
  const btnClear = document.getElementById('btn-voice-clear');
  const indicator = document.getElementById('voice-recording-indicator');
  const preview = document.getElementById('voice-transcript-preview');
  const summary = document.getElementById('voice-analysis-summary');
  const unsupported = document.getElementById('voice-unsupported');
  const notesTextarea = document.getElementById('observation-notes');

  // Verify support
  if (!recorder.isSupported()) {
    if (unsupported) unsupported.hidden = false;
    if (btnStart) btnStart.hidden = true;
  } else {
    // Setup recorder update streaming
    recorder.onTranscriptUpdate = (text) => {
      if (preview) {
        preview.textContent = text;
        preview.hidden = false;
      }
    };

    if (btnStart) {
      btnStart.addEventListener('click', async () => {
        try {
          const lang = getCurrentLang() === 'th' ? 'th-TH' : 'en-US';
          btnStart.hidden = true;
          if (btnStop) btnStop.hidden = false;
          if (indicator) indicator.hidden = false;
          if (preview) {
            preview.textContent = '';
            preview.hidden = false;
          }
          if (summary) summary.hidden = true;
          
          await recorder.start(lang);
        } catch (err) {
          console.error(err);
          const localizedErr = getVoiceErrorMessage(err, getCurrentLang());
          alert(localizedErr);
          // Restore UI
          btnStart.hidden = false;
          if (btnStop) btnStop.hidden = true;
          if (indicator) indicator.hidden = true;
        }
      });
    }

    if (btnStop) {
      btnStop.addEventListener('click', async () => {
        try {
          if (btnStop) btnStop.hidden = true;
          if (indicator) indicator.hidden = true;
          
          const result = await recorder.stop();
          
          if (result.transcript) {
            const currentLang = getCurrentLang();
            // Run analysis
            voiceObservations = analyzeTranscript(result.transcript, currentLang);
            
            // Show preview
            if (preview) {
              preview.textContent = result.transcript;
              preview.hidden = false;
            }
            
            // Format and show observations box
            if (summary) {
              const obsLines = [];
              const isThai = currentLang === 'th';
              
              obsLines.push(isThai
                ? `ความยาวเฉลี่ย: ${voiceObservations.avgWordsPerUtterance} คำ/ประโยค`
                : `Avg length: ${voiceObservations.avgWordsPerUtterance} words`
              );
              obsLines.push(isThai
                ? `คำศัพท์ทั้งหมด: ${voiceObservations.uniqueWordCount} คำ`
                : `Vocabulary size: ${voiceObservations.uniqueWordCount} words`
              );
              if (voiceObservations.pronounNote) {
                obsLines.push(isThai
                  ? `การใช้สรรพนาม: พบสรรพนามแทนตัวเองในบุคคลอื่น`
                  : `Pronouns: Potential substitute noted`
                );
              }
              if (voiceObservations.echolaliaSignal) {
                obsLines.push(isThai
                  ? `การพูดซ้ำ: พบการพูดซ้ำวลี/ประโยค`
                  : `Repetition: Potential repeating noted`
                );
              }
              
              summary.innerHTML = `
                <strong data-i18n="screening.voiceAnalysisLabel">${t('screening.voiceAnalysisLabel')}</strong>
                <ul style="margin: var(--space-2) 0 0 0; padding-left: var(--space-4); list-style-type: disc;">
                  ${obsLines.map(line => `<li>${line}</li>`).join('')}
                </ul>
              `;
              summary.hidden = false;
            }

            // Append to notes textarea
            if (notesTextarea) {
              const isThai = currentLang === 'th';
              const labelHeader = isThai 
                ? `\n\n[บันทึกการสังเกตการพูดเพิ่มเติม / Supplementary Speech Observation Notes]\nคำถอดเสียง: "${result.transcript}"`
                : `\n\n[Supplementary Speech Observation Notes]\nTranscript: "${result.transcript}"`;
              
              const bullet1 = isThai
                ? `- ความยาวประโยคเฉลี่ย: ${voiceObservations.avgWordsPerUtterance} คำ`
                : `- Average words per utterance: ${voiceObservations.avgWordsPerUtterance} words`;
              const bullet2 = isThai
                ? `- คำศัพท์ที่ไม่ซ้ำกัน: ${voiceObservations.uniqueWordCount} คำ`
                : `- Unique vocabulary: ${voiceObservations.uniqueWordCount} words`;
              const bullet3 = isThai
                ? `- ข้อสังเกตการใช้สรรพนาม: ${voiceObservations.pronounNote ? 'พบการใช้สรรพนามแทนตัวเองในบุคคลอื่น' : 'ไม่พบสิ่งผิดปกติ'}`
                : `- Pronoun observation: ${voiceObservations.pronounNote ? 'potential pronoun confusion noted' : 'none noted'}`;
              const bullet4 = isThai
                ? `- ข้อสังเกตการพูดซ้ำ (Echolalia): ${voiceObservations.echolaliaSignal ? 'พบข้อสังเกตการพูดซ้ำประโยคเดิม' : 'ไม่พบสิ่งผิดปกติ'}`
                : `- Repetitive speech observation: ${voiceObservations.echolaliaSignal ? 'potential phrase repetition noted' : 'none noted'}`;
              
              const disclaimer = isThai
                ? `* ข้อมูลนี้เป็นบันทึกการสังเกตเพิ่มเติม ไม่ใช่ผลการประเมินทางคลินิก`
                : `* This information is an additional observation note, not a clinical assessment.`;

              const appendedText = `${labelHeader}\n${bullet1}\n${bullet2}\n${bullet3}\n${bullet4}\n${disclaimer}`;
              notesTextarea.value = notesTextarea.value.trim() + appendedText;
            }

            if (btnClear) btnClear.hidden = false;
          } else {
            // No transcript
            if (btnStart) btnStart.hidden = false;
          }
        } catch (err) {
          console.error(err);
          const localizedErr = getVoiceErrorMessage(err, getCurrentLang());
          alert(localizedErr);
          if (btnStart) btnStart.hidden = false;
        }
      });
    }

    if (btnClear) {
      btnClear.addEventListener('click', () => {
        voiceObservations = null;
        if (preview) {
          preview.textContent = '';
          preview.hidden = true;
        }
        if (summary) {
          summary.innerHTML = '';
          summary.hidden = true;
        }
        if (btnClear) btnClear.hidden = true;
        if (btnStart) btnStart.hidden = false;
        if (btnStop) btnStop.hidden = true;
        if (indicator) indicator.hidden = true;

        // Strip voice observation lines from textarea if they exist
        if (notesTextarea) {
          const content = notesTextarea.value;
          const searchPattern = /\[บันทึกการสังเกตการพูดเพิ่มเติม|\[Supplementary Speech Observation Notes\]/;
          const matchIndex = content.search(searchPattern);
          if (matchIndex !== -1) {
            notesTextarea.value = content.substring(0, matchIndex).trim();
          }
        }
      });
    }
  }
}

export function resetScreeningForm() {
  currentStep = 1;
  voiceObservations = null;
  
  // Clear voice preview in DOM
  const preview = document.getElementById('voice-transcript-preview');
  if (preview) {
    preview.textContent = '';
    preview.hidden = true;
  }
  const summary = document.getElementById('voice-analysis-summary');
  if (summary) {
    summary.innerHTML = '';
    summary.hidden = true;
  }
  const clearBtn = document.getElementById('btn-voice-clear');
  if (clearBtn) clearBtn.hidden = true;
  const startBtn = document.getElementById('btn-voice-start');
  if (startBtn) startBtn.hidden = false;
  const stopBtn = document.getElementById('btn-voice-stop');
  if (stopBtn) stopBtn.hidden = true;
  const indicator = document.getElementById('voice-recording-indicator');
  if (indicator) indicator.hidden = true;
  
  const form = document.getElementById('screening-form');
  if (form) {
    form.reset();
    form.querySelectorAll('.likert-option.selected').forEach(el => {
      el.classList.remove('selected');
    });
    form.querySelectorAll('.question-item.has-error').forEach(el => {
      el.classList.remove('has-error');
    });
    form.querySelectorAll('.form-select.error').forEach(el => {
      el.classList.remove('error');
    });
    form.querySelectorAll('.form-error').forEach(el => {
      el.style.display = 'none';
    });
  }
  
  showStep(1);
}
