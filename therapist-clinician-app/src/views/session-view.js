import { store } from "../store/state.js";
import { getVisibleCases } from "../services/case-service.js";
import { getVisibleSessions, createNewSession } from "../services/session-service.js";
import { uploadSessionAudio } from "../services/audio-service.js";
import { startTranscription } from "../services/transcription-service.js";
import { formatFileSize } from "@shared/utils/format.js";

export function renderSessionView() {
  const state = store.getState();
  const casesList = getVisibleCases();
  const sessionsList = getVisibleSessions();

  const selectedSession = sessionsList.find(s => s.session_id === state.selectedSessionId) || sessionsList[0];

  // Helper to get case details
  const getCaseLabel = caseId => {
    const c = casesList.find(item => item.case_id === caseId);
    return c ? `${c.display_label} (${c.anonymized_child_code})` : caseId;
  };

  let sessionDetailsHtml = "";
  if (selectedSession) {
    const audioFile = state.audioFiles.find(a => a.session_id === selectedSession.session_id);
    const transcript = state.transcripts[selectedSession.session_id];

    sessionDetailsHtml = `
      <section class="panel" style="padding: 16px;">
        <div class="panel-title">
          <h3>Session Details: ${selectedSession.session_id}</h3>
          <span>${getCaseLabel(selectedSession.case_id)}</span>
        </div>
        <div style="display: grid; gap: 10px; font-size: 0.9rem;">
          <p><strong>Session metadata</strong></p>
          <div><strong>Date:</strong> ${selectedSession.session_date}</div>
          <div><strong>Type:</strong> ${selectedSession.session_type.replaceAll("_", " ")}</div>
          <div><strong>Status:</strong> <span class="status-pill status-good">${selectedSession.processing_status.replaceAll("_", " ")}</span></div>
          <div><strong>Notes:</strong> ${selectedSession.notes || "None"}</div>
          <hr style="border: 0; border-top: 1px solid var(--line); margin: 10px 0;" />
          
          <p><strong>Audio File Metadata</strong></p>
          ${
            audioFile
              ? `
            <div><strong>Filename:</strong> ${audioFile.original_filename}</div>
            <div><strong>Size:</strong> ${formatFileSize(audioFile.file_size)}</div>
            <div><strong>Duration:</strong> ${audioFile.duration_seconds}s</div>
            <div><strong>Stored Name:</strong> ${audioFile.stored_filename}</div>
            <div style="font-size: 0.8rem; color: var(--muted); margin-top: 4px;">No file bytes are persisted (Metadata-only mock upload).</div>
          `
              : `
            <div style="padding: 12px; border: 1px dashed var(--line); border-radius: var(--radius); text-align: center;">
              <p style="margin-bottom: 8px;">No audio file linked to this session.</p>
              <input type="file" id="audio-file-input" accept=".wav,.mp3,.m4a,.mp4,.mov" style="display: none;" />
              <button class="primary-action" id="trigger-upload-btn" data-session-id="${selectedSession.session_id}" data-case-id="${selectedSession.case_id}">
                Upload audio metadata
              </button>
            </div>
          `
          }
          <hr style="border: 0; border-top: 1px solid var(--line); margin: 10px 0;" />
          
          ${
            audioFile && !transcript
              ? `
            <div style="padding: 12px; text-align: center;">
              <p style="margin-bottom: 8px;">Audio is uploaded. Ready to run transcription.</p>
              <button class="primary-action" id="run-transcription-btn" data-session-id="${selectedSession.session_id}">
                Run transcription pipeline
              </button>
            </div>
          `
              : ""
          }

          ${
            transcript
              ? `
            <div>
              <p><strong>Transcript QA Results:</strong> <span class="status-pill status-good">${transcript.qa_status}</span> (Score: ${transcript.qa_score})</p>
              <button class="secondary-action" id="view-transcript-btn" data-session-id="${selectedSession.session_id}">
                Open transcript QA viewer and correction UI
              </button>
            </div>
          `
              : ""
          }
          
          <div style="font-size: 0.8rem; color: var(--muted); padding: 8px; background: var(--panel-soft); border-radius: 4px; margin-top: 8px;">
            ℹ️ **Mock audio upload & transcription pipeline:** Real audio pipeline is not run. Clicking upload registers the audio filename metadata only. Audio/video player deferred.
          </div>
        </div>
      </section>
    `;
  } else {
    sessionDetailsHtml = `
      <section class="panel" style="padding: 16px; display: flex; align-items: center; justify-content: center;">
        <p class="empty-state">Select a session to view details.</p>
      </section>
    `;
  }

  return `
    <div style="display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 20px;">
      <div style="display: grid; gap: 16px;">
        <section class="panel" style="padding: 16px;">
          <div class="panel-title">
            <h3>Add session</h3>
            <span>record child interaction</span>
          </div>
          <form id="create-session-form" class="form-grid" style="display: grid; gap: 12px; grid-template-columns: 1fr;">
            <label>Child Case
              <select id="session-case-id" required>
                ${casesList.map(c => `<option value="${c.case_id}">${c.display_label} (${c.anonymized_child_code})</option>`).join("")}
              </select>
            </label>
            <label>Session Date
              <input type="date" id="session-date" required value="${new Date().toISOString().split("T")[0]}" />
            </label>
            <label>Session Type
              <select id="session-type">
                <option value="free_play">Free Play</option>
                <option value="structured_assessment">Structured Assessment</option>
                <option value="therapy_session">Therapy Session</option>
              </select>
            </label>
            <label>Session Notes / Context
              <textarea id="session-notes" placeholder="Notes on play context, speaker count..."></textarea>
            </label>
            <button class="primary-action" type="submit">Add session</button>
          </form>
        </section>

        ${sessionDetailsHtml}
      </div>

      <section class="panel" style="padding: 16px;">
        <div class="panel-title">
          <h3>Recent Sessions</h3>
          <span>total sessions: ${sessionsList.length}</span>
        </div>
        <div style="display: grid; gap: 10px;">
          ${sessionsList
            .map(
              s => `
            <div class="session-item-row" data-session-id="${s.session_id}" style="cursor: pointer; padding: 12px; border: 1px solid ${s.session_id === state.selectedSessionId ? "var(--violet)" : "var(--line)"}; border-radius: var(--radius); background: ${s.session_id === state.selectedSessionId ? "var(--violet-soft)" : "var(--shell)"};">
              <strong>${s.session_id}</strong>
              <div style="font-size: 0.8rem; color: var(--muted); margin-top: 4px;">
                ${getCaseLabel(s.case_id)} · ${s.session_date}
              </div>
              <div style="margin-top: 6px; display: flex; justify-content: space-between; align-items: center;">
                <span class="status-pill ${s.processing_status === "failed" ? "status-bad" : "status-good"}">
                  ${s.processing_status}
                </span>
                <span style="font-size: 0.8rem; color: var(--muted);">${s.session_type.replaceAll("_", " ")}</span>
              </div>
            </div>
          `
            )
            .join("")}
        </div>
      </section>
    </div>
  `;
}

