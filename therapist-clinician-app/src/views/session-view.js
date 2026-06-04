import { store } from "../store/state.js";
import { getVisibleCases } from "../services/case-service.js";
import { getVisibleSessions, createNewSession, updateSessionStatus } from "../services/session-service.js";
import { renderTranscriptReview, bindTranscriptReview } from "./transcript-view.js";
import {
  getAudioFileUrl,
  getFileStorageLabel,
  hasSecureAudioConsent,
  registerAudioFileBlob,
  uploadSecureAudioFile,
  uploadSessionAudio
} from "../services/audio-service.js";
import { startTranscription } from "../services/transcription-service.js";
import { formatFileSize } from "@shared/utils/format.js";
import { FILE_STORAGE_MODE, PROCESSING_MODE } from "../constants.js";
import { renderAccessDenied } from "../components/access-denied.js";
import { buildTranscriptWorkflowArtifacts } from "../services/transcript-workflow-service.js";
import { addAudit } from "../services/audit-service.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { renderConsentWarning, renderPrivacyStatusTags } from "../components/privacy-status.js";
import { iconSvg } from "../components/icons.js";

// Persistent recording variables
let activeMediaRecorder = null;
let recordedAudioChunks = [];
let recordingSecondsElapsed = 0;
let recordingTimerId = null;

function renderSessionStepper(session, audioFile, transcript) {
  if (!session) return "";
  
  let currentStep = 1; // 1: Audio Link, 2: Transcribe, 3: QA Review, 4: Ready
  
  if (audioFile) {
    currentStep = 2;
    if (transcript) {
      currentStep = 3;
      if (transcript.qa_status === "completed" || session.processing_status === "completed") {
        currentStep = 4;
      }
    }
  }
  
  const steps = [
    { num: 1, label: "Audio Upload" },
    { num: 2, label: "Transcribe" },
    { num: 3, label: "Clinical QA" },
    { num: 4, label: "Ready" }
  ];
  
  return `
    <div class="session-stepper">
      ${steps.map((step, idx) => {
        let statusClass = "pending";
        if (step.num < currentStep) {
          statusClass = "completed";
        } else if (step.num === currentStep) {
          statusClass = "active";
        }
        
        const connector = idx < steps.length - 1 ? '<div class="step-connector"></div>' : '';
        return `
          <div class="step-item ${statusClass}">
            <div class="step-badge">
              ${statusClass === "completed" ? `
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              ` : step.num}
            </div>
            <span class="step-label">${step.label}</span>
          </div>
          ${connector}
        `;
      }).join('')}
    </div>
  `;
}

