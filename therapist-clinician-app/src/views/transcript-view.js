import { store } from "../store/state.js";
import { getVisibleSessions } from "../services/session-service.js";
import { getVisibleCases } from "../services/case-service.js";
import { updateUtterance, saveTherapistReview } from "../services/review-service.js";
import { checkTranscriptQuality } from "@shared/services/safety-service.js";
import { exportCHAT, exportJSON } from "@shared/services/export-service.js";
import { renderUtteranceRow } from "../components/utterance-editor.js";
import { renderPipelineStatus } from "../components/pipeline-status.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { addAudit } from "../services/audit-service.js";
import { updateSessionStatus } from "../services/session-service.js";
import { renderAccessDenied } from "../components/access-denied.js";
import { escapeHtml } from "@shared/utils/html.js";
import {
  buildEvidenceItems,
  buildFeatureAndAiOutputs,
  buildTranscriptWorkflowArtifacts
} from "../services/transcript-workflow-service.js";

export function renderTranscriptReview() {
  const state = store.getState();
  const sessions = getVisibleSessions();
  const cases = getVisibleCases();

  const selectedVisibleSession = sessions.find(s => s.session_id === state.selectedSessionId);
  const selectedSessionExists = state.sessions.some(s => s.session_id === state.selectedSessionId);
  if (!selectedVisibleSession && selectedSessionExists) {
    return renderAccessDenied("Access denied: this session is not assigned to your account.");
  }
  const selectedSession = selectedVisibleSession || sessions[0];
  if (!selectedSession) {
    return `<p class="empty-state">No visible sessions for transcript QA.</p>`;
  }

  const childCase = cases.find(c => c.case_id === selectedSession.case_id);
  const transcriptLines = state.transcriptLines[selectedSession.session_id] || [];
  const transcriptRecord = state.transcripts[selectedSession.session_id];
  const features = state.extractedFeatureOutputs[selectedSession.session_id];
  const aiOutput = state.aiDecisionOutputs[selectedSession.session_id];
  const evidenceItems = buildEvidenceItems(transcriptLines, aiOutput);
  const transcriptIsReviewed = transcriptRecord?.review_status === "reviewed";
  const featureStatus = features?.extraction_status || "not_started";
  const aiStatus = aiOutput?.therapist_review_status || "not_started";

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
      <div class="panel" style="padding: 12px; margin-bottom: 16px; background: var(--panel-soft);">
        <strong>Transcript review safety gate</strong>
        <p style="font-size: 0.85rem; color: var(--muted); margin-top: 6px;">
          ASR-generated transcripts may contain errors, especially for children's speech, noisy audio, overlapping speech, or multilingual speech.
          Features are labeled preliminary until the transcript is reviewed, and edited transcripts require feature extraction to be re-run.
        </p>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px;">
          <span class="status-pill ${transcriptIsReviewed ? "status-good" : "status-warn"}">Transcript: ${transcriptRecord.review_status}</span>
          <span class="status-pill ${featureStatus === "completed" ? "status-good" : "status-warn"}">Features: ${featureStatus}</span>
          <span class="status-pill ${aiStatus === "awaiting_review" ? "status-good" : "status-warn"}">AI support: ${aiStatus}</span>
        </div>
      </div>
      
      <div style="display: grid; grid-template-columns: 1.3fr 0.7fr; gap: 20px;">
        <section class="panel" style="padding: 16px;">
          <div class="panel-title">
            <h3>CHAT transcript viewer and correction UI</h3>
            <span>Session: ${selectedSession.session_id}</span>
          </div>
          
          <table style="width: 100%; border-collapse: collapse;">
            <thead>
              <tr style="border-bottom: 2px solid var(--line); text-align: left;">
                <th style="padding: 8px;">Line</th>
                <th style="padding: 8px;">Speaker</th>
                <th style="padding: 8px;">Utterance Text</th>
                <th style="padding: 8px;">Timing</th>
                <th style="padding: 8px;">Flags for clinician review</th>
                <th style="padding: 8px;">Review</th>
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
            <button class="primary-action" id="rerun-feature-extraction-btn" data-session-id="${selectedSession.session_id}">
              Re-run feature extraction
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
                Please check and correct flagged transcript lines before interpreting screening support.
              </p>
            </div>
            <div style="display: grid; gap: 10px; max-height: 520px; overflow: auto;">
              ${
                evidenceItems.length
                  ? evidenceItems
                      .map(
                        (item, index) => `
                <div style="border: 1px solid var(--line); border-radius: 6px; padding: 10px; background: var(--shell);">
                  <div style="display: flex; justify-content: space-between; gap: 8px; align-items: center;">
                    <strong>${item.line_number ? `<a href="#line-${item.line_number}">Line ${item.line_number}</a>` : "Feature summary"}</strong>
                    <span class="status-pill status-warn">${escapeHtml(item.marker_type)}</span>
                  </div>
                  <div style="font-size: 0.82rem; color: var(--muted); margin-top: 6px;">
                    ${escapeHtml(item.speaker)}${item.utterance_text ? `: ${escapeHtml(item.utterance_text)}` : ""}
                  </div>
                  <p style="font-size: 0.82rem; margin-top: 6px;">${escapeHtml(item.explanation)}</p>
                  <label style="display: flex; gap: 6px; align-items: center; font-size: 0.8rem;">
                    <input type="checkbox" class="evidence-reviewed-checkbox" data-evidence-index="${index}" data-line-index="${item.line_index ?? ""}" data-flag-index="${item.flag_index ?? ""}" ${item.reviewed ? "checked" : ""} />
                    Therapist reviewed
                  </label>
                  <label style="display: block; margin-top: 6px; font-size: 0.8rem;">Therapist interpretation
                    <input type="text" class="evidence-interpretation-input" data-evidence-index="${index}" data-line-index="${item.line_index ?? ""}" data-flag-index="${item.flag_index ?? ""}" value="${escapeHtml(item.interpretation_note || "")}" style="width: 100%; border: 1px solid var(--line); border-radius: 4px; padding: 6px; margin-top: 4px;" />
                  </label>
                </div>
              `
                      )
                      .join("")
                  : '<p style="color: var(--muted);">No feature or transcript markers need extra evidence review yet.</p>'
              }
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

      const {
        transcriptRecord,
        transcriptLines,
        featuresSet,
        aiOutput,
        sessionUpdates
      } = buildTranscriptWorkflowArtifacts({
        session,
        childCase,
        transcriptText: rawText,
        filename: "generated_mock.cha",
        transcriptCount: Object.keys(state.transcripts).length
      });

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
        ...sessionUpdates
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
        const reviewed = row.querySelector(".line-reviewed-checkbox");
        const note = row.querySelector(".interpretation-note-input");
        if (select && input) {
          updateUtterance(sessId, idx, input.value, select.value, {
            reviewed: Boolean(reviewed?.checked),
            interpretation_note: note?.value || ""
          });
        }
      });

      alert("Transcript corrections saved. Extracted features are marked stale until you re-run feature extraction.");
      navigate("transcript");
    });
  }

  const rerunFeaturesBtn = document.getElementById("rerun-feature-extraction-btn");
  if (rerunFeaturesBtn) {
    rerunFeaturesBtn.addEventListener("click", () => {
      const sessId = rerunFeaturesBtn.getAttribute("data-session-id");
      const state = store.getState();
      const session = state.sessions.find(s => s.session_id === sessId);
      const childCase = state.cases.find(c => c.case_id === session?.case_id);
      const transcriptRecord = state.transcripts[sessId];
      const lines = state.transcriptLines[sessId] || [];
      const reviewed = transcriptRecord?.review_status === "reviewed";
      const { featuresSet, aiOutput } = buildFeatureAndAiOutputs({
        session,
        childCase,
        transcriptLines: lines,
        reviewed
      });

      store.setState({
        extractedFeatureOutputs: { ...state.extractedFeatureOutputs, [sessId]: featuresSet },
        aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: aiOutput }
      });

      updateSessionStatus(sessId, {
        feature_extraction_status: featuresSet.extraction_status,
        ai_analysis_status: aiOutput.therapist_review_status
      });

      addAudit("rerun_feature_extraction", "Session", sessId, "Re-ran feature extraction after transcript review/correction.");
      alert(reviewed ? "Feature extraction re-run complete." : "Feature extraction re-run complete and remains preliminary until transcript review is signed off.");
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
      saveEvidenceReviewEdits(sessId);

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

    const state = store.getState();
    const sessId = state.selectedSessionId;
    const session = state.sessions.find(s => s.session_id === sessId);
    const childCase = state.cases.find(c => c.case_id === session.case_id);
    const artifacts = buildTranscriptWorkflowArtifacts({
      session,
      childCase,
      transcriptText: text,
      filename: file.name,
      transcriptCount: Object.keys(state.transcripts).length
    });

    if (artifacts.validation.quality === "fail") {
      alert("CHAT Upload Error:\n" + artifacts.validation.warnings.map(w => `- ${w.message}`).join("\n"));
      return;
    }

    store.setState({
      transcripts: { ...state.transcripts, [sessId]: artifacts.transcriptRecord },
      transcriptLines: { ...state.transcriptLines, [sessId]: artifacts.transcriptLines },
      extractedFeatureOutputs: { ...state.extractedFeatureOutputs, [sessId]: artifacts.featuresSet },
      aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: artifacts.aiOutput }
    });

    updateSessionStatus(sessId, artifacts.sessionUpdates);

    addAudit("handleTranscriptUpload", "Transcript", artifacts.transcriptRecord.transcript_id, `Uploaded CHA transcript file: ${file.name}`);
    navigate("transcript");
  };
  reader.readAsText(file);
}

