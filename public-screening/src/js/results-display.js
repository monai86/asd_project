/**
 * results-display.js — Results Page Rendering (Redesigned)
 *
 * Reads scoring data from sessionStorage, renders the results page,
 * updates the gauge needle, populates category breakdown, and handles
 * the mockup risk assessment cards and toggling detailed results.
 */

import { applyTranslations, t, getCurrentLang } from './i18n.js';
import { initNav } from './nav.js';
import { generatePDF } from './pdf-export.js';
import { resetScreeningForm } from './screening-form.js';

// ─── Storage Key ────────────────────────────────────────────────────────────
const STORAGE_KEY = 'screening-result';

/**
 * Return specific list of mockup checklist recommendations based on concern level.
 */
function getMockupRecommendations(concernLevel, lang) {
  const isThai = lang === 'th';
  if (concernLevel === 'low') {
    return [
      isThai ? 'ส่งเสริมพัฒนาการอย่างต่อเนื่อง' : 'Promote development continuously',
      isThai ? 'เล่นและทำกิจกรรมร่วมกันเป็นประจำ' : 'Play and engage in activities together regularly',
      isThai ? 'สังเกตพฤติกรรมอย่างต่อเนื่อง' : 'Observe behaviors continuously',
      isThai ? 'หากมีข้อสงสัย แนะนำให้ปรึกษาผู้เชี่ยวชาญ' : 'If in doubt, consult a specialist'
    ];
  } else if (concernLevel === 'moderate') {
    return [
      isThai ? 'ปรึกษาผู้เชี่ยวชาญด้านพัฒนาการเพื่อการประเมินเพิ่มเติม' : 'Consult developmental specialists for further evaluation',
      isThai ? 'สังเกตพัฒนาการและบันทึกข้อสังเกตอย่างสม่ำเสมอ' : 'Observe development and log observations regularly',
      isThai ? 'เล่นเกมกระตุ้นพัฒนาการเพื่อเสริมสร้างการสื่อสาร' : 'Play developmental stimulation games to boost communication',
      isThai ? 'นำสรุปผลคัดกรองนี้ไปปรึกษาแพทย์หรือนักแก้ไขการพูด' : 'Bring this screening summary to consult doctors or speech therapists'
    ];
  } else {
    return [
      isThai ? 'แนะนำอย่างยิ่งให้ปรึกษากุมารแพทย์พัฒนาการเพื่อรับการวินิจฉัย' : 'Strongly recommend consulting a developmental pediatrician for diagnosis',
      isThai ? 'นำรายงานสรุปผลการคัดกรองนี้เป็นข้อมูลสนับสนุนการพูดคุยกับแพทย์' : 'Bring this screening summary report as support info for doctor visits',
      isThai ? 'ติดต่อศูนย์หรือสถาบันพัฒนาการเด็กเพื่อเริ่มโปรแกรมกระตุ้นพัฒนาการ' : 'Contact child development centers/institutes to start stimulation programs',
      isThai ? 'มีส่วนร่วมและสนับสนุนการสื่อสารในบ้านทุกวันอย่างใกล้ชิด' : 'Closely engage and support communication at home daily'
    ];
  }
}

/**
 * Render the results content into the existing DOM elements.
 * @param {Object} data — result object from scoring.js
 */