export function bindSessionView(navigate) {
  // Session creation
  const form = document.getElementById("create-session-form");
  if (form) {
    form.addEventListener("submit", e => {
      e.preventDefault();
      const caseId = document.getElementById("session-case-id").value;
      const date = document.getElementById("session-date").value;
      const type = document.getElementById("session-type").value;
      const notes = document.getElementById("session-notes").value;

      const newSess = createNewSession({
        case_id: caseId,
        session_date: date,
        session_type: type,
        notes
      });

      store.setState({ selectedSessionId: newSess.session_id });
      navigate("session");
    });
  }

  // Session selection click handler
  const items = document.querySelectorAll(".session-item-row");
  items.forEach(item => {
    item.addEventListener("click", () => {
      const sessId = item.getAttribute("data-session-id");
      store.setState({ selectedSessionId: sessId });
      navigate("session");
    });
  });

  // Audio Upload click
  const triggerBtn = document.getElementById("trigger-upload-btn");
  const fileInput = document.getElementById("audio-file-input");
  if (triggerBtn && fileInput) {
    triggerBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", e => {
      const file = e.target.files[0];
      if (file) {
        const sessId = triggerBtn.getAttribute("data-session-id");
        const caseId = triggerBtn.getAttribute("data-case-id");
        try {
          uploadSessionAudio(file, sessId, caseId);
          navigate("session");
        } catch (err) {
          alert(err.message);
        }
      }
    });
  }

  // Run Transcription
  const runBtn = document.getElementById("run-transcription-btn");
  if (runBtn) {
    runBtn.addEventListener("click", async () => {
      const sessId = runBtn.getAttribute("data-session-id");
      runBtn.innerText = "Transcribing...";
      runBtn.disabled = true;
      try {
        await startTranscription(sessId);
        navigate("session");
      } catch (err) {
        alert("Transcription failed: " + err.message);
        navigate("session");
      }
    });
  }

  // View transcript QA
  const viewTransBtn = document.getElementById("view-transcript-btn");
  if (viewTransBtn) {
    viewTransBtn.addEventListener("click", () => {
      const sessId = viewTransBtn.getAttribute("data-session-id");
      store.setState({ selectedSessionId: sessId });
      navigate("transcript");
    });
  }
}
