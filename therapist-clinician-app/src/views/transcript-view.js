import { store } from "../store/state.js";
import { getVisibleSessions } from "../services/session-service.js";
import { getVisibleCases } from "../services/case-service.js";
import { updateUtterance, saveTherapistReview, generateDecisionSupport } from "../services/review-service.js";
import { checkTranscriptQuality, wrapWithDisclaimer } from "@shared/services/safety-service.js";
import { exportCHAT, exportJSON } from "@shared/services/export-service.js";
import { renderUtteranceRow } from "../components/utterance-editor.js";
import { renderPipelineStatus } from "../components/pipeline-status.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { addAudit } from "../services/audit-service.js";
import { extractAllFeatures } from "@shared/services/feature-extraction-service.js";
import { updateSessionStatus } from "../services/session-service.js";
import { createTranscript } from "@shared/models";

export function renderTranscriptReview() {
  const state = store.getState();
  const sessions = getVisibleSessions();
  const cases = getVisibleCases();

  const selectedSession = sessions.find(s => s.session_id === state.selectedSessionId) || sessions[0];
  if (!selectedSession) {
    return `<p class="empty-state">No visible sessions for transcript QA.</p>`;
  }

  const childCase = cases.find(c => c.case_id === selectedSession.case_id);
  const transcriptLines = state.transcriptLines[selectedSession.session_id] || [];
  const transcriptRecord = state.transcripts[selectedSession.session_id];

  // Run a mock QA review of the raw text
  let qaStatusHtml = "";
  if (transcriptRecord) {
    const qa = checkTranscriptQuality(transcriptRecord.transcript_text, transcriptLines);
    const badgeClass = qa.quality === "pass" ? "status-good" : qa.quality === "needs_review" ? "status-warn" : "status-bad";

    qaStatusHtml = `
      <div class="panel" style="padding: 16px; margin-bottom: 16px;">
        <div class="panel-title">
          <h3>Transcript QA Results</h3>
          <span class="status-pill ${badgeClass}">QA: ${qa.quality} (Score: ${qa.score})</span>
        </div>
        <div style="font-size: 0.9rem; display: grid; gap: 8px;">
          ${
            qa.warnings.length
              ? qa.warnings
                  .map(
                    w => `
            <div style="color: ${w.severity === "error" ? "var(--rose)" : "var(--amber)"}; font-weight: 700;">
              ⚠ [${w.code}] ${w.message}
            </div>
          `
                  )
                  .join("")
              : '<div style="color: var(--green); font-weight: 700;">✓ No transcript validation issues found.</div>'
          }
        </div>
      </div>
    `;
  }

  const selectSessionHtml = `
    <label>Select Session to Review
      <select id="qa-session-select" style="padding: 6px; border-radius: 4px; border: 1px solid var(--line); margin-bottom: 16px;">
        ${sessions
          .map(
            s => `
          <option value="${s.session_id}" ${s.session_id === selectedSession.session_id ? "selected" : ""}>
            Session ${s.session_id.replace("SESSION-", "")} (${s.session_date})
          </option>
        `
          )
          .join("")}
      </select>
    </label>
  `;

  let detailsHtml = "";
  if (transcriptRecord) {
    detailsHtml = `
      ${renderPipelineStatus(selectedSession.processing_status)}
      ${qaStatusHtml}
      
      <div style="display: grid; grid-template-columns: 1.3fr 0.7fr; gap: 20px;">
        <section class="panel" style="padding: 16px;">
          <div class="panel-title">
            <h3>CHAT transcript viewer and correction UI</h3>
            <span>Session: ${selectedSession.session_id}</span>
          </div>
          
          <table style="width: 100%; border-collapse: collapse;">
            <thead>
              <tr style="border-bottom: 2px solid var(--line); text-align: left;">
                <th style="padding: 8px;">Speaker</th>
                <th style="padding: 8px;">Utterance Text</th>
                <th style="padding: 8px; text-align: right;">Confidence</th>
              </tr>
            </thead>
            <tbody>
              ${transcriptLines
                .map((line, idx) => renderUtteranceRow(line, idx, selectedSession.session_id))
                .join("")}
            </tbody>
          </table>
          
          <div style="margin-top: 16px; display: flex; gap: 10px;">
            <button class="primary-action" id="save-transcript-edits-btn" data-session-id="${selectedSession.session_id}">
              Save Transcript Corrections
            </button>
            <button class="secondary-action" id="export-chat-btn" data-session-id="${selectedSession.session_id}">
              Export CHAT-like File
            </button>
            <button class="secondary-action" id="export-json-btn" data-session-id="${selectedSession.session_id}">
              Export JSON Dataset
            </button>
          </div>
        </section>

        <section class="panel" style="padding: 16px;">
          <div class="panel-title">
            <h3>Evidence Review & Therapist Notes</h3>
            <span>requires clinical signature</span>
          </div>
          <div style="display: grid; gap: 12px;">
            <label>Clinical Notes
              <textarea id="review-notes" style="min-height: 120px;" placeholder="Add therapist observations...">${selectedSession.notes || ""}</textarea>
            </label>
            <div style="padding: 12px; background: var(--violet-soft); border-radius: var(--radius);">
              <strong>Evidence Review Panel</strong>
              <p style="font-size: 0.8rem; margin-top: 6px; color: var(--violet-strong);">
                Please check and correct any low-confidence child lines before finalizing decision support.
              </p>
            </div>
            <button class="primary-action" id="submit-clinical-review-btn" data-session-id="${selectedSession.session_id}">
              Sign off Review
            </button>
          </div>
        </section>
      </div>
    `;
  } else {
    detailsHtml = `
      <div style="padding: 24px; text-align: center; border: 1px dashed var(--line); border-radius: var(--radius); background: var(--shell);">
        <h3>CHAT transcript workflow</h3>
        <p>No transcript exists for this session yet.</p>
        <p style="font-size: 0.85rem; color: var(--muted); margin-bottom: 12px;">
          To test transcription, please upload an audio file or click below to generate a mock transcript from metadata.
        </p>
        
        <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
          <button class="primary-action" id="generate-mock-transcript-btn" data-session-id="${selectedSession.session_id}">
            Generate mock CHAT from audio metadata
          </button>
          <input type="file" id="transcript-upload-input" accept=".cha" style="display: none;" />
          <button class="secondary-action" id="upload-cha-btn">
            Upload/select .cha transcript
          </button>
        </div>
        <p style="font-size: 0.8rem; color: var(--muted); margin-top: 12px;">
          * Note: Real audio-to-CHAT execution is deferred. No file bytes are persisted.
        </p>
      </div>
    `;
  }

  return `
    ${renderSafetyBanner()}
    <div style="margin-bottom: 16px;">
      ${selectSessionHtml}
    </div>
    ${detailsHtml}
  `;
}