function saveEvidenceReviewEdits(sessionId) {
  const state = store.getState();
  const lines = (state.transcriptLines[sessionId] || []).map(line => ({
    ...line,
    clinical_flags: [...(line.clinical_flags || [])]
  }));

  document.querySelectorAll(".evidence-reviewed-checkbox").forEach(checkbox => {
    const lineIndex = checkbox.getAttribute("data-line-index");
    const flagIndex = checkbox.getAttribute("data-flag-index");
    if (lineIndex === "" || flagIndex === "") return;
    const flag = lines[Number(lineIndex)]?.clinical_flags?.[Number(flagIndex)];
    if (flag) flag.reviewed = checkbox.checked;
  });

  document.querySelectorAll(".evidence-interpretation-input").forEach(input => {
    const lineIndex = input.getAttribute("data-line-index");
    const flagIndex = input.getAttribute("data-flag-index");
    if (lineIndex === "" || flagIndex === "") return;
    const flag = lines[Number(lineIndex)]?.clinical_flags?.[Number(flagIndex)];
    if (flag) flag.interpretation_note = input.value;
  });

  store.setState({
    transcriptLines: {
      ...state.transcriptLines,
      [sessionId]: lines
    }
  });
}

function downloadFile(content, filename, contentType) {
  const a = document.createElement("a");
  const file = new Blob([content], { type: contentType });
  a.href = URL.createObjectURL(file);
  a.download = filename;
  a.click();
}