export function renderSessionView() {
  const state = store.getState();
  const casesList = getVisibleCases();
  const sessionsList = getVisibleSessions();

  const selectedVisibleSession = sessionsList.find(s => s.session_id === state.selectedSessionId);
  const selectedSessionExists = state.sessions.some(s => s.session_id === state.selectedSessionId);
  if (!selectedVisibleSession && selectedSessionExists) {
    return renderAccessDenied("Access denied: this session is not assigned to your account.");
  }
  const selectedSession = selectedVisibleSession || sessionsList[0];
  const activeStorageLabel = getFileStorageLabel(FILE_STORAGE_MODE);

  // Helper to get case details
  const getCaseLabel = caseId => {
    const c = casesList.find(item => item.case_id === caseId);
    return c ? `${c.display_label} (${c.anonymized_child_code})` : caseId;
  };

  let sessionDetailsHtml = "";
  if (selectedSession) {
    const audioFile = state.audioFiles.find(a => a.session_id === selectedSession.session_id);
    const sessionCase = casesList.find(c => c.case_id === selectedSession.case_id) || state.cases.find(c => c.case_id === selectedSession.case_id);
    const audioPreviewUrl = audioFile ? getAudioFileUrl(audioFile.audio_file_id) : null;
    const previewElement = audioPreviewUrl
      ? ["mp4", "mov"].includes(audioFile.file_type)
        ? `<video controls src="${audioPreviewUrl}" style="width: 100%; max-height: 220px; border-radius: var(--radius-sm); border: 1px solid var(--line); margin-top: 8px;"></video>`
        : `<audio controls src="${audioPreviewUrl}" style="width: 100%; margin-top: 8px;"></audio>`
      : "";
    const transcript = state.transcripts[selectedSession.session_id];
    const secureStorageMode =
      FILE_STORAGE_MODE === "secure_backend" ||
      FILE_STORAGE_MODE === "supabase_storage" ||
      FILE_STORAGE_MODE === "backend_placeholder";
    const secureConsentGranted = hasSecureAudioConsent(sessionCase);
    const secureUploadGate = secureStorageMode && !secureConsentGranted
      ? `
        <div class="secure-gate status-bad-soft" role="alert" style="padding: 12px; border-radius: var(--radius-sm); margin-bottom: 10px;">
          <strong style="display: block; margin-bottom: 4px;">Secure audio upload locked</strong>
          <span style="font-size: 0.8rem; opacity: 0.9;">Guardian consent must be granted before storing or processing audio/video files.</span>
        </div>
      `
      : `
        <div class="secure-gate status-good-soft" style="padding: 12px; border-radius: var(--radius-sm); margin-bottom: 10px;">
          <strong style="display: block; margin-bottom: 4px;">Secure storage policy</strong>
          <span style="font-size: 0.8rem; opacity: 0.9;">Audio/video access uses private storage, signed URLs, encryption status, retention policy, and audit logs.</span>
        </div>
      `;

    sessionDetailsHtml = `
      <section class="glass-card session-details-panel" style="padding: 20px; display: flex; flex-direction: column; gap: 16px;">
        ${renderSessionStepper(selectedSession, audioFile, transcript)}
        
        <div class="panel-title" style="margin-bottom: 0;">
          <h3>Session Details: ${selectedSession.session_id}</h3>
          <span>${getCaseLabel(selectedSession.case_id)}</span>
        </div>
        <div style="display: grid; gap: 12px; font-size: 0.9rem;">
          <div style="background: var(--surface-raised); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 12px; display: grid; gap: 8px;">
            <p style="margin: 0 0 4px 0; font-weight: 700; color: var(--primary); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">Session metadata</p>
            <div><strong>Case ID:</strong> ${selectedSession.case_id}</div>
            <div style="display: flex; gap: 6px; flex-wrap: wrap;">${renderPrivacyStatusTags(sessionCase)}</div>
            ${renderConsentWarning(sessionCase)}
            <div><strong>Date:</strong> ${selectedSession.session_date}</div>
            <div><strong>Type:</strong> ${selectedSession.session_type.replaceAll("_", " ")}</div>
            <div><strong>Status:</strong> <span class="status-pill status-good">${selectedSession.processing_status.replaceAll("_", " ")}</span></div>
            <div><strong>Notes:</strong> ${selectedSession.notes || "None"}</div>
          </div>
          
          <div style="background: var(--surface-raised); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 12px; display: grid; gap: 8px;">
            <p style="margin: 0 0 4px 0; font-weight: 700; color: var(--primary); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">Audio File Metadata</p>
            ${secureUploadGate}
            ${
              audioFile
                ? `
              <div><strong>Filename:</strong> ${audioFile.original_filename}</div>
              <div><strong>Size:</strong> ${formatFileSize(audioFile.file_size)}</div>
              <div><strong>Duration:</strong> ${audioFile.duration_seconds}s</div>
              <div><strong>Stored Name:</strong> ${audioFile.stored_filename}</div>
              <div><strong>Storage Mode:</strong> ${audioFile.storage_mode || "metadata_only"}</div>
              ${previewElement}
              <div style="font-size: 0.8rem; color: var(--muted); margin-top: 4px;">${getFileStorageLabel(audioFile.storage_mode || FILE_STORAGE_MODE)}</div>
            `
                : `
              <div style="padding: 16px; border: 1px dashed var(--line); border-radius: var(--radius-sm); text-align: center; display: grid; gap: 12px; background: var(--surface);">
                <p style="margin: 0; font-weight: 500;">No audio file linked to this session.</p>
                <p style="font-size: 0.8rem; color: var(--muted); margin: 0;">${activeStorageLabel}</p>
                <input type="file" id="audio-file-input" accept=".wav,.mp3,.m4a,.mp4,.mov" style="display: none;" />
                <div style="display: flex; gap: 10px; justify-content: center; align-items: center; flex-wrap: wrap;">
                  <button class="secondary-action" id="trigger-upload-btn" data-session-id="${selectedSession.session_id}" data-case-id="${selectedSession.case_id}">
                    ${secureStorageMode ? "Request secure audio upload" : "Upload audio metadata"}
                  </button>
                  <button class="primary-action" id="in-app-record-btn" data-session-id="${selectedSession.session_id}" data-case-id="${selectedSession.case_id}" style="display: flex; align-items: center; gap: 6px; background: var(--destructive);">
                    <span id="record-dot" style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: white;"></span>
                    <b id="record-text">Record in app</b>
                  </button>
                </div>
                <div id="recording-timer" style="display: none; font-weight: 700; color: var(--destructive); font-size: 1.1rem; margin-top: 4px;">
                  <span class="recording-state-icon">${iconSvg.record}</span> Recording: <span id="record-time-val">00:00</span>
                </div>
                <div class="audio-visualizer-container" id="visualizer-wrapper" style="display: none; justify-content: center; align-items: center; gap: 4px; height: 40px; margin-top: 8px;">
                  <svg height="30" width="120" style="display: flex; align-items: center;">
                    <rect class="bar" x="5" y="5" width="4" height="20" rx="2" fill="var(--primary)" />
                    <rect class="bar" x="17" y="5" width="4" height="20" rx="2" fill="var(--primary)" />
                    <rect class="bar" x="29" y="5" width="4" height="20" rx="2" fill="var(--primary)" />
                    <rect class="bar" x="41" y="5" width="4" height="20" rx="2" fill="var(--primary)" />
                    <rect class="bar" x="53" y="5" width="4" height="20" rx="2" fill="var(--primary)" />
                    <rect class="bar" x="65" y="5" width="4" height="20" rx="2" fill="var(--primary)" />
                    <rect class="bar" x="77" y="5" width="4" height="20" rx="2" fill="var(--primary)" />
                    <rect class="bar" x="89" y="5" width="4" height="20" rx="2" fill="var(--primary)" />
                    <rect class="bar" x="101" y="5" width="4" height="20" rx="2" fill="var(--primary)" />
                    <rect class="bar" x="113" y="5" width="4" height="20" rx="2" fill="var(--primary)" />
                  </svg>
                </div>
              </div>
            `
            }
          </div>
          
          ${
            audioFile && !transcript
              ? `
            <div style="padding: 16px; text-align: center; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--surface);">
              <p style="margin: 0 0 8px 0; font-weight: 500;">Audio is uploaded. Ready to run transcription.</p>
              <p style="font-size: 0.8rem; color: var(--muted); margin: 0 0 12px 0;">Audio processing mode: ${PROCESSING_MODE}</p>
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
            <div style="padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--surface); display: flex; flex-direction: column; gap: 10px;">
              <p style="margin: 0; font-weight: 500;"><strong>Transcript QA Results:</strong> <span class="status-pill status-good">${transcript.qa_status}</span> (Score: ${transcript.qa_score})</p>
              <button class="primary-action" id="view-transcript-btn" data-session-id="${selectedSession.session_id}">
                Open Transcript Review Workspace
              </button>
            </div>
          `
              : ""
          }
 
          <div style="padding: 16px; border: 1px dashed var(--line); border-radius: var(--radius-sm); text-align: center; background: var(--surface);">
            <p style="margin: 0 0 6px 0; font-weight: 500;">CHAT transcript</p>
            <p style="font-size: 0.8rem; color: var(--muted); margin: 0 0 12px 0;">
              Upload or select a .cha transcript for therapist review. Extracted features remain preliminary until review is complete.
            </p>
            <input type="file" id="session-cha-file-input" accept=".cha" style="display: none;" />
            <button class="secondary-action" id="session-upload-cha-btn" data-session-id="${selectedSession.session_id}">
              Upload/select .cha transcript
            </button>
          </div>
          
          <div style="font-size: 0.75rem; color: var(--muted); padding: 10px; background: rgba(239, 68, 68, 0.03); border: 1px solid var(--line-dark); border-radius: var(--radius-sm); margin-top: 4px; line-height: 1.4;">
            <strong>Mock audio upload & transcription pipeline:</strong> Real audio pipeline is not run in the browser. ${activeStorageLabel} Audio processing mode is ${PROCESSING_MODE}.
          </div>
        </div>
      </section>
    `;
  } else {
    sessionDetailsHtml = `
      <section class="glass-card empty-details-panel" style="padding: 20px; display: flex; align-items: center; justify-content: center; min-height: 200px;">
        <p class="empty-state">Select a session to view details.</p>
      </section>
    `;
  }

  return `
    ${renderSafetyBanner()}
    <div style="display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 20px;">
      <div style="display: grid; gap: 16px;">
        <section class="glass-card add-session-panel" style="padding: 20px;">
          <div class="panel-title">
            <h3>Add Session</h3>
            <span>record child interaction</span>
          </div>
          <form id="create-session-form" class="form-grid" style="display: grid; gap: 16px; grid-template-columns: 1fr;">
            <label>Child Case
              <select id="session-case-id" class="glass-input" required style="margin-top: 6px;">
                ${casesList.map(c => `<option value="${c.case_id}">${c.display_label} (${c.anonymized_child_code})</option>`).join("")}
              </select>
            </label>
            <label>Session Date
              <input type="date" class="glass-input" id="session-date" required value="${new Date().toISOString().split("T")[0]}" style="margin-top: 6px;" />
            </label>
            <label>Session Type
              <select id="session-type" class="glass-input" style="margin-top: 6px;">
                <option value="free_play">Free Play</option>
                <option value="structured_assessment">Structured Assessment</option>
                <option value="therapy_session">Therapy Session</option>
              </select>
            </label>
            <label>Session Notes / Context
              <textarea id="session-notes" class="glass-input" placeholder="Notes on play context, speaker count..." style="margin-top: 6px; min-height: 80px;"></textarea>
            </label>
            <button class="primary-action" type="submit" style="margin-top: 8px;">Add session</button>
          </form>
        </section>

        ${sessionDetailsHtml}
      </div>

      <section class="glass-card recent-sessions-panel" style="padding: 20px;">
        <div class="panel-title">
          <h3>Recent Sessions</h3>
          <span>total sessions: ${sessionsList.length}</span>
        </div>
        <div class="session-timeline">
          ${sessionsList
            .map(
              s => {
                const isActive = s.session_id === state.selectedSessionId;
                return `
            <div class="session-timeline-item session-item-row ${isActive ? "active" : ""}" data-session-id="${s.session_id}">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <div class="timeline-item-header">
                  <strong>${s.session_id}</strong>
                  <span class="timeline-item-date">${s.session_date}</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--muted); margin-top: 4px;">
                  ${getCaseLabel(s.case_id)}
                </div>
                <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px;">
                  ${renderPrivacyStatusTags(casesList.find(item => item.case_id === s.case_id) || state.cases.find(item => item.case_id === s.case_id))}
                </div>
                <div style="margin-top: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem;">
                  <span class="status-pill ${s.processing_status === "failed" ? "status-bad" : "status-good"}">
                    ${s.processing_status}
                  </span>
                  <span style="font-size: 0.75rem; color: var(--muted); text-transform: capitalize;">${s.session_type.replaceAll("_", " ")}</span>
                </div>
              </div>
            </div>
          `;
              }
            )
            .join("")}
        </div>
      </section>
    </div>
  `;
}