export function bindTranscriptReview(navigate) {
  // Session switcher
  const qaSelect = document.getElementById("qa-session-select");
  if (qaSelect) {
    qaSelect.addEventListener("change", e => {
      store.setState({ selectedSessionId: e.target.value });
      navigate("transcript");
    });
  }

  // Generate mock transcript
  const mockBtn = document.getElementById("generate-mock-transcript-btn");
  if (mockBtn) {
    mockBtn.addEventListener("click", () => {
      const sessId = mockBtn.getAttribute("data-session-id");
      const state = store.getState();
      const session = state.sessions.find(s => s.session_id === sessId);
      const childCase = state.cases.find(c => c.case_id === session.case_id);

      const ageYears = Math.floor((childCase?.age_months || 48) / 12);
      const ageMonths = String((childCase?.age_months || 48) % 12).padStart(2, "0");
      const sex = childCase?.sex === "male" || childCase?.sex === "female" ? childCase.sex : "";

      const rawText = `@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\tteng|Mock|CHI|${ageYears};${ageMonths}.00|${sex}|||Target_Child|||
@ID:\tteng|Mock|MOT|||||Mother|||
*CHI:\twant car .
*MOT:\twhich car do you want ?
*CHI:\tred car .
@End`;

      const utterances = [
        { utterance_id: "UTT-001", speaker_label: "CHILD", text: "want car .", start_time: 1.0, end_time: 2.2, duration: 1.2, word_count: 2, confidence: 0.89 },
        { utterance_id: "UTT-002", speaker_label: "CAREGIVER", text: "which car do you want ?", start_time: 2.8, end_time: 4.5, duration: 1.7, word_count: 5, confidence: 0.93 },
        { utterance_id: "UTT-003", speaker_label: "CHILD", text: "red car .", start_time: 5.0, end_time: 6.2, duration: 1.2, word_count: 2, confidence: 0.86 }
      ];

      const transcriptLines = [
        { speaker: "CHI", text: "want car .", confidence: 0.89 },
        { speaker: "MOT", text: "which car do you want ?", confidence: 0.93 },
        { speaker: "CHI", text: "red car .", confidence: 0.86 }
      ];

      const transcriptId = `TRANSCRIPT-${String(Object.keys(state.transcripts).length + 1).padStart(3, "0")}`;
      const transcriptRecord = createTranscript({
        transcript_id: transcriptId,
        session_id: sessId,
        case_id: session.case_id,
        owner_user_id: session.owner_user_id,
        original_filename: "generated_mock.cha",
        transcript_text: rawText,
        review_status: "awaiting_review",
        qa_status: "pass",
        qa_score: 100,
        qa_issues: []
      });

      // Extract features (Module 7)
      const featuresSet = extractAllFeatures(
        utterances.map(u => ({ ...u, confidence: u.confidence })),
        childCase?.age_months || 48
      );

      // Generate clinical decision support
      const aiOutput = generateDecisionSupport(featuresSet.features);

      const updatedTranscripts = { ...state.transcripts, [sessId]: transcriptRecord };
      const updatedLines = { ...state.transcriptLines, [sessId]: transcriptLines };
      const updatedFeatures = { ...state.extractedFeatureOutputs, [sessId]: featuresSet };
      const updatedAI = { ...state.aiDecisionOutputs, [sessId]: aiOutput };

      store.setState({
        transcripts: updatedTranscripts,
        transcriptLines: updatedLines,
        extractedFeatureOutputs: updatedFeatures,
        aiDecisionOutputs: updatedAI
      });

      updateSessionStatus(sessId, {
        transcript_id: transcriptId,
        processing_status: "transcript_ready",
        feature_extraction_status: "completed",
        ai_analysis_status: "completed",
        therapist_review_status: "awaiting_review"
      });

      addAudit("transcription_complete", "Session", sessId, "Generated mock CHAT from audio metadata.");
      navigate("transcript");
    });
  }

  // Upload .cha file
  const uploadBtn = document.getElementById("upload-cha-btn");
  const fileInput = document.getElementById("transcript-upload-input");
  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", e => {
      const file = e.target.files[0];
      if (file) {
        handleTranscriptUpload(file, navigate);
      }
    });
  }

  // Save Transcript Corrections click
  const saveCorrectionsBtn = document.getElementById("save-transcript-edits-btn");
  if (saveCorrectionsBtn) {
    saveCorrectionsBtn.addEventListener("click", () => {
      const sessId = saveCorrectionsBtn.getAttribute("data-session-id");
      const rows = document.querySelectorAll(".utterance-row");

      rows.forEach(row => {
        const idx = parseInt(row.getAttribute("data-line-index"));
        const select = row.querySelector(".speaker-edit-select");
        const input = row.querySelector(".text-edit-input");
        if (select && input) {
          updateUtterance(sessId, idx, input.value, select.value);
        }
      });

      // Re-run feature extraction and decision support with updated corrections
      const state = store.getState();
      const lines = state.transcriptLines[sessId] || [];
      const childCase = state.cases.find(c => c.case_id === state.selectedCaseId);

      const mappedUtterances = lines.map((l, index) => ({
        utterance_id: `UTT-${String(index + 1).padStart(3, "0")}`,
        speaker_label: l.speaker === "CHI" ? "CHILD" : (l.speaker === "MOT" ? "CAREGIVER" : "THERAPIST"),
        text: l.text,
        start_time: index * 2.0,
        end_time: index * 2.0 + 1.5,
        duration: 1.5,
        word_count: l.text.split(/\s+/).filter(Boolean).length,
        confidence: l.confidence
      }));

      const newFeatures = extractAllFeatures(mappedUtterances, childCase?.age_months || 48);
      const newAI = generateDecisionSupport(newFeatures.features);

      store.setState({
        extractedFeatureOutputs: { ...state.extractedFeatureOutputs, [sessId]: newFeatures },
        aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: newAI }
      });

      alert("Transcript corrections saved. Features and Decision Support scores recomputed.");
      navigate("transcript");
    });
  }

  // Export Buttons
  const expChatBtn = document.getElementById("export-chat-btn");
  if (expChatBtn) {
    expChatBtn.addEventListener("click", () => {
      const sessId = expChatBtn.getAttribute("data-session-id");
      const state = store.getState();
      const session = state.sessions.find(s => s.session_id === sessId);
      const childCase = state.cases.find(c => c.case_id === session.case_id);
      const lines = state.transcriptLines[sessId];

      const chatText = exportCHAT(session, childCase, lines);
      downloadFile(chatText, `${sessId}_transcript.cha`, "text/plain");
      addAudit("export_chat", "Session", sessId, "Exported transcript as CHAT-like file.");
    });
  }

  const expJsonBtn = document.getElementById("export-json-btn");
  if (expJsonBtn) {
    expJsonBtn.addEventListener("click", () => {
      const sessId = expJsonBtn.getAttribute("data-session-id");
      const state = store.getState();
      const session = state.sessions.find(s => s.session_id === sessId);
      const childCase = state.cases.find(c => c.case_id === session.case_id);
      const lines = state.transcriptLines[sessId];
      const features = state.extractedFeatureOutputs[sessId];
      const ai = state.aiDecisionOutputs[sessId];

      const jsonObj = exportJSON(session, childCase, lines, features, ai);
      downloadFile(JSON.stringify(jsonObj, null, 2), `${sessId}_dataset.json`, "application/json");
      addAudit("export_json", "Session", sessId, "Exported session dataset as JSON.");
    });
  }

  // Sign off Review click
  const submitReviewBtn = document.getElementById("submit-clinical-review-btn");
  if (submitReviewBtn) {
    submitReviewBtn.addEventListener("click", () => {
      const sessId = submitReviewBtn.getAttribute("data-session-id");
      const notes = document.getElementById("review-notes").value;

      saveTherapistReview({
        sessionId: sessId,
        notes,
        approvedSummary: "Approved speech sample review."
      });

      alert("Clinical review submitted successfully.");
      navigate("dashboard");
    });
  }
}

