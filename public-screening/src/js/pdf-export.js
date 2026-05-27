/**
 * pdf-export.js — Client-Side PDF / Print Summary Export
 *
 * Uses window.print() with a print-optimised overlay for maximum
 * browser compatibility (no external libraries required).
 * Also provides a plain-text download fallback.
 */

import { getCurrentLang, t } from './i18n.js';

// ─── Helpers ────────────────────────────────────────────────────────────────

/** Map concern level to a human-readable, safe label */
function concernLabel(level) {
  const lang = getCurrentLang();
  const map = {
    low:      { en: 'Low Concern',      th: 'ระดับความกังวลต่ำ' },
    moderate: { en: 'Moderate Concern',  th: 'ระดับความกังวลปานกลาง' },
    high:     { en: 'High Concern',      th: 'ระดับความกังวลสูง' },
  };
  return (map[level] || map.low)[lang];
}

/** Format today's date */
function formatDate() {
  return new Intl.DateTimeFormat(getCurrentLang() === 'th' ? 'th-TH' : 'en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  }).format(new Date());
}

/** Map age range key to readable text */
function ageRangeLabel(key) {
  const lang = getCurrentLang();
  const labels = {
    under12: { en: 'Under 12 months',  th: 'ต่ำกว่า 12 เดือน' },
    m12_18:  { en: '12–18 months',     th: '12–18 เดือน' },
    m18_24:  { en: '18–24 months',     th: '18–24 เดือน' },
    m24_36:  { en: '24–36 months',     th: '24–36 เดือน' },
    m36_48:  { en: '36–48 months',     th: '36–48 เดือน' },
    m48_60:  { en: '48–60 months',     th: '48–60 เดือน' },
    over60:  { en: '60+ months',       th: '60 เดือนขึ้นไป' },
  };
  return (labels[key] || { en: key, th: key })[lang];
}

/** Category display name */
function categoryName(cat) {
  const lang = getCurrentLang();
  const names = {
    speech:     { en: 'Speech & Language',       th: 'ภาษาและการพูด' },
    social:     { en: 'Social Communication',    th: 'การสื่อสารทางสังคม' },
    repetitive: { en: 'Repetitive Behaviors',    th: 'พฤติกรรมซ้ำๆ' },
  };
  return (names[cat] || { en: cat, th: cat })[lang];
}


// ─── Print-Optimised HTML Builder ───────────────────────────────────────────

/**
 * Build the hidden print-only summary HTML.
 * @param {Object} data — result object from scoring.js
 * @returns {string}
 */
function buildPrintHTML(data) {
  const lang = getCurrentLang();
  const isEN = lang === 'en';

  // Category rows
  const catRows = ['speech', 'social', 'repetitive'].map((cat) => `
    <tr>
      <td>${categoryName(cat)}</td>
      <td>${data.categoryScores[cat]} / 100</td>
    </tr>
  `).join('');

  // Feature rows
  const featureRows = (data.featureBreakdown || []).map((f) => `
    <tr>
      <td>${isEN ? f.name : f.nameTh}</td>
      <td>${f.score} / ${f.maxScore}</td>
      <td>${f.level}</td>
    </tr>
  `).join('');

  // Recommendations
  const recItems = (data.recommendations || []).map((r) => `<li>${r}</li>`).join('');

  // Voice Observations (optional section)
  let voiceObsHTML = '';
  if (data.voiceObservations) {
    const vo = data.voiceObservations;
    const pronounText = vo.pronounNote
      ? (isEN ? 'Potential pronoun substitute/reversal noted' : 'พบข้อสังเกตความสับสนในการใช้สรรพนาม')
      : (isEN ? 'None noted' : 'ไม่พบสิ่งผิดปกติ');
    const echoText = vo.echolaliaSignal
      ? (isEN ? 'Potential phrase repetition noted' : 'พบข้อสังเกตการพูดซ้ำ')
      : (isEN ? 'None noted' : 'ไม่พบสิ่งผิดปกติ');

    voiceObsHTML = `
      <h2>${isEN ? '🎙️ Voice Observation Notes' : '🎙️ หมายเหตุจากการสังเกตเสียง'}</h2>
      <blockquote style="font-style: italic; border-left: 3px solid #666; padding-left: 10px; margin: 10px 0;">
        "${vo.rawTranscript}"
      </blockquote>
      <ul>
        <li>${isEN ? 'Average words per utterance' : 'ความยาวประโยคเฉลี่ย'}: <strong>${vo.avgWordsPerUtterance} ${isEN ? 'words' : 'คำ'}</strong></li>
        <li>${isEN ? 'Vocabulary size (unique words)' : 'จำนวนคำศัพท์ที่ใช้'}: <strong>${vo.uniqueWordCount} ${isEN ? 'words' : 'คำ'}</strong></li>
        <li>${isEN ? 'Pronoun indicator' : 'ตัวบ่งชี้ด้านการใช้สรรพนาม'}: <strong>${pronounText}</strong></li>
        <li>${isEN ? 'Repetitive speech (Echolalia)' : 'ตัวบ่งชี้การพูดซ้ำ'}: <strong>${echoText}</strong></li>
      </ul>
      <p style="font-size: 0.8em; color: #666; font-style: italic; margin-top: 5px; margin-bottom: 20px;">
        ${isEN ? 'This information is an additional observation note, not a clinical assessment.' : 'ข้อมูลนี้เป็นบันทึกการสังเกตเพิ่มเติม ไม่ใช่ผลการประเมินทางคลินิก'}
      </p>
    `;
  }

  return `
    <div id="print-summary" class="print-summary">
      <h1>${isEN ? 'Developmental Screening Support Summary' : 'สรุปผลการคัดกรองพัฒนาการ'}</h1>

      <p class="print-date">${isEN ? 'Date Generated' : 'วันที่สร้าง'}: ${formatDate()}</p>

      <div class="print-disclaimer">
        <strong>${isEN ? '⚠️ Important Disclaimer' : '⚠️ ข้อสงวนสิทธิ์ที่สำคัญ'}</strong><br>
        This system is a clinical decision-support prototype. It does not diagnose ASD and does not replace qualified clinical judgment.<br>
        ${isEN
          ? 'This is NOT a medical diagnosis. This summary is generated by a screening support tool and is intended to help identify areas where professional consultation may be beneficial.'
          : 'นี่ไม่ใช่การวินิจฉัยทางการแพทย์ สรุปนี้สร้างขึ้นโดยเครื่องมือสนับสนุนการคัดกรอง มีวัตถุประสงค์เพื่อช่วยระบุด้านที่อาจได้ประโยชน์จากการปรึกษาผู้เชี่ยวชาญ'}
      </div>

      <h2>${isEN ? 'Child\'s Age Range' : 'ช่วงอายุของเด็ก'}</h2>
      <p>${ageRangeLabel(data.ageRange)}</p>

      <h2>${isEN ? 'Overall Concern Level' : 'ระดับความกังวลโดยรวม'}</h2>
      <p class="print-score">
        <strong>${concernLabel(data.concernLevel)}</strong>
        &nbsp;—&nbsp;${isEN ? 'Score' : 'คะแนน'}: ${data.overallScore} / 100
      </p>

      <h2>${isEN ? 'Category Scores' : 'คะแนนตามหมวดหมู่'}</h2>
      <table class="print-table">
        <thead><tr><th>${isEN ? 'Category' : 'หมวดหมู่'}</th><th>${isEN ? 'Score' : 'คะแนน'}</th></tr></thead>
        <tbody>${catRows}</tbody>
      </table>

      <h2>${isEN ? 'Individual Question Responses' : 'คำตอบรายข้อ'}</h2>
      <table class="print-table">
        <thead><tr>
          <th>${isEN ? 'Feature' : 'รายการ'}</th>
          <th>${isEN ? 'Score' : 'คะแนน'}</th>
          <th>${isEN ? 'Level' : 'ระดับ'}</th>
        </tr></thead>
        <tbody>${featureRows}</tbody>
      </table>

      ${voiceObsHTML}

      <h2>${isEN ? 'Recommendations' : 'คำแนะนำ'}</h2>
      <ul>${recItems}</ul>

      <div class="print-consult">
        <p>${isEN
          ? 'Please share this summary with a qualified healthcare professional for proper assessment.'
          : 'กรุณานำสรุปนี้ไปปรึกษาผู้เชี่ยวชาญด้านสุขภาพเพื่อการประเมินที่เหมาะสม'}</p>
      </div>

      <footer class="print-footer">
        <p>${isEN
          ? 'Generated by asd-project Screening Support Tool'
          : 'สร้างโดยเครื่องมือสนับสนุนการคัดกรอง asd-project'}</p>
      </footer>
    </div>
  `;
}


// ─── Print Styles (injected once) ───────────────────────────────────────────

const PRINT_STYLE_ID = 'print-summary-styles';

function injectPrintStyles() {
  if (document.getElementById(PRINT_STYLE_ID)) return;

  const style = document.createElement('style');
  style.id = PRINT_STYLE_ID;
  style.textContent = `
    /* ── Screen: hide the print summary ── */
    #print-summary { display: none; }

    /* ── Print: show ONLY the summary ── */
    @media print {
      body > *:not(#print-summary) { display: none !important; }
      #print-summary {
        display: block !important;
        font-family: 'Sarabun', 'Segoe UI', sans-serif;
        color: #1a1a2e;
        max-width: 700px;
        margin: 0 auto;
        padding: 24px;
        font-size: 12pt;
        line-height: 1.6;
      }
      #print-summary h1 {
        font-size: 18pt;
        margin-bottom: 4px;
        color: #2d3250;
      }
      #print-summary h2 {
        font-size: 13pt;
        margin-top: 20px;
        border-bottom: 1px solid #ccc;
        padding-bottom: 4px;
        color: #2d3250;
      }
      .print-date {
        font-size: 10pt;
        color: #666;
        margin-bottom: 16px;
      }
      .print-disclaimer {
        border: 2px solid #e74c3c;
        padding: 12px;
        margin: 16px 0;
        border-radius: 6px;
        background: #fdf2f2;
        font-size: 10pt;
      }
      .print-score {
        font-size: 14pt;
      }
      .print-table {
        width: 100%;
        border-collapse: collapse;
        margin: 8px 0 16px;
        font-size: 10pt;
      }
      .print-table th, .print-table td {
        border: 1px solid #ddd;
        padding: 6px 10px;
        text-align: left;
      }
      .print-table thead { background: #f4f4f9; }
      .print-consult {
        margin: 20px 0;
        padding: 14px;
        background: #f0fdf4;
        border-left: 4px solid #22c55e;
        border-radius: 4px;
      }
      .print-footer {
        margin-top: 30px;
        font-size: 9pt;
        color: #888;
        text-align: center;
        border-top: 1px solid #ddd;
        padding-top: 8px;
      }
    }
  `;
  document.head.appendChild(style);
}


// ─── Text File Fallback ─────────────────────────────────────────────────────

/**
 * Generate a plain-text summary and trigger download.
 * @param {Object} data
 */
function downloadTextSummary(data) {
  const lang = getCurrentLang();
  const isEN = lang === 'en';
  const nl = '\n';
  const hr = '─'.repeat(50);

  let txt = '';
  txt += (isEN ? 'DEVELOPMENTAL SCREENING SUPPORT SUMMARY' : 'สรุปผลการคัดกรองพัฒนาการ') + nl;
  txt += hr + nl;
  txt += `${isEN ? 'Date' : 'วันที่'}: ${formatDate()}${nl}`;
  txt += nl;
  txt += (isEN
    ? '⚠️ DISCLAIMER: This system is a clinical decision-support prototype. It does not diagnose ASD and does not replace qualified clinical judgment.'
    : '⚠️ ข้อสงวนสิทธิ์: นี่ไม่ใช่การวินิจฉัยทางการแพทย์') + nl;
  txt += hr + nl;
  txt += `${isEN ? 'Age Range' : 'ช่วงอายุ'}: ${ageRangeLabel(data.ageRange)}${nl}`;
  txt += `${isEN ? 'Overall Concern Level' : 'ระดับความกังวลโดยรวม'}: ${concernLabel(data.concernLevel)} (${data.overallScore}/100)${nl}`;
  txt += nl;
  txt += (isEN ? 'CATEGORY SCORES' : 'คะแนนตามหมวดหมู่') + nl;
  txt += hr + nl;
  for (const cat of ['speech', 'social', 'repetitive']) {
    txt += `  ${categoryName(cat)}: ${data.categoryScores[cat]}/100${nl}`;
  }
  txt += nl;
  txt += (isEN ? 'INDIVIDUAL FEATURES' : 'ผลรายข้อ') + nl;
  txt += hr + nl;
  for (const f of data.featureBreakdown || []) {
    txt += `  ${isEN ? f.name : f.nameTh}: ${f.score}/${f.maxScore} (${f.level})${nl}`;
  }
  txt += nl;
  txt += (isEN ? 'RECOMMENDATIONS' : 'คำแนะนำ') + nl;
  txt += hr + nl;
  for (const r of data.recommendations || []) {
    txt += `  • ${r}${nl}`;
  }
  txt += nl;
  txt += (isEN
    ? 'Please share this with a qualified healthcare professional for proper assessment.'
    : 'กรุณานำสรุปนี้ไปปรึกษาผู้เชี่ยวชาญด้านสุขภาพเพื่อการประเมินที่เหมาะสม') + nl;
  txt += hr + nl;
  txt += (isEN
    ? 'Generated by asd-project Screening Support Tool'
    : 'สร้างโดยเครื่องมือสนับสนุนการคัดกรอง asd-project') + nl;

  // Trigger download
  const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `screening-summary-${new Date().toISOString().slice(0, 10)}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}


// ─── Public API ─────────────────────────────────────────────────────────────

/**
 * Generate and export a PDF summary via window.print().
 * Falls back to a downloadable plain-text file if something goes wrong.
 *
 * @param {Object} resultData — the full result object from scoring.js
 */
export function generatePDF(resultData) {
  try {
    injectPrintStyles();

    // Remove any previously-injected summary
    const existing = document.getElementById('print-summary');
    if (existing) existing.remove();

    // Inject the print-optimised summary into the body
    const wrapper = document.createElement('div');
    wrapper.innerHTML = buildPrintHTML(resultData);
    const summaryEl = wrapper.firstElementChild;
    document.body.appendChild(summaryEl);

    // Give browser a tick to render, then print
    requestAnimationFrame(() => {
      window.print();
    });
  } catch (err) {
    console.warn('[pdf-export] Print failed, falling back to text download:', err);
    downloadTextSummary(resultData);
  }
}