function renderResults(data) {
  const lang = getCurrentLang();

  // Add body class for low concern celebration
  if (data.concernLevel === 'low') {
    document.body.classList.add('celebrate');
  } else {
    document.body.classList.remove('celebrate');
  }

  // A. Mockup Primary Risk Card
  const primaryRiskCard = document.getElementById('primary-risk-card');
  if (primaryRiskCard) {
    const subtitle = lang === 'en' ? 'From preliminary screening' : 'จากการคัดกรองในเบื้องต้น';
    const explanation = t(`results.${data.concernLevel}Explanation`);
    const starEmoji = data.concernLevel === 'low' ? '⭐' : data.concernLevel === 'moderate' ? '💛' : '❤️';
    primaryRiskCard.innerHTML = `
      <div class="risk-card risk-card-${data.concernLevel}">
        <div class="risk-card-icon">${starEmoji}</div>
        <div class="risk-card-body">
          <span class="risk-card-subtitle">${subtitle}</span>
          <span class="risk-card-title">${t(`results.${data.concernLevel}`)}</span>
          <p class="risk-card-explanation">${explanation}</p>
        </div>
      </div>
    `;
  }

  // B. Mockup Recommendations Checklist
  const recMockupList = document.getElementById('rec-mockup-list');
  if (recMockupList) {
    const items = getMockupRecommendations(data.concernLevel, lang);
    recMockupList.innerHTML = items.map(item => `
      <div class="rec-mockup-item">
        <span class="rec-mockup-check">✓</span>
        <span class="rec-mockup-text">${item}</span>
      </div>
    `).join('');
  }

  // 1. Age range
  const ageEl = document.getElementById('results-age');
  if (ageEl) {
    const ageKey = `screening.ageOptions.${data.ageRange}`;
    ageEl.innerHTML = `${t('results.ageRangeLabel')}: <strong>${t(ageKey)}</strong>`;
  }

  // 2. Gauge label and score
  const gaugeContainer = document.getElementById('gauge-container');
  if (gaugeContainer) {
    // Reset previous classes
    gaugeContainer.className = `concern-gauge-container concern-${data.concernLevel}`;
  }
  const gaugeLabel = document.getElementById('gauge-label');
  if (gaugeLabel) {
    gaugeLabel.textContent = t(`results.${data.concernLevel}`);
  }
  const gaugeScore = document.getElementById('gauge-score');
  if (gaugeScore) {
    gaugeScore.textContent = `${data.overallScore} / 100`;
  }

  // 3. Gauge Needle rotation (-90deg for 0 score, 90deg for 100 score)
  const needle = document.getElementById('gauge-needle');
  if (needle) {
    const angle = -90 + (data.overallScore / 100) * 180;
    requestAnimationFrame(() => {
      needle.style.transition = 'transform 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)';
      needle.style.transform = `rotate(${angle}deg)`;
      needle.style.transformOrigin = '100px 100px';
    });
  }

  // 4. Explanation text
  const explanationEl = document.getElementById('explanation-text');
  if (explanationEl) {
    explanationEl.textContent = t(`results.${data.concernLevel}Explanation`);
  }

  // 5. Category breakdown summary cards
  const categoryCards = document.getElementById('category-cards');
  if (categoryCards) {
    const commScore = data.categoryScores.communication ?? data.categoryScores.speech ?? 0;
    const socialScore = data.categoryScores.social ?? 0;
    const repScore = data.categoryScores.repetitive ?? 0;
    const playScore = data.categoryScores.play ?? Math.round(socialScore * 0.7 + 10);
    const sensoryScore = data.categoryScores.sensory ?? Math.round(repScore * 0.8 + 10);

    const domains = [
      { key: 'communication', score: commScore, icon: '🗣️', color: 'blue', i18nKey: 'speechCategory' },
      { key: 'social', score: socialScore, icon: '👥', color: 'purple', i18nKey: 'socialCategory' },
      { key: 'repetitive', score: repScore, icon: '🔄', color: 'peach', i18nKey: 'repetitiveCategory' },
      { key: 'play', score: playScore, icon: '🎨', color: 'blue', i18nKey: 'playCategory' },
      { key: 'sensory', score: sensoryScore, icon: '⚡', color: 'purple', i18nKey: 'sensoryCategory' }
    ];

    categoryCards.innerHTML = domains.map(dom => {
      const score = dom.score;
      const level = score <= 33 ? 'low' : score <= 66 ? 'moderate' : 'high';
      const label = t(`results.${dom.i18nKey}`);
      const concernText = t(`results.${level}`);
      const explanation = t(`results.${dom.key}${level.charAt(0).toUpperCase() + level.slice(1)}`);

      return `
        <div class="feature-card" style="display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-4); margin-bottom: var(--space-3); align-items: stretch; height: auto;">
          <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
            <div style="display: flex; align-items: center; gap: var(--space-3);">
              <div class="feature-icon feature-icon-${dom.color}">${dom.icon}</div>
              <div>
                <div class="feature-label" data-i18n="results.${dom.i18nKey}">${label}</div>
                <span class="badge badge-${level}" style="font-size: var(--text-xs); font-weight: 600; padding: 2px 8px; border-radius: var(--radius-full); background: var(--concern-${level}-bg); color: var(--concern-${level}); border: 1px solid var(--concern-${level}-border);">
                  ${concernText}
                </span>
              </div>
            </div>
            <div class="feature-value">${score} <span style="font-size: var(--text-xs); color: var(--text-muted);">/ 100</span></div>
          </div>
          <div class="feature-bar" style="margin: var(--space-2) 0 0 0; width: 100%;">
            <div class="feature-bar-fill" style="width: 0%; background: var(--concern-${level});" data-bar-width="${score}"></div>
          </div>
          <p style="font-size: var(--text-xs); color: var(--text-secondary); margin: var(--space-1) 0 0 0; line-height: 1.4;">
            ${explanation}
          </p>
        </div>
      `;
    }).join('');

    setTimeout(() => {
      document.querySelectorAll('#category-cards .feature-bar-fill').forEach(bar => {
        const width = bar.dataset.barWidth;
        bar.style.transition = 'width 0.8s ease-out 0.3s';
        bar.style.width = `${width}%`;
      });
    }, 50);
  }

  // 6. Detailed feature breakdown accordion items
  const featureList = document.getElementById('feature-list');
  if (featureList) {
    const icons = { speech: '🗣️', social: '👥', repetitive: '🔄' };
    const iconColors = { speech: 'blue', social: 'purple', repetitive: 'peach' };

    featureList.innerHTML = (data.featureBreakdown || []).map(f => {
      const name = lang === 'en' ? f.name : f.nameTh;
      const pct = (f.score / f.maxScore) * 100;

      return `
        <div class="feature-card" style="margin-bottom: var(--space-3);">
          <div class="feature-icon feature-icon-${iconColors[f.category]}">${icons[f.category]}</div>
          <div style="flex: 1; min-width: 0; padding-right: var(--space-3);">
            <div class="feature-label">${name}</div>
            <div class="feature-value">${f.score} <span style="font-size: var(--text-xs); color: var(--text-muted);">/ ${f.maxScore}</span></div>
          </div>
          <div class="feature-bar">
            <div class="feature-bar-fill" style="width: ${pct}%; background: var(--concern-${f.level});"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  // 7. Recommendations list (detailed report)
  const recommendationsList = document.getElementById('recommendations-list');
  if (recommendationsList) {
    recommendationsList.innerHTML = (data.recommendations || []).map(r => `
      <li class="recommendation-item" style="margin-bottom: var(--space-2); display: flex; gap: var(--space-2); align-items: start;">
        <span class="recommendation-icon">💡</span>
        <span>${r}</span>
      </li>
    `).join('');
  }

  // 7.5. Voice Observations
  const voiceCard = document.getElementById('voice-obs-card');
  if (voiceCard && data.voiceObservations) {
    voiceCard.style.display = 'block';

    const transcriptEl = document.getElementById('voice-raw-transcript');
    if (transcriptEl) {
      transcriptEl.textContent = `"${data.voiceObservations.rawTranscript}"`;
    }

    const listEl = document.getElementById('voice-observations-list');
    if (listEl) {
      const isThai = lang === 'th';
      const items = [];

      items.push(isThai
        ? `ความยาวประโยคเฉลี่ย: <strong>${data.voiceObservations.avgWordsPerUtterance} คำ/ประโยค</strong>`
        : `Average words per utterance: <strong>${data.voiceObservations.avgWordsPerUtterance} words</strong>`
      );

      items.push(isThai
        ? `จำนวนคำศัพท์ที่ใช้: <strong>${data.voiceObservations.uniqueWordCount} คำ</strong>`
        : `Vocabulary size (unique words): <strong>${data.voiceObservations.uniqueWordCount} words</strong>`
      );

      if (data.voiceObservations.pronounNote) {
        items.push(isThai
          ? `ตัวบ่งชี้ด้านการใช้สรรพนาม: <span class="badge badge-warning">พบการใช้สรรพนามแทนตัวเองในบุคคลอื่น / Potential pronoun substitution noted</span>`
          : `Pronoun indicator: <span class="badge badge-warning">Potential pronoun reversal/substitution noted</span>`
        );
      } else {
        items.push(isThai
          ? `ตัวบ่งชี้ด้านการใช้สรรพนาม: <span class="badge badge-info">ไม่พบข้อควรสังเกต / None noted</span>`
          : `Pronoun indicator: <span class="badge badge-info">None noted</span>`
        );
      }

      if (data.voiceObservations.echolaliaSignal) {
        items.push(isThai
          ? `ตัวบ่งชี้การพูดซ้ำ (Echolalia): <span class="badge badge-warning">พบข้อสังเกตการพูดซ้ำประโยคเดิม / Potential phrase repetition noted</span>`
          : `Repetitive speech (Echolalia): <span class="badge badge-warning">Potential phrase repetition noted</span>`
        );
      } else {
        items.push(isThai
          ? `ตัวบ่งชี้การพูดซ้ำ (Echolalia): <span class="badge badge-info">ไม่พบข้อควรสังเกต / None noted</span>`
          : `Repetitive speech (Echolalia): <span class="badge badge-info">None noted</span>`
        );
      }

      listEl.innerHTML = items.map(item => `
        <li style="margin-bottom: var(--space-2); display: flex; gap: var(--space-2); align-items: start;">
          <span style="color: var(--accent-primary);">•</span>
          <span>${item}</span>
        </li>
      `).join('');
    }
  } else if (voiceCard) {
    voiceCard.style.display = 'none';
  }

  applyTranslations();

  const footerDisclaimer = document.querySelector('.footer-disclaimer');
  if (footerDisclaimer && !footerDisclaimer.textContent.includes('clinical decision-support prototype')) {
    footerDisclaimer.insertAdjacentHTML(
      'afterend',
      '<p class="footer-disclaimer">This system is a clinical decision-support prototype. It does not diagnose ASD and does not replace qualified clinical judgment.</p>'
    );
  }
}

/**
 * Initialise the results page.
 * Call once inside DOMContentLoaded.
 */
export function initResults() {
  const container = document.getElementById('results-content');
  const noDataEl = document.getElementById('no-data-message');

  if (!container || !noDataEl) {
    console.warn('[results-display] Core layout elements not found.');
    return;
  }

  // Retrieve data from sessionStorage
  let data;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) throw new Error('No screening data found');
    data = JSON.parse(raw);
  } catch (err) {
    container.style.display = 'none';
    noDataEl.style.display = 'block';
    applyTranslations();
    return;
  }

  noDataEl.style.display = 'none';
  container.style.display = 'block';

  // Render initial results
  renderResults(data);

  // ── Event listeners ──

  // Toggle detailed report visibility
  const toggleDetailsBtn = document.getElementById('btn-toggle-details');
  const detailedReport = document.getElementById('detailed-report');
  if (toggleDetailsBtn && detailedReport) {
    toggleDetailsBtn.addEventListener('click', () => {
      const isHidden = detailedReport.style.display === 'none' || detailedReport.style.display === '';
      if (isHidden) {
        detailedReport.style.display = 'block';
        toggleDetailsBtn.textContent = getCurrentLang() === 'en' ? 'Hide Detailed Report' : 'ซ่อนรายละเอียดผลการคัดกรอง';
        detailedReport.scrollIntoView({ behavior: 'smooth' });
      } else {
        detailedReport.style.display = 'none';
        toggleDetailsBtn.textContent = getCurrentLang() === 'en' ? 'View Detailed Report' : 'ดูรายละเอียดผลการคัดกรอง';
      }
    });
  }

  // Download / Print PDF report
  const downloadBtn = document.getElementById('btn-download');
  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      generatePDF(data);
    });
  }

  // Restart / Start over
  const restartBtn = document.getElementById('btn-restart');
  if (restartBtn) {
    restartBtn.addEventListener('click', () => {
      sessionStorage.removeItem('screening-answers');
      sessionStorage.removeItem(STORAGE_KEY);

      // Reset screening form inputs and state
      resetScreeningForm();
    });
  }

  // Re-render when language changes
  window.addEventListener('langchange', () => {
    renderResults(data);
  });
}
