import { store } from "../store/state.js";
import { getChildProgress } from "../services/progress-service.js";
import { buildProgressReportMarkdown } from "../services/report-service.js";
import { renderRadarChart, radarEntries } from "../components/radar-chart.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { addAudit } from "../services/audit-service.js";
import { renderAccessDenied } from "../components/access-denied.js";

export function renderProgressReports() {
  const state = store.getState();
  const progress = getChildProgress(state.selectedCaseId);

  if (!progress) {
    const selectedCaseExists = state.cases.some(c => c.case_id === state.selectedCaseId);
    return `
      ${renderSafetyBanner()}
      ${selectedCaseExists ? renderAccessDenied() : '<p class="empty-state">No progress data found for the selected child. Please add sessions and complete transcript reviews first.</p>'}
    `;
  }

  const { caseItem, sessions, goals } = progress;

  let currentThaiSummary = (state.therapistThaiSummaries && state.therapistThaiSummaries[state.selectedCaseId]) || "";
  if (!currentThaiSummary) {
    currentThaiSummary = `**สรุปแนวโน้มพัฒนาการจากข้อมูลเชิงพรรณนาเบื้องต้น:**\n` + generateAutoSummaryText(sessions, state.sessionVocabs || {});
  }

  // Render score timeline list
  const timelineHtml = sessions
    .map(
      s => `
    <div style="padding: 10px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--shell); display: flex; justify-content: space-between; align-items: center;">
      <div>
        <strong>Session ${s.session_id.replace("SESSION-", "")}</strong>
        <span style="font-size: 0.8rem; color: var(--muted); margin-left: 10px;">${s.date}</span>
      </div>
      <div style="display: flex; align-items: center; gap: 12px;">
        <span class="status-pill status-good" style="font-weight: 800;">Score: ${s.score.toFixed(2)}</span>
        <span class="status-pill status-warn">${s.review_status}</span>
      </div>
    </div>
  `
    )
    .join("");

  // Feature trends list
  const trendsHtml = `
    <div style="display: grid; gap: 8px;">
      <div style="padding: 10px; border: 1px solid var(--line); border-radius: 4px; display: flex; justify-content: space-between;">
        <span>Mean Length of Utterance (MLU):</span>
        <strong>${sessions.length ? sessions[sessions.length - 1].mlu.toFixed(2) : "0.00"} words</strong>
      </div>
      <div style="padding: 10px; border: 1px solid var(--line); border-radius: 4px; display: flex; justify-content: space-between;">
        <span>Vocabulary Diversity (TTR):</span>
        <strong>${sessions.length ? sessions[sessions.length - 1].ttr.toFixed(2) : "0.00"}</strong>
      </div>
      <div style="padding: 10px; border: 1px solid var(--line); border-radius: 4px; display: flex; justify-content: space-between;">
        <span>Echolalia Ratio:</span>
        <strong>${sessions.length ? sessions[sessions.length - 1].echolalia_ratio.toFixed(2) : "0.00"}</strong>
      </div>
    </div>
  `;

  // Goal auto-tracking linked to features
  const latestSessId = sessions.length ? sessions[sessions.length - 1].session_id : null;
  const latestFeats = latestSessId ? state.extractedFeatureOutputs[latestSessId]?.features : null;
  const goalsHtml = goals
    .map(g => {
      let statusClass = "status-muted";
      let statusLabel = g.status || "active";
      let progressPct = 0;
      let progressDisplay = "";

      if (latestFeats && g.metric && g.metric !== "none") {
        const val = latestFeats[g.metric] ?? 0;
        if (g.metric === "mlu" || g.metric === "ttr") {
          const target = g.target_value;
          progressPct = Math.min(100, Math.round((val / target) * 100));
          const achieved = val >= target;
          statusClass = achieved ? "status-good" : "status-warn";
          statusLabel = achieved ? "Achieved" : "In Progress";
          progressDisplay = `(${val.toFixed(2)} / ${target.toFixed(2)})`;
        } else if (g.metric === "echolalia_ratio") {
          const target = g.target_value;
          const achieved = val <= target;
          statusClass = achieved ? "status-good" : "status-warn";
          statusLabel = achieved ? "Achieved" : "In Progress";
          progressDisplay = `(${val.toFixed(2)} / ${target.toFixed(2)})`;
          progressPct = val <= target ? 100 : Math.round((target / val) * 100);
        }
      }

      return `
        <div style="padding: 12px; border: 1px solid var(--line); border-radius: 6px; background: var(--shell); display: grid; gap: 6px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.9rem; font-weight: 700;">${g.text}</span>
            <span class="status-pill ${statusClass}">${statusLabel} ${progressDisplay}</span>
          </div>
          ${g.metric && g.metric !== "none" ? `
            <div style="height: 6px; width: 100%; background: var(--panel-soft); border-radius: 3px; overflow: hidden; margin-top: 4px;">
              <div style="height: 100%; width: ${progressPct}%; background: ${statusClass === "status-good" ? "var(--green)" : "var(--amber)"}; border-radius: 3px;"></div>
            </div>
          ` : ""}
        </div>
      `;
    })
    .join("");

  // Developmental Norm Overlay Calculation
  let normHtml = "";
  if (sessions.length > 0) {
    const latestSess = sessions[sessions.length - 1];
    const childAge = caseItem.age_months;
    
    let ageKey = "48-59";
    if (childAge < 48) ageKey = "36-47";
    else if (childAge > 59) ageKey = "60-72";
    
    const norms = state.developmentalNorms[ageKey] || { mlu: { mean: 3.8, sd: 0.5 }, ttr: { mean: 0.48, sd: 0.05 } };
    const latestFeatures = state.extractedFeatureOutputs[latestSess.session_id]?.features || {};
    
    const childMlu = latestFeatures.mlu ?? 0;
    const childTtr = latestFeatures.ttr ?? 0;
    
    const mluMean = norms.mlu.mean;
    const mluSd = norms.mlu.sd;
    const mluSdDiff = (childMlu - mluMean) / mluSd;
    const mluStatus = mluSdDiff < -1.5 ? "Delayed" : (mluSdDiff > 1.5 ? "Advanced" : "Typical");
    const mluBadgeClass = mluStatus === "Delayed" ? "status-bad" : "status-good";
    
    const ttrMean = norms.ttr.mean;
    const ttrSd = norms.ttr.sd;
    const ttrSdDiff = (childTtr - ttrMean) / ttrSd;
    const ttrStatus = ttrSdDiff < -1.5 ? "Delayed" : (ttrSdDiff > 1.5 ? "Advanced" : "Typical");
    const ttrBadgeClass = ttrStatus === "Delayed" ? "status-bad" : "status-good";
    
    normHtml = `
      <section class="glass-card" style="padding: 16px;">
        <div class="panel-title">
          <h3>Developmental Norm Overlay (วัย ${childAge} เดือน)</h3>
          <span>เปรียบเทียบเกณฑ์กลุ่มอายุ ${ageKey} เดือน</span>
        </div>
        
        <div style="display: grid; gap: 14px;">
          <!-- MLU Norm -->
          <div style="border: 1px solid var(--line); padding: 12px; border-radius: 6px; background: var(--shell);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <strong>Mean Length of Utterance (MLU):</strong>
              <span class="status-pill ${mluBadgeClass}">${mluStatus} (${mluSdDiff.toFixed(1)} SD)</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--muted); margin-bottom: 8px;">
              เกณฑ์ปกติ: ${mluMean.toFixed(1)} &plusmn; ${mluSd} คำ · ของน้องล่าสุด: <b>${childMlu.toFixed(2)} คำ</b>
            </div>
            <div style="position: relative; height: 16px; background: #e0e0e0; border-radius: 8px; overflow: visible; margin: 15px 0 5px;">
              <div style="position: absolute; left: ${Math.max(0, ((mluMean - mluSd) / 6.0) * 100)}%; right: ${Math.max(0, (1 - (mluMean + mluSd) / 6.0) * 100)}%; top: 0; bottom: 0; background: rgba(76, 175, 80, 0.3); border-radius: 2px;"></div>
              <div style="position: absolute; left: ${Math.min(100, (childMlu / 6.0) * 100)}%; top: 50%; transform: translate(-50%, -50%); width: 14px; height: 14px; border-radius: 50%; background: var(--violet); border: 2px solid white; box-shadow: 0 0 6px rgba(0,0,0,0.3);"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--muted);">
              <span>0.0 คำ</span>
              <span>ปกติ (${(mluMean - mluSd).toFixed(1)} - ${(mluMean + mluSd).toFixed(1)})</span>
              <span>6.0 คำ</span>
            </div>
          </div>
          
          <!-- TTR Norm -->
          <div style="border: 1px solid var(--line); padding: 12px; border-radius: 6px; background: var(--shell);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <strong>Type-Token Ratio (TTR - ความหลากคำ):</strong>
              <span class="status-pill ${ttrBadgeClass}">${ttrStatus} (${ttrSdDiff.toFixed(1)} SD)</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--muted); margin-bottom: 8px;">
              เกณฑ์ปกติ: ${ttrMean.toFixed(2)} &plusmn; ${ttrSd} · ของน้องล่าสุด: <b>${childTtr.toFixed(2)}</b>
            </div>
            <div style="position: relative; height: 16px; background: #e0e0e0; border-radius: 8px; overflow: visible; margin: 15px 0 5px;">
              <div style="position: absolute; left: ${Math.max(0, ((ttrMean - ttrSd) / 1.0) * 100)}%; right: ${Math.max(0, (1 - (ttrMean + ttrSd) / 1.0) * 100)}%; top: 0; bottom: 0; background: rgba(76, 175, 80, 0.3); border-radius: 2px;"></div>
              <div style="position: absolute; left: ${Math.min(100, (childTtr / 1.0) * 100)}%; top: 50%; transform: translate(-50%, -50%); width: 14px; height: 14px; border-radius: 50%; background: var(--violet); border: 2px solid white; box-shadow: 0 0 6px rgba(0,0,0,0.3);"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--muted);">
              <span>0.0</span>
              <span>ปกติ (${(ttrMean - ttrSd).toFixed(2)} - ${(ttrMean + ttrSd).toFixed(2)})</span>
              <span>1.0</span>
            </div>
          </div>
        </div>
      </section>
    `;
  }

  // Session Diff View Calculation
  let diffHtml = "";
  if (sessions.length >= 2) {
    const diffSessionIdA = state.diffSessionIdA || sessions[0].session_id;
    const diffSessionIdB = state.diffSessionIdB || sessions[sessions.length - 1].session_id;
    
    const sessA = state.sessions.find(s => s.session_id === diffSessionIdA);
    const sessB = state.sessions.find(s => s.session_id === diffSessionIdB);
    
    if (sessA && sessB) {
      const featA = state.extractedFeatureOutputs[diffSessionIdA]?.features || {};
      const featB = state.extractedFeatureOutputs[diffSessionIdB]?.features || {};
      
      const mluA = featA.mlu ?? 0;
      const mluB = featB.mlu ?? 0;
      const ttrA = featA.ttr ?? 0;
      const ttrB = featB.ttr ?? 0;
      const echoA = featA.echolalia_ratio ?? 0;
      const echoB = featB.echolalia_ratio ?? 0;
      const untellA = featA.unintelligible_ratio ?? 0;
      const untellB = featB.unintelligible_ratio ?? 0;
      
      const mluChange = mluB - mluA;
      const ttrChange = ttrB - ttrA;
      const echoChange = echoB - echoA;
      const untellChange = untellB - untellA;
      
      const vocabA = state.sessionVocabs[diffSessionIdA] || [];
      const vocabB = state.sessionVocabs[diffSessionIdB] || [];
      const wordsA = new Set(vocabA.map(v => v.word));
      const newWordsUsed = vocabB.filter(v => !wordsA.has(v.word)).map(v => v.word);
      
      diffHtml = `
        <section class="glass-card" style="padding: 16px; grid-column: span 2;">
          <div class="panel-title" style="border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-bottom: 14px;">
            <h3>⚖ เปรียบเทียบผลลัพธ์ข้ามเซสชัน (Session Diff View)</h3>
            <span>วิเคราะห์พัฒนาการประโยคและคำศัพท์อย่างละเอียด</span>
          </div>
          
          <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 16px;">
            <label>เปรียบเทียบเซสชัน A:
              <select id="diff-session-select-a" style="padding: 6px; border-radius: 4px; border: 1px solid var(--line);">
                ${sessions.map(s => `<option value="${s.session_id}" ${s.session_id === diffSessionIdA ? "selected" : ""}>Session ${s.session_id.replace("SESSION-", "")} (${s.session_date})</option>`).join("")}
              </select>
            </label>
            <span style="font-size: 1.2rem; align-self: flex-end; margin-bottom: 4px;">➔</span>
            <label>เปรียบเทียบเซสชัน B:
              <select id="diff-session-select-b" style="padding: 6px; border-radius: 4px; border: 1px solid var(--line);">
                ${sessions.map(s => `<option value="${s.session_id}" ${s.session_id === diffSessionIdB ? "selected" : ""}>Session ${s.session_id.replace("SESSION-", "")} (${s.session_date})</option>`).join("")}
              </select>
            </label>
          </div>
          
          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px;">
            <div style="padding: 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--shell); text-align: center;">
              <small style="color: var(--muted); display: block;">ความยาวประโยค (MLU)</small>
              <strong>${mluA.toFixed(2)} ➔ ${mluB.toFixed(2)}</strong>
              <div style="font-size: 0.82rem; font-weight: 700; color: ${mluChange >= 0 ? "var(--green)" : "var(--rose)"}; margin-top: 4px;">
                ${mluChange >= 0 ? "+" : ""}${mluChange.toFixed(2)} (${mluChange >= 0 ? "เพิ่มขึ้น" : "ลดลง"})
              </div>
            </div>
            
            <div style="padding: 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--shell); text-align: center;">
              <small style="color: var(--muted); display: block;">ความหลากหลายของคำ (TTR)</small>
              <strong>${ttrA.toFixed(2)} ➔ ${ttrB.toFixed(2)}</strong>
              <div style="font-size: 0.82rem; font-weight: 700; color: ${ttrChange >= 0 ? "var(--green)" : "var(--rose)"}; margin-top: 4px;">
                ${ttrChange >= 0 ? "+" : ""}${ttrChange.toFixed(2)} (${ttrChange >= 0 ? "ดีขึ้น" : "ลดลง"})
              </div>
            </div>
            
            <div style="padding: 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--shell); text-align: center;">
              <small style="color: var(--muted); display: block;">อัตราการพูดซ้ำ (Echolalia)</small>
              <strong>${(echoA*100).toFixed(0)}% ➔ ${(echoB*100).toFixed(0)}%</strong>
              <div style="font-size: 0.82rem; font-weight: 700; color: ${echoChange <= 0 ? "var(--green)" : "var(--rose)"}; margin-top: 4px;">
                ${echoChange.toFixed(2)} (${echoChange <= 0 ? "ลดลง (ดี)" : "เพิ่มขึ้น"})
              </div>
            </div>
            
            <div style="padding: 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--shell); text-align: center;">
              <small style="color: var(--muted); display: block;">ออกเสียงไม่ชัดเจน</small>
              <strong>${(untellA*100).toFixed(0)}% ➔ ${(untellB*100).toFixed(0)}%</strong>
              <div style="font-size: 0.82rem; font-weight: 700; color: ${untellChange <= 0 ? "var(--green)" : "var(--rose)"}; margin-top: 4px;">
                ${untellChange.toFixed(2)} (${untellChange <= 0 ? "ลดลง (ดี)" : "เพิ่มขึ้น"})
              </div>
            </div>
          </div>
          
          <div style="border: 1px solid var(--line); padding: 12px; border-radius: 6px; background: var(--violet-soft);">
            <strong style="color: var(--violet-strong); font-size: 0.88rem; display: block; margin-bottom: 6px;">🆕 คำศัพท์ใหม่ที่เพิ่มขึ้นใน Session B (New Words Introduced):</strong>
            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
              ${newWordsUsed.length > 0 
                ? newWordsUsed.map(w => `<span style="padding: 3px 6px; background: white; border: 1px solid var(--violet); border-radius: 4px; font-weight: 700; font-size: 0.82rem; color: var(--violet-strong);">${w}</span>`).join("")
                : '<span style="color: var(--muted); font-size: 0.82rem;">ไม่มีคำศัพท์ใหม่ที่แตกต่างกันชัดเจน</span>'
              }
            </div>
          </div>
        </section>
      `;
    }
  }

  const radarChartHtml = renderRadarChart(radarEntries(caseItem));

  return `
    ${renderSafetyBanner()}
    <section class="dashboard-command" style="margin-bottom: 16px;">
      <div>
        <h2>Printable / Exportable Progress Report</h2>
        <p style="color: var(--muted); font-size: 0.85rem;">This tool is for progress tracking and clinical decision support only.</p>
      </div>
      <div style="display: flex; gap: 10px;">
        <button class="secondary-action" id="download-progress-md-btn" data-case-id="${caseItem.case_id}">
          Download Markdown
        </button>
        <button class="primary-action" id="print-progress-pdf-btn">
          Print / Save PDF
        </button>
      </div>
    </section>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
      <section class="glass-card" style="padding: 16px;">
        <div class="panel-title">
          <h3>Score Timeline</h3>
          <span>longitudinal concern metrics</span>
        </div>
        <div style="display: grid; gap: 8px;">
          ${timelineHtml || '<p class="empty-state">No session timeline scores found.</p>'}
        </div>
      </section>

      ${radarChartHtml}
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
      <section class="glass-card" style="padding: 16px;">
        <div class="panel-title">
          <h3>Feature Trends Over Sessions</h3>
          <span>longitudinal language feature values</span>
        </div>
        ${trendsHtml}
      </section>

      ${normHtml || `
        <section class="glass-card" style="padding: 16px;">
          <p class="empty-state">No norm comparison overlay available. Add sessions first.</p>
        </section>
      `}
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
      <section class="glass-card" style="padding: 16px; grid-column: span 2;">
        <div class="panel-title">
          <h3>Therapy Goal Progress</h3>
          <span>caseload active goals</span>
        </div>
        <div style="display: grid; gap: 10px;">
          ${goalsHtml || '<p class="empty-state">No active goal records for this case.</p>'}
        </div>
      </section>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
      <section class="glass-card" style="padding: 16px; grid-column: span 2;">
        <div class="panel-title" style="border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-bottom: 14px;">
          <h3>📝 สรุปผลทางคลินิกภาษาไทย (Safe Thai Summary)</h3>
          <span>บทสรุปผลสำหรับผู้ปกครองและบันทึกเพิ่มเติมของนักบำบัด (สามารถแก้ไขได้และจะนำไปเขียนในรายงานสรุป)</span>
        </div>
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div style="padding: 10px; border: 1px solid var(--violet); border-radius: 6px; background: var(--violet-soft); font-size: 0.85rem; color: var(--violet-strong); text-align: left;">
            ⚠️ <b>ข้อความเตือนความปลอดภัยเชิงคลินิก (Clinical Disclaimer):</b> ระบบนี้เป็นระบบสนับสนุนการตัดสินใจทางคลินิกจำลองในขั้นวิจัย (Research Prototype) ไม่ใช่เครื่องมือทางการแพทย์และไม่สามารถใช้แทนการวินิจฉัยโรคได้ ผลลัพธ์ทั้งหมดต้องได้รับตรวจทานและแปรผลร่วมโดยนักบำบัดภาษาและบุคลากรทางการแพทย์ที่เชี่ยวชาญ
          </div>
          <textarea id="thai-summary-textarea" 
                    style="width: 100%; min-height: 150px; padding: 12px; border-radius: var(--radius); border: 1px solid var(--line); font-family: inherit; line-height: 1.5; background: var(--shell); color: var(--text);"
                    placeholder="ป้อนบทสรุปพัฒนาการเป็นภาษาไทยเพื่อพิมพ์ในรายงาน..."
          >${currentThaiSummary}</textarea>
        </div>
      </section>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
      ${diffHtml}
    </div>
  `;
}

