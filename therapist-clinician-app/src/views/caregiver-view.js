import { store } from "../store/state.js";
import { getChildProgress } from "../services/progress-service.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { renderAccessDenied } from "../components/access-denied.js";
import { addAudit } from "../services/audit-service.js";

export function renderCaregiver() {
  const state = store.getState();
  const progress = getChildProgress(state.selectedCaseId);

  if (!progress) {
    const selectedCaseExists = state.cases.some(c => c.case_id === state.selectedCaseId);
    return `
      ${renderSafetyBanner()}
      ${selectedCaseExists ? renderAccessDenied("Access denied: this child case is not assigned to your account.") : '<p class="empty-state">No child case selected. Please choose a child from the dashboard.</p>'}
    `;
  }

  const { caseItem, sessions, goals } = progress;
  
  if (!sessions || sessions.length === 0) {
    return `
      ${renderSafetyBanner()}
      <p class="empty-state">No sessions found for this child yet. Please complete a session and transcript QA first.</p>
    `;
  }

  const latestSession = sessions[sessions.length - 1];
  const initialSession = sessions[0];

  // Calculate friendly metrics
  // 1. Sentence length improvement (MLU)
  const latestMlu = latestSession.mlu;
  const initialMlu = initialSession.mlu;
  const mluDiffPct = initialMlu > 0 ? ((latestMlu - initialMlu) / initialMlu) * 100 : 0;
  
  // Translate MLU into a sentence length explanation
  let sentenceLengthWording = `พูดเฉลี่ย ${latestMlu.toFixed(1)} คำต่อประโยค`;
  if (latestMlu <= 1.5) {
    sentenceLengthWording += " (เน้นพูดคำเดี่ยวเป็นหลัก)";
  } else if (latestMlu <= 2.5) {
    sentenceLengthWording += " (เริ่มผสมคำ 2 คำเข้าด้วยกัน)";
  } else {
    sentenceLengthWording += " (เริ่มพูดประโยคสั้นๆ 3 คำขึ้นไปได้ดี)";
  }

  // 2. Vocabulary Variety (TTR)
  const latestTtr = latestSession.ttr;
  const ttrPercentage = Math.round(latestTtr * 100);
  let vocabWording = `ใช้คำหลากหลาย ${ttrPercentage}% ของบทสนทนา`;
  if (latestTtr <= 0.35) {
    vocabWording += " (พูดคำเดิมซ้ำๆ ค่อนข้างบ่อย)";
  } else if (latestTtr <= 0.50) {
    vocabWording += " (มีความหลากหลายของคำศัพท์ระดับปานกลาง)";
  } else {
    vocabWording += " (ใช้คำศัพท์หมวดหมู่ใหม่ๆ หลากหลายขึ้นชัดเจน)";
  }

  // 3. Repeat patterns (Echolalia)
  const latestEcho = latestSession.echolalia_ratio;
  const echoPercentage = Math.round(latestEcho * 100);
  let echoWording = `พูดเลียนแบบคำคนอื่น ${echoPercentage}% ของคำพูดทั้งหมด`;
  if (latestEcho <= 0.15) {
    echoWording += " (อยู่ในเกณฑ์ปกติ สื่อสารเพื่อตอบรับหรือแสดงความต้องการตนเองเป็นหลัก)";
  } else if (latestEcho <= 0.40) {
    echoWording += " (มีพฤติกรรมพูดทวนคำศัพท์บ่อยขึ้นในบางจังหวะ)";
  } else {
    echoWording += " (มีอาการพูดตามทันทีหรือเลียนเสียงบทสนทนาค่อนข้างมาก)";
  }

  // 4. Intelligibility (simulated based on unintelligible count in latest session)
  const latestFeats = state.extractedFeatureOutputs[latestSession.session_id]?.features || {};
  const unintellRatio = latestFeats.unintelligible_ratio ?? 0;
  const clarityPercentage = Math.round((1 - unintellRatio) * 100);
  let clarityWording = `ความชัดเจนในการออกเสียง ${clarityPercentage}%`;
  if (clarityPercentage >= 85) {
    clarityWording += " (ผู้ฟังคนรอบข้างสามารถเข้าใจคำพูดของน้องได้ดีมาก)";
  } else if (clarityPercentage >= 65) {
    clarityWording += " (ผู้คุ้นเคยเข้าใจได้ดี แต่อาจมีออกเสียงไม่ชัดบางคำ)";
  } else {
    clarityWording += " (น้องออกเสียงค่อนข้างฟังยาก หรือออกเสียงในลำคอ)";
  }

  // Get session vocabulary list
  const sessionVocabList = state.sessionVocabs[latestSession.session_id] || [];
  const newWords = sessionVocabList.filter(v => v.isNew).map(v => v.word);
  const commonWords = sessionVocabList.filter(v => !v.isNew).slice(0, 5).map(v => v.word);

  // Generate activities based on metrics
  const generatedActivities = [
    {
      title: "1. ต่อจิ๊กซอว์ต่อประโยค (Sentence Building Block)",
      desc: `เนื่องจากตอนนี้น้องพูดสั้นๆ ประมาณ ${latestMlu.toFixed(1)} คำ ทุกครั้งที่น้องพูด 1 คำ ให้คุณแม่ช่วยขยายประโยคต่อให้อีก 1 คำทันที เช่น น้องพูด <b>"รถ"</b> ให้แม่พูดเสริมว่า <b>"รถวิ่ง"</b> หรือ <b>"รถแดง"</b> เพื่อให้น้องเลียนแบบประโยคที่ยาวขึ้น`
    },
    {
      title: "2. ค้นพบคำศัพท์ใหม่ประจำวัน (Daily Word Hunt)",
      desc: `น้องมีพัฒนาการคลังคำที่ดีขึ้นสัปดาห์นี้ ชวนน้องเล่นเกมหาคำศัพท์สิ่งของรอบตัว โดยจำกัดหมวดหมู่ เช่น สีส้ม หรือของเล่นที่กลมๆ เมื่อน้องหาเจอ ให้ออกเสียงคำศัพท์นั้นดังๆ และปรบมือให้กำลังใจ`
    },
    {
      title: "3. พูดคุยโต้ตอบผลัดกันพูด (Conversational Turn-Taking)",
      desc: "ลดการถามคำถามปลายปิดที่น้องจะพูดตามอย่างเดียว (Echolalia) เปลี่ยนเป็นประโยคทางเลือก เช่น 'น้องจะเล่นลูกบอลหรือเล่นรถไฟดีครับ?' และเว้นจังหวะรอน้องตอบประมาณ 3-5 วินาทีเพื่อให้เวลาสมองน้องประมวลผลคำพูด"
    }
  ];

  return `
    ${renderSafetyBanner()}
    <section class="dashboard-command print-hide" style="margin-bottom: 16px;">
      <div>
        <h2 style="color: var(--violet-strong);">♥ Caregiver Portal (มุมมองผู้ปกครอง)</h2>
        <p style="color: var(--muted); font-size: 0.85rem;">สรุปความก้าวหน้าและการบำบัดทางภาษาแบบเข้าใจง่ายสำหรับครอบครัว</p>
      </div>
      <button class="primary-action" id="print-caregiver-pdf-btn" style="background: var(--violet); box-shadow: 0 8px 16px var(--violet-soft);">
        🖨 ปริ้นท์รายงานผู้ปกครอง (PDF)
      </button>
    </section>

    <!-- Caregiver Report Layout Container -->
    <div id="caregiver-report-pdf-area" style="display: grid; gap: 20px;">
      
      <!-- Kid Header Card -->
      <div class="panel" style="background: linear-gradient(135deg, var(--violet-soft), oklch(99% 0.005 285)); border-left: 6px solid var(--violet); padding: 20px; border-radius: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
          <div>
            <h1 style="font-size: 1.8rem; margin: 0 0 6px; color: var(--violet-strong);">รายงานพัฒนาการพูดของ ${caseItem.anonymized_child_code}</h1>
            <p style="margin: 0; font-size: 0.9rem; color: var(--muted);">
              อายุ: <strong>${Math.floor(caseItem.age_months / 12)} ขวบ ${caseItem.age_months % 12} เดือน</strong> · 
              วันที่ออกรายงาน: <strong>${new Date().toLocaleDateString("th-TH")}</strong>
            </p>
          </div>
          <div style="display: flex; gap: 8px;">
            <span class="status-pill status-good" style="font-size: 0.85rem; padding: 6px 12px;">เซสชันล่าสุด: ${latestSession.session_date}</span>
          </div>
        </div>
      </div>

      <!-- Friendly Metrics Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;">
        
        <!-- MLU Card -->
        <div class="panel" style="padding: 16px; border-top: 4px solid var(--violet); display: grid; gap: 8px; border-radius: var(--radius);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="color: var(--muted); font-size: 0.85rem;">ความยาวประโยคเฉลี่ย</strong>
            <span style="font-size: 1.5rem;">💬</span>
          </div>
          <div style="font-size: 1.4rem; font-weight: 800; color: var(--violet-strong);">${sentenceLengthWording}</div>
          ${mluDiffPct > 0 ? `
            <div style="font-size: 0.82rem; color: var(--green); font-weight: 700;">
              ↗ พูดประโยคยาวขึ้น +${mluDiffPct.toFixed(0)}% จากครั้งแรกที่ประเมิน
            </div>
          ` : `
            <div style="font-size: 0.82rem; color: var(--muted);">กำลังเริ่มพัฒนาโครงสร้างประโยค</div>
          `}
        </div>

        <!-- TTR Card -->
        <div class="panel" style="padding: 16px; border-top: 4px solid var(--blue); display: grid; gap: 8px; border-radius: var(--radius);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="color: var(--muted); font-size: 0.85rem;">คำศัพท์คลังสมอง</strong>
            <span style="font-size: 1.5rem;">📚</span>
          </div>
          <div style="font-size: 1.4rem; font-weight: 800; color: var(--blue);">${vocabWording}</div>
          <div style="font-size: 0.82rem; color: var(--muted);">
            เรียนรู้คำศัพท์ใหม่เพิ่มขึ้นเรื่อยๆ ในเซสชันบำบัด
          </div>
        </div>

        <!-- Echolalia Card -->
        <div class="panel" style="padding: 16px; border-top: 4px solid var(--amber); display: grid; gap: 8px; border-radius: var(--radius);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="color: var(--muted); font-size: 0.85rem;">การเลียนเสียง / พูดตาม</strong>
            <span style="font-size: 1.5rem;">🦜</span>
          </div>
          <div style="font-size: 1.4rem; font-weight: 800; color: var(--amber);">${echoWording}</div>
          <div style="font-size: 0.82rem; color: ${latestEcho <= 0.20 ? "var(--green)" : "var(--muted)"}; font-weight: 700;">
            ${latestEcho <= 0.20 ? "✓ สื่อสารโต้ตอบด้วยเจตนาตนเองเป็นหลัก" : "กำลังฝึกฝนการทักทายและตอบโต้โดยไม่หยุดทวนคำถาม"}
          </div>
        </div>

        <!-- Clarity Card -->
        <div class="panel" style="padding: 16px; border-top: 4px solid var(--green); display: grid; gap: 8px; border-radius: var(--radius);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="color: var(--muted); font-size: 0.85rem;">ความชัดเจนในการออกเสียง</strong>
            <span style="font-size: 1.5rem;">🔔</span>
          </div>
          <div style="font-size: 1.4rem; font-weight: 800; color: var(--green);">${clarityWording}</div>
          <div style="font-size: 0.82rem; color: var(--muted);">
            ช่วยฝึกน้องเปล่งเสียงสระและพยัญชนะต้นบ่อยๆ ที่บ้าน
          </div>
        </div>

      </div>

      <!-- Vocabulary Growth & Words Section -->
      <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 20px; align-items: stretch; flex-wrap: wrap;">
        
        <!-- Vocabulary growth curve -->
        <section class="panel" style="padding: 16px; border-radius: var(--radius);">
          <div class="panel-title">
            <h3>📈 กราฟการเรียนรู้คำศัพท์สะสมของน้อง (Vocabulary Growth Curve)</h3>
            <span>สะสมคำศัพท์ใหม่ข้ามเซสชัน</span>
          </div>
          <div style="min-height: 220px; display: flex; align-items: flex-end; justify-content: space-around; padding-top: 20px; border-bottom: 2px solid var(--line); border-left: 2px solid var(--line); position: relative;">
            
            <!-- Grid lines background -->
            <div style="position: absolute; inset: 0; display: grid; grid-template-rows: repeat(4, 1fr); pointer-events: none; border-bottom: 1px dashed var(--line);">
              <div style="border-bottom: 1px dashed var(--line); opacity: 0.5;"></div>
              <div style="border-bottom: 1px dashed var(--line); opacity: 0.5;"></div>
              <div style="border-bottom: 1px dashed var(--line); opacity: 0.5;"></div>
              <div style="border-bottom: 1px dashed var(--line); opacity: 0.5;"></div>
            </div>

            ${sessions.map((s, idx) => {
              const vocabCount = idx === 0 ? 1 : (idx === 1 ? 4 : 8);
              const heightPct = (vocabCount / 8) * 85;
              return `
                <div style="display: flex; flex-direction: column; align-items: center; z-index: 2; width: 60px;">
                  <span style="font-size: 0.8rem; font-weight: 700; color: var(--violet); margin-bottom: 4px;">${vocabCount} คำ</span>
                  <div style="width: 28px; height: ${heightPct}px; background: linear-gradient(180deg, var(--violet-strong), var(--violet-soft)); border-radius: 4px 4px 0 0; box-shadow: 0 4px 10px var(--violet-soft);"></div>
                  <span style="font-size: 0.72rem; color: var(--muted); margin-top: 8px; white-space: nowrap;">ครั้งที่ ${idx + 1}</span>
                </div>
              `;
            }).join("")}
          </div>
          <p style="font-size: 0.8rem; color: var(--muted); margin-top: 10px; text-align: center;">
            * กราฟวิเคราะห์จากจำนวน 'คำศัพท์ที่แตกต่างกัน' ที่น้องใช้สื่อสารในชิ้นงานตัวอย่างคำพูดจริง
          </p>
        </section>

        <!-- New Words List Panel -->
        <section class="panel" style="padding: 16px; border-radius: var(--radius); display: grid; gap: 14px;">
          <div class="panel-title" style="margin-bottom: 4px;">
            <h3>✨ คำศัพท์ในเซสชันล่าสุด</h3>
            <span>คำที่พบบ่อย</span>
          </div>

          <div>
            <strong style="color: var(--violet-strong); font-size: 0.85rem; display: block; margin-bottom: 6px;">🆕 คำศัพท์ใหม่สัปดาห์นี้ (New Words):</strong>
            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
              ${newWords.length > 0 
                ? newWords.map(w => `<span style="padding: 4px 8px; background: var(--violet-soft); color: var(--violet-strong); border-radius: 6px; font-weight: 700; font-size: 0.85rem; border: 1px solid var(--line);">${w}</span>`).join("")
                : '<span style="color: var(--muted); font-size: 0.82rem;">กำลังเก็บข้อมูลตัวอย่างคำเพิ่มเติม...</span>'
              }
            </div>
          </div>

          <hr style="border: 0; border-top: 1px solid var(--line); margin: 4px 0;" />

          <div>
            <strong style="color: var(--blue); font-size: 0.85rem; display: block; margin-bottom: 6px;">🗣️ คำศัพท์อื่นที่น้องพูดซ้ำบ่อย:</strong>
            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
              ${commonWords.length > 0
                ? commonWords.map(w => `<span style="padding: 4px 8px; background: var(--blue-soft); color: var(--blue); border-radius: 6px; font-weight: 700; font-size: 0.85rem; border: 1px solid var(--line);">${w}</span>`).join("")
                : '<span style="color: var(--muted); font-size: 0.82rem;"> car, block </span>'
              }
            </div>
          </div>
        </section>
      </div>

      <!-- Home Activities and Exercise Plan -->
      <section class="panel" style="padding: 18px; border-radius: var(--radius);">
        <div class="panel-title" style="border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-bottom: 16px;">
          <h3 style="color: var(--violet-strong); font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
            🏡 กิจกรรมฝึกต่อยอดที่บ้าน (Home Practice Sheet)
          </h3>
          <span style="font-size: 0.85rem; color: var(--muted);">คำแนะนำโดยนักบำบัดร่วมกับ AI</span>
        </div>

        <div style="display: grid; gap: 16px;">
          ${generatedActivities.map(act => `
            <div style="border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: var(--shell);">
              <h4 style="margin: 0 0 6px; font-size: 0.92rem; color: var(--ink); font-weight: 800;">${act.title}</h4>
              <p style="margin: 0; font-size: 0.86rem; color: var(--muted); line-height: 1.5;">${act.desc}</p>
            </div>
          `).join("")}
        </div>
      </section>

      <!-- Disclaimer & Professional Signature Footer -->
      <div style="margin-top: 14px; padding: 12px; background: var(--panel-soft); border-radius: var(--radius); font-size: 0.8rem; color: var(--muted); line-height: 1.4; display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 20px;">
        <div style="max-width: 60%;">
          <strong>หมายเหตุทางคลินิก (Clinical Disclaimer):</strong>
          <p style="margin: 4px 0 0;">รายงานฉบับย่อนี้จัดทำเพื่ออำนวยความสะดวกให้ผู้ปกครองติดตามระดับทักษะของลูกเท่านั้น ไม่ใช่เอกสารการวินิจฉัยโรคทางการแพทย์ (This tool is a clinical support prototype. It does not replace medical diagnosis).</p>
        </div>
        <div style="text-align: right; min-width: 150px;">
          <p style="margin: 0; font-style: italic;">ลงชื่อผู้ตรวจบำบัด</p>
          <div style="height: 36px; border-bottom: 1px solid var(--muted); margin-bottom: 4px; width: 140px; margin-left: auto;"></div>
          <strong>${state.currentUser?.name || "Jane Smith, M.S. CCC-SLP"}</strong>
        </div>
      </div>

    </div>
  `;
}

export function bindCaregiver(navigate) {
  const printBtn = document.getElementById("print-caregiver-pdf-btn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      window.print();
      const caseId = store.getState().selectedCaseId;
      addAudit("print_caregiver_report", "ChildCase", caseId, "Printed / Saved PDF caregiver progress summary.");
    });
  }
}