export function bindSessionView(navigate) {
  const state = store.getState();
  const sessionsList = getVisibleSessions();
  const selectedSession = sessionsList.find(s => s.session_id === state.selectedSessionId) || sessionsList[0];
  // Session creation
  const form = document.getElementById("create-session-form");
  if (form) {
    form.addEventListener("submit", async e => {
      e.preventDefault();
      const caseId = document.getElementById("session-case-id").value;
      const date = document.getElementById("session-date").value;
      const type = document.getElementById("session-type").value;
      const notes = document.getElementById("session-notes").value;

      try {
        const newSess = await createNewSession({
          case_id: caseId,
          session_date: date,
          session_type: type,
          notes
        });

        store.setState({ selectedSessionId: newSess.session_id });
        navigate("session");
      } catch (err) {
        alert("Failed to create session: " + err.message);
      }
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
          if (FILE_STORAGE_MODE === "secure_backend" || FILE_STORAGE_MODE === "supabase_storage") {
            triggerBtn.disabled = true;
            triggerBtn.textContent = "Uploading securely...";
            uploadSecureAudioFile(file, sessId, caseId)
              .then(result => {
                if (result.intent.status === "not_configured") {
                  alert(result.intent.message);
                  return;
                }
                navigate("session");
              })
              .catch(err => alert(err.message))
              .finally(() => {
                triggerBtn.disabled = false;
                triggerBtn.textContent = "Request secure audio upload";
              });
            return;
          }
          uploadSessionAudio(file, sessId, caseId);
          navigate("session");
        } catch (err) {
          alert(err.message);
        }
      }
    });
  }

  // In-app Recording click
  const recordBtn = document.getElementById("in-app-record-btn");
  const recordDot = document.getElementById("record-dot");
  const recordText = document.getElementById("record-text");
  const timerDiv = document.getElementById("recording-timer");
  const timeVal = document.getElementById("record-time-val");

  if (recordBtn) {
    recordBtn.addEventListener("click", async () => {
      const sessId = recordBtn.getAttribute("data-session-id");
      const caseId = recordBtn.getAttribute("data-case-id");

      if (activeMediaRecorder && activeMediaRecorder.state === "recording") {
        // Stop recording
        activeMediaRecorder.stop();
        clearInterval(recordingTimerId);
        timerDiv.style.display = "none";
        const viz = document.getElementById("visualizer-wrapper");
        if (viz) viz.style.display = "none";
        recordDot.style.background = "white";
        recordDot.style.animation = "none";
        recordText.innerText = "Record in app";
        return;
      }

      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recordedAudioChunks = [];
        activeMediaRecorder = new MediaRecorder(stream);
        
        activeMediaRecorder.ondataavailable = event => {
          recordedAudioChunks.push(event.data);
        };

        activeMediaRecorder.onstop = () => {
          const audioBlob = new Blob(recordedAudioChunks, { type: "audio/wav" });
          const audioUrl = URL.createObjectURL(audioBlob);
          
          // Save in store
          const state = store.getState();
          const updatedAudioUrls = { ...state.audioUrls, [sessId]: audioUrl };
          
          // Create audio file metadata
          const audioFileId = `AUDIO-${String(state.audioFiles.length + 1).padStart(3, "0")}`;
          const recordedFile = new File([audioBlob], `in-app-recording-${sessId}.wav`, { type: "audio/wav" });
          const newAudioFile = {
            audio_file_id: audioFileId,
            original_filename: `in-app-recording-${sessId}.wav`,
            stored_filename: `${caseId}_${sessId}_${audioFileId}.wav`,
            file_type: "wav",
            file_size: audioBlob.size,
            duration_seconds: recordingSecondsElapsed,
            upload_time: new Date().toISOString(),
            owner_user_id: state.currentUser?.user_id || "user_therapist_001",
            case_id: caseId,
            session_id: sessId,
            processing_status: "completed",
            storage_mode: "browser_preview"
          };
          registerAudioFileBlob(audioFileId, recordedFile);

          const updatedAudioFiles = [...state.audioFiles, newAudioFile];
          
          // Update session metadata to link this audio
          const updatedSessions = state.sessions.map(s => {
            if (s.session_id === sessId) {
              return {
                ...s,
                audio_file_id: audioFileId,
                processing_status: "completed"
              };
            }
            return s;
          });

          store.setState({
            audioUrls: updatedAudioUrls,
            audioFiles: updatedAudioFiles,
            sessions: updatedSessions
          });

          addAudit("in_app_recording_complete", "Session", sessId, `Completed in-app audio recording for session ${sessId}. Size: ${audioBlob.size} bytes`);
          
          // Clean up stream tracks
          stream.getTracks().forEach(track => track.stop());
          
          navigate("session");
        };

        activeMediaRecorder.start();
        recordingSecondsElapsed = 0;
        timerDiv.style.display = "block";
        const viz = document.getElementById("visualizer-wrapper");
        if (viz) viz.style.display = "flex";
        timeVal.innerText = "00:00";
        recordDot.style.background = "red";
        recordDot.style.animation = "pulse 1s infinite";
        recordText.innerText = "Stop Recording";

        recordingTimerId = setInterval(() => {
          recordingSecondsElapsed++;
          const mins = String(Math.floor(recordingSecondsElapsed / 60)).padStart(2, "0");
          const secs = String(recordingSecondsElapsed % 60).padStart(2, "0");
          timeVal.innerText = `${mins}:${secs}`;
        }, 1000);

      } catch (err) {
        alert("Failed to access microphone: " + err.message);
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

  const chaUploadBtn = document.getElementById("session-upload-cha-btn");
  const chaFileInput = document.getElementById("session-cha-file-input");
  if (chaUploadBtn && chaFileInput) {
    chaUploadBtn.addEventListener("click", () => chaFileInput.click());
    chaFileInput.addEventListener("change", e => {
      const file = e.target.files[0];
      if (!file) return;

      const sessId = chaUploadBtn.getAttribute("data-session-id");
      const state = store.getState();
      const session = state.sessions.find(s => s.session_id === sessId);
      const childCase = state.cases.find(c => c.case_id === session?.case_id);
      const reader = new FileReader();
      reader.onload = event => {
        const artifacts = buildTranscriptWorkflowArtifacts({
          session,
          childCase,
          transcriptText: event.target.result,
          filename: file.name,
          transcriptCount: Object.keys(state.transcripts).length
        });

        if (artifacts.validation.quality === "fail") {
          alert("CHAT Upload Error:\n" + artifacts.validation.warnings.map(w => `- ${w.message}`).join("\n"));
          return;
        }

        store.setState({
          selectedSessionId: sessId,
          transcripts: { ...state.transcripts, [sessId]: artifacts.transcriptRecord },
          transcriptLines: { ...state.transcriptLines, [sessId]: artifacts.transcriptLines },
          extractedFeatureOutputs: { ...state.extractedFeatureOutputs, [sessId]: artifacts.featuresSet },
          aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: artifacts.aiOutput }
        });

        updateSessionStatus(sessId, artifacts.sessionUpdates);
        addAudit("upload_chat_transcript", "Transcript", artifacts.transcriptRecord.transcript_id, `Uploaded CHA transcript file from session detail: ${file.name}`);
        navigate("transcript");
      };
      reader.readAsText(file);
    });
  }
}