export function bindProgressReports(navigate) {
  const textarea = document.getElementById("thai-summary-textarea");
  if (textarea) {
    textarea.addEventListener("input", (e) => {
      const state = store.getState();
      const caseId = state.selectedCaseId;
      const updatedSummaries = { ...(state.therapistThaiSummaries || {}), [caseId]: e.target.value };
      store.setState({ therapistThaiSummaries: updatedSummaries });
    });
  }

  const downloadBtn = document.getElementById("download-progress-md-btn");
  if (downloadBtn) {
    downloadBtn.addEventListener("click", () => {
      const caseId = downloadBtn.getAttribute("data-case-id");
      const state = store.getState();

      const caseItem = state.cases.find(c => c.case_id === caseId);
      const childSessions = state.sessions.filter(s => s.case_id === caseId);
      const currentSummaryText = document.getElementById("thai-summary-textarea")?.value || "";

      // Generate report using buildProgressReportMarkdown
      const reportMd = buildProgressReportMarkdown(
        caseItem,
        childSessions,
        state.extractedFeatureOutputs,
        state.aiDecisionOutputs,
        state.transcripts,
        currentSummaryText
      );

      // Create new report object and save to store state
      const reportId = `REPORT-${String(state.generatedReports.length + 1).padStart(3, "0")}`;
      const newReport = {
        report_id: reportId,
        case_id: caseId,
        owner_user_id: caseItem.owner_user_id,
        title: `Progress Report: ${caseItem.anonymized_child_code}`,
        ai_summary: reportMd,
        export_status: "completed",
        created_at: new Date().toISOString()
      };
      const nextReports = [...(state.generatedReports || []).filter(r => r.case_id !== caseId), newReport];
      store.setState({ generatedReports: nextReports });

      const a = document.createElement("a");
      const file = new Blob([reportMd], { type: "text/markdown" });
      a.href = URL.createObjectURL(file);
      a.download = `${caseItem.anonymized_child_code}_progress_report.md`;
      a.click();

      addAudit("report_exported", "ChildCase", caseId, `Exported progress report markdown for case ${caseId}`);
    });
  }

  const printBtn = document.getElementById("print-progress-pdf-btn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      const caseId = store.getState().selectedCaseId;
      const state = store.getState();
      const caseItem = state.cases.find(c => c.case_id === caseId);
      const childSessions = state.sessions.filter(s => s.case_id === caseId);
      const currentSummaryText = document.getElementById("thai-summary-textarea")?.value || "";

      const reportMd = buildProgressReportMarkdown(
        caseItem,
        childSessions,
        state.extractedFeatureOutputs,
        state.aiDecisionOutputs,
        state.transcripts,
        currentSummaryText
      );

      const reportId = `REPORT-${String(state.generatedReports.length + 1).padStart(3, "0")}`;
      const newReport = {
        report_id: reportId,
        case_id: caseId,
        owner_user_id: caseItem.owner_user_id,
        title: `Progress Report: ${caseItem.anonymized_child_code}`,
        ai_summary: reportMd,
        export_status: "completed",
        created_at: new Date().toISOString()
      };
      const nextReports = [...(state.generatedReports || []).filter(r => r.case_id !== caseId), newReport];
      store.setState({ generatedReports: nextReports });

      window.print();
      addAudit("print_report", "ChildCase", store.getState().selectedCaseId, "Printed / Saved PDF progress report.");
    });
  }

  const selectA = document.getElementById("diff-session-select-a");
  if (selectA) {
    selectA.addEventListener("change", (e) => {
      store.setState({ diffSessionIdA: e.target.value });
      navigate("progress");
    });
  }

  const selectB = document.getElementById("diff-session-select-b");
  if (selectB) {
    selectB.addEventListener("change", (e) => {
      store.setState({ diffSessionIdB: e.target.value });
      navigate("progress");
    });
  }
}