function handleTranscriptUpload(file, navigate) {
  const reader = new FileReader();
  reader.onload = e => {
    const text = e.target.result;
    const validation = checkTranscriptQuality(text);

    if (validation.quality === "fail") {
      alert("CHAT Upload Error:\n" + validation.warnings.map(w => `- ${w.message}`).join("\n"));
      return;
    }

    const state = store.getState();
    const sessId = state.selectedSessionId;
    const session = state.sessions.find(s => s.session_id === sessId);

    // Basic regex parser for CHA lines
    const transcriptLines = [];
    const lines = text.split("\n");
    lines.forEach(l => {
      if (l.startsWith("*CHI:")) {
        transcriptLines.push({ speaker: "CHI", text: l.replace("*CHI:", "").trim(), confidence: 1.0 });
      } else if (l.startsWith("*MOT:")) {
        transcriptLines.push({ speaker: "MOT", text: l.replace("*MOT:", "").trim(), confidence: 1.0 });
      } else if (l.startsWith("*INV:")) {
        transcriptLines.push({ speaker: "INV", text: l.replace("*INV:", "").trim(), confidence: 1.0 });
      }
    });

    const transcriptId = `TRANSCRIPT-${String(Object.keys(state.transcripts).length + 1).padStart(3, "0")}`;
    const transcriptRecord = createTranscript({
      transcript_id: transcriptId,
      session_id: sessId,
      case_id: session.case_id,
      owner_user_id: session.owner_user_id,
      original_filename: file.name,
      transcript_text: text,
      review_status: "awaiting_review",
      qa_status: validation.quality,
      qa_score: validation.score,
      qa_issues: validation.warnings
    });

    // Run pipeline
    const childCase = state.cases.find(c => c.case_id === session.case_id);
    const mappedUtterances = transcriptLines.map((l, index) => ({
      utterance_id: `UTT-${String(index + 1).padStart(3, "0")}`,
      speaker_label: l.speaker === "CHI" ? "CHILD" : (l.speaker === "MOT" ? "CAREGIVER" : "THERAPIST"),
      text: l.text,
      start_time: index * 2.0,
      end_time: index * 2.0 + 1.5,
      duration: 1.5,
      word_count: l.text.split(/\s+/).filter(Boolean).length,
      confidence: 1.0
    }));

    const featuresSet = extractAllFeatures(mappedUtterances, childCase?.age_months || 48);
    const aiOutput = generateDecisionSupport(featuresSet.features);

    store.setState({
      transcripts: { ...state.transcripts, [sessId]: transcriptRecord },
      transcriptLines: { ...state.transcriptLines, [sessId]: transcriptLines },
      extractedFeatureOutputs: { ...state.extractedFeatureOutputs, [sessId]: featuresSet },
      aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: aiOutput }
    });

    updateSessionStatus(sessId, {
      transcript_id: transcriptId,
      processing_status: "transcript_ready",
      feature_extraction_status: "completed",
      ai_analysis_status: "completed",
      therapist_review_status: "awaiting_review"
    });

    addAudit("handleTranscriptUpload", "Transcript", transcriptId, `Uploaded CHA transcript file: ${file.name}`);
    navigate("transcript");
  };
  reader.readAsText(file);
}

function downloadFile(content, filename, contentType) {
  const a = document.createElement("a");
  const file = new Blob([content], { type: contentType });
  a.href = URL.createObjectURL(file);
  a.download = filename;
  a.click();
}