function generateAutoSummaryText(sessions, sessionVocabs) {
  if (!sessions || sessions.length < 2) {
    return "- ข้อมูลเซสชันไม่เพียงพอสำหรับการวิเคราะห์แนวโน้มพัฒนาการข้ามเซสชัน (ต้องการอย่างน้อย 2 เซสชัน)";
  }

  const sessA = sessions[0];
  const sessB = sessions[sessions.length - 1];

  const mluA = sessA.mlu ?? 0;
  const mluB = sessB.mlu ?? 0;
  const ttrA = sessA.ttr ?? 0;
  const ttrB = sessB.ttr ?? 0;
  const echoA = sessA.echolalia_ratio ?? 0;
  const echoB = sessB.echolalia_ratio ?? 0;

  const mluChange = mluB - mluA;
  const ttrChange = ttrB - ttrA;
  const echoChange = echoB - echoA;

  let mluDesc = "";
  if (mluChange > 0.2) {
    mluDesc = `มีความก้าวหน้าขึ้นในการเพิ่มความยาวประโยคเฉลี่ย (MLU) (เพิ่มขึ้น ${mluChange.toFixed(2)} คำ จากเซสชันแรกที่ ${mluA.toFixed(2)} คำ เป็น ${mluB.toFixed(2)} คำ)`;
  } else if (mluChange < -0.2) {
    mluDesc = `ความยาวประโยคเฉลี่ย (MLU) ลดลงเล็กน้อย (ลดลง ${Math.abs(mluChange).toFixed(2)} คำ จาก ${mluA.toFixed(2)} คำ เป็น ${mluB.toFixed(2)} คำ) ควรติดตามและกระตุ้นการสื่อสารอย่างต่อเนื่อง`;
  } else {
    mluDesc = `ความยาวประโยคเฉลี่ย (MLU) ค่อนข้างคงที่ (อยู่ที่ประมาณ ${mluB.toFixed(2)} คำ)`;
  }

  let ttrDesc = "";
  if (ttrChange > 0.05) {
    ttrDesc = `มีความหลากคำและคลังคำศัพท์ที่กว้างขวางมากขึ้น (TTR เพิ่มขึ้น ${ttrChange.toFixed(2)} จาก ${ttrA.toFixed(2)} เป็น ${ttrB.toFixed(2)})`;
  } else {
    ttrDesc = `ความหลากหลายในการใช้คำศัพท์ค่อนข้างคงที่ (TTR ล่าสุดอยู่ที่ ${ttrB.toFixed(2)})`;
  }

  let echoDesc = "";
  if (echoChange < -0.05) {
    echoDesc = `มีอัตราการพูดซ้ำเลียนแบบ (Echolalia) ลดลงอย่างเห็นได้ชัด (ลดลง ${(Math.abs(echoChange) * 100).toFixed(0)}% จาก ${(echoA * 100).toFixed(0)}% เป็น ${(echoB * 100).toFixed(0)}%) แสดงถึงการตอบสนองที่ตรงวัตถุประสงค์ขึ้น`;
  } else if (echoChange > 0.05) {
    echoDesc = `พบพฤติกรรมการพูดซ้ำเลียนแบบ (Echolalia) เพิ่มขึ้นเล็กน้อย (เพิ่มขึ้น ${(echoChange * 100).toFixed(0)}% จาก ${(echoA * 100).toFixed(0)}% เป็น ${(echoB * 100).toFixed(0)}%) ควรส่งเสริมการพูดตอบโต้ที่เป็นธรรมชาติมากขึ้น`;
  } else {
    echoDesc = `อัตราการพูดซ้ำเลียนแบบค่อนข้างคงที่ (อยู่ที่ประมาณ ${(echoB * 100).toFixed(0)}%)`;
  }

  const vocabA = sessionVocabs[sessA.session_id] || [];
  const vocabB = sessionVocabs[sessB.session_id] || [];
  const wordsA = new Set(vocabA.map(v => v.word));
  const newWordsUsed = vocabB.filter(v => !wordsA.has(v.word)).map(v => v.word);
  let vocabDesc = "ไม่พบคำศัพท์ใหม่ที่แตกต่างอย่างมีนัยสำคัญ";
  if (newWordsUsed.length > 0) {
    vocabDesc = `ตรวจพบคำศัพท์ใหม่ที่เป็นประโยชน์เพิ่มเติมในเซสชันล่าสุด ได้แก่: ${newWordsUsed.slice(0, 5).join(', ')}`;
  }

  return `- **แนวโน้มความยาวประโยคเฉลี่ย (MLU Trend):** ${mluDesc}
- **ความหลากหลายของคำศัพท์ (TTR Trend):** ${ttrDesc}
- **พฤติกรรมการสื่อสารเลียนแบบ (Echolalia Trend):** ${echoDesc}
- **การเพิ่มคลังคำศัพท์ (Vocabulary Expansion):** ${vocabDesc}`;
}
