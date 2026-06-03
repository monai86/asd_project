import { store } from "../store/state.js";
import { getVisibleSessions } from "../services/session-service.js";
import { getVisibleCases } from "../services/case-service.js";
import { updateUtterance, saveTherapistReview } from "../services/review-service.js";
import { getAudioFileUrl } from "../services/audio-service.js";
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
import {
  evaluateReferenceComparisonReadiness,
  loadReferenceComparisonForSession,
  referenceReasonLabel,
  REFERENCE_COMPARISON_STATUS,
  topReferenceFeatures
} from "../services/reference-comparison-service.js";
import { loadReferenceSimilarity } from "../services/reference-similarity-service.js";
import {
  buildLocalTranscriptQaResult,
  loadTranscriptQaForSession,
  shouldLoadBackendTranscriptQa,
  TRANSCRIPT_QA_LOAD_STATUS
} from "../services/transcript-qa-service.js";

function withoutReferenceComparison(referenceComparisons = {}, sessionId) {
  const next = { ...referenceComparisons };
  delete next[sessionId];
  return next;
}

function withoutTranscriptQa(transcriptQaResults = {}, sessionId) {
  const next = { ...transcriptQaResults };
  delete next[sessionId];
  return next;
}

export function renderTranscriptQaPanel({ session, transcript, transcriptLines, qaState }) {
  if (!transcript) return "";
  const qa = qaState || buildLocalTranscriptQaResult(transcript, transcriptLines);
  const quality = qa.quality || "needs_review";
  const badgeClass = quality === "pass" ? "status-good" : quality === "needs_review" ? "status-warn" : "status-bad";
  const sourceLabel = qa.source === "api" ? "backend CHAT/CLAN readiness" : "lightweight local QA";
  const issues = qa.issues || [];
  const readiness = qa.readiness || {};
  const readinessItems = [
    ["Feature extraction", readiness.feature_extraction_ready],
    ["Reference comparison", readiness.reference_comparison_ready],
    ["CLAN metrics", readiness.clan_metric_ready]
  ];

  if (qa.load_status === TRANSCRIPT_QA_LOAD_STATUS.LOADING) {
    return `
      <div class="glass-card qa-panel-glass" style="padding: 12px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <h4 style="margin: 0; font-size: 0.9rem; font-family: sans-serif;">Transcript QA Results</h4>
          <span class="status-pill status-warn" style="font-size: 0.75rem; padding: 2px 8px;">QA: loading</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--muted);">Loading backend Transcript QA...</div>
      </div>
    `;
  }

  return `
    <div class="glass-card qa-panel-glass" style="padding: 12px; margin-bottom: 16px;">
      <div style="display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-bottom: 6px;">
        <h4 style="margin: 0; font-size: 0.9rem; font-family: sans-serif;">Transcript QA Results</h4>
        <span class="status-pill ${badgeClass}" style="font-size: 0.75rem; padding: 2px 8px;">QA: ${escapeHtml(quality)}${qa.score === null || qa.score === undefined ? "" : ` (Score: ${escapeHtml(String(qa.score))})`}</span>
      </div>
      <div style="font-size: 0.76rem; color: var(--muted); margin-bottom: 8px;">Source: ${escapeHtml(sourceLabel)}</div>
      ${
        qa.load_status === TRANSCRIPT_QA_LOAD_STATUS.ERROR
          ? `<div style="font-size: 0.8rem; color: var(--rose); font-weight: 700; margin-bottom: 8px;">${escapeHtml(qa.error_detail || "Backend Transcript QA request failed.")}</div>`
          : ""
      }
      <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px;">
        ${readinessItems.map(([label, ready]) => `
          <span class="status-pill ${ready ? "status-good" : "status-warn"}" style="font-size: 0.68rem; padding: 1px 6px;">
            ${escapeHtml(label)}: ${ready ? "ready" : "limited"}
          </span>
        `).join("")}
      </div>
      <div style="font-size: 0.8rem; display: grid; gap: 6px;">
        ${
          issues.length
            ? issues
                .map(
                  issue => `
          <div style="color: ${issue.severity === "error" ? "var(--rose)" : "var(--amber)"}; font-weight: 700;">
            [${escapeHtml(issue.code || "QA_WARNING")}] ${escapeHtml(issue.message || "Review transcript before interpretation.")}
          </div>
        `
                )
                .join("") + `
          <button type="button" class="primary-action" id="ai-autofix-chat-btn" data-session-id="${escapeHtml(session.session_id)}" style="margin-top: 6px; background: var(--violet); width: fit-content; padding: 4px 10px; font-size: 0.8rem; border-radius: 4px;">
            AI Auto-Fix CHAT Format
          </button>
        `
            : '<div style="color: var(--green); font-weight: 700;">No transcript validation issues found.</div>'
        }
      </div>
    </div>
  `;
}

function formatReferenceValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isFinite(numeric)) return numeric.toFixed(Math.abs(numeric) >= 10 ? 1 : 2);
  return String(value);
}

function renderReasonList(reasons = [], warnings = []) {
  const items = [...reasons, ...warnings];
  if (!items.length) return "";
  return `
    <ul style="margin: 8px 0 0 18px; padding: 0; color: var(--muted); font-size: 0.78rem; line-height: 1.4;">
      ${items.map(reason => `<li>${escapeHtml(referenceReasonLabel(reason))}</li>`).join("")}
    </ul>
  `;
}

function renderReferenceFeatureRows(payload, aiOutput) {
  const cohorts = payload?.cohorts || [];
  if (!cohorts.length) {
    return `<p class="empty-state" style="font-size: 0.78rem;">No matched Reference Cohort rows were returned.</p>`;
  }

  return cohorts
    .map(cohort => {
      const featureRows = topReferenceFeatures({ cohorts: [cohort] }, aiOutput);
      return `
        <div style="border: 1px solid var(--line); border-radius: 6px; padding: 10px; background: var(--shell);">
          <div style="display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-bottom: 8px;">
            <strong style="font-size: 0.82rem;">${escapeHtml(cohort.group)} cohort</strong>
            <span class="status-pill ${cohort.confidence_flag === "ok" ? "status-good" : "status-warn"}" style="font-size: 0.68rem; padding: 1px 6px;">
              ${cohort.confidence_flag === "low_n" ? "Caution: low-count context" : escapeHtml(cohort.confidence_flag)} · n=${escapeHtml(String(cohort.cohort_n))}
            </span>
          </div>
          <div style="display: grid; gap: 6px;">
            ${featureRows
              .map(row => `
                <div style="display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: start; font-size: 0.76rem; border-top: 1px solid var(--line); padding-top: 6px;">
                  <div>
                    <strong>${escapeHtml(row.feature)}</strong>
                    <div style="color: var(--muted);">
                      value ${formatReferenceValue(row.value)} · median ${formatReferenceValue(row.median)} · IQR ${formatReferenceValue(row.q1)}-${formatReferenceValue(row.q3)}
                    </div>
                  </div>
                  <span class="status-pill ${row.position === "within_iqr" ? "status-good" : row.position === "missing" ? "status-warn" : "status-warn"}" style="font-size: 0.66rem; padding: 1px 6px;">
                    ${escapeHtml(row.position)}${row.percentile === null || row.percentile === undefined ? "" : ` · p${formatReferenceValue(row.percentile)}`}
                  </span>
                </div>
              `)
              .join("")}
          </div>
          ${
            (cohort.clan_metric_comparisons || []).length
              ? `<p style="font-size: 0.74rem; color: var(--muted); margin: 8px 0 0;">CLAN-derived metrics available: ${cohort.clan_metric_comparisons.length}</p>`
              : ""
          }
        </div>
      `;
    })
    .join("");
}

export function renderReferenceComparisonPanel({
  session,
  transcript,
  features,
  qaResult,
  aiOutput,
  currentUser,
  comparisonState
}) {
  const readiness = evaluateReferenceComparisonReadiness({ transcript, features, qaResult });
  const state = readiness.ready ? comparisonState : { ...readiness, payload: null };
  const status = state?.status || (readiness.ready ? "idle" : REFERENCE_COMPARISON_STATUS.BLOCKED);
  const badgeClass =
    status === REFERENCE_COMPARISON_STATUS.READY && state?.payload
      ? "status-good"
      : status === REFERENCE_COMPARISON_STATUS.ERROR || status === REFERENCE_COMPARISON_STATUS.BLOCKED
        ? "status-bad"
        : "status-warn";
  const payload = state?.payload;
  const canLoad = readiness.ready && status !== REFERENCE_COMPARISON_STATUS.LOADING && !payload;
  const warnings = state?.warnings || readiness.warnings || [];
  const reasons = state?.reasons || [];

  let bodyHtml = "";
  if (!readiness.ready || status === REFERENCE_COMPARISON_STATUS.BLOCKED) {
    bodyHtml = `
      <p style="font-size: 0.8rem; color: var(--muted); margin: 6px 0 0;">
        Reference Comparison is held until transcript review, QA, and feature extraction are ready.
      </p>
      ${renderReasonList(readiness.reasons, readiness.warnings)}
    `;
  } else if (status === REFERENCE_COMPARISON_STATUS.UNAVAILABLE) {
    bodyHtml = `
      <p style="font-size: 0.8rem; color: var(--muted); margin: 6px 0 0;">
        Backend Reference Comparison is not configured in this runtime. Mock mode does not generate percentiles or reference distributions.
      </p>
      ${renderReasonList(reasons, warnings)}
    `;
  } else if (status === REFERENCE_COMPARISON_STATUS.ERROR) {
    bodyHtml = `
      <p style="font-size: 0.8rem; color: var(--rose); margin: 6px 0 0;">
        ${escapeHtml(state?.error_detail || "Reference Comparison request failed.")}
      </p>
    `;
  } else if (status === REFERENCE_COMPARISON_STATUS.LOADING) {
    bodyHtml = `<p style="font-size: 0.8rem; color: var(--muted); margin: 6px 0 0;">Loading matched Reference Cohorts...</p>`;
  } else if (payload) {
    let similarityHtml = "";
    if (comparisonState?.similarityPayload?.results?.length) {
      similarityHtml = `
        <div style="margin-top: 12px; border-top: 1px dashed var(--line); padding-top: 12px;">
          <strong style="font-size: 0.82rem; color: var(--ink);">Similar Reference Cases (Descriptive)</strong>
          <div style="display: grid; gap: 8px; margin-top: 8px;">
            ${comparisonState.similarityPayload.results.map(res => `
              <div class="similar-case-card" style="padding: 8px; border: 1px solid var(--line); border-radius: 4px; background: var(--shell); font-size: 0.74rem;">
                <div style="display: flex; justify-content: space-between; font-weight: bold; margin-bottom: 4px;">
                  <span>${escapeHtml(res.corpus)} (${escapeHtml(res.group)})</span>
                  <span style="color: var(--violet);">dist: ${res.distance}</span>
                </div>
                <div style="color: var(--muted);">MLU: ${res.features.mlu !== undefined ? res.features.mlu : "-"} · TTR: ${res.features.ttr !== undefined ? res.features.ttr : "-"}</div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    bodyHtml = `
      <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px;">
        <span class="status-pill status-good" style="font-size: 0.68rem; padding: 1px 6px;">${escapeHtml(payload.status)}</span>
        <span class="status-pill status-good" style="font-size: 0.68rem; padding: 1px 6px;">age ${escapeHtml(payload.age_band_12mo || "-")}</span>
        <span class="status-pill status-good" style="font-size: 0.68rem; padding: 1px 6px;">${escapeHtml(payload.task_type || "-")}</span>
        <span class="status-pill status-good" style="font-size: 0.68rem; padding: 1px 6px;">${escapeHtml(payload.language || "eng")}</span>
      </div>
      ${renderReasonList([], [...warnings, ...(payload.warnings || [])])}
      <div style="display: grid; gap: 10px; margin-top: 10px;">
        ${renderReferenceFeatureRows(payload, aiOutput)}
      </div>
      ${similarityHtml}
    `;
  } else {
    bodyHtml = `
      <p style="font-size: 0.8rem; color: var(--muted); margin: 6px 0 0;">
        Transcript and features are ready. Load the backend Reference Comparison to inspect matched descriptive cohorts.
      </p>
      ${renderReasonList([], warnings)}
    `;
  }

  return `
    <div class="glass-card reference-comparison-panel" id="reference-comparison-panel" data-session-id="${escapeHtml(session?.session_id || "")}" data-can-load="${canLoad ? "true" : "false"}" style="padding: 12px; margin-bottom: 16px;">
      <div style="display: flex; justify-content: space-between; gap: 12px; align-items: center;">
        <strong>Reference Comparison readiness</strong>
        <span class="status-pill ${badgeClass}" style="font-size: 0.75rem; padding: 2px 8px;">Reference: ${escapeHtml(status)}</span>
      </div>
      <p style="font-size: 0.78rem; color: var(--muted); margin: 6px 0 0;">
        Descriptive context only. It must stay separate from screening support scores and clinical conclusions.
      </p>
      ${bodyHtml}
      ${
        canLoad
          ? `<button class="secondary-action" id="load-reference-comparison-btn" data-session-id="${escapeHtml(session.session_id)}" style="margin-top: 10px; padding: 6px 10px; font-size: 0.78rem;">Load Reference Comparison</button>`
          : ""
      }
      ${currentUser ? "" : `<p style="font-size: 0.74rem; color: var(--muted); margin: 8px 0 0;">Sign in is required before loading backend comparison.</p>`}
    </div>
  `;
}

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
  const qaState = state.transcriptQaResults?.[selectedSession.session_id];
  const qaRequiredBeforeReference = shouldLoadBackendTranscriptQa({
    transcript: transcriptRecord,
    currentUser: state.currentUser,
    qaState
  });
  const referenceQaState = qaState || (qaRequiredBeforeReference
    ? {
        load_status: TRANSCRIPT_QA_LOAD_STATUS.ERROR,
        source: "api_required",
        quality: "needs_review",
        score: null,
        issues: [],
        readiness: {
          feature_extraction_ready: true,
          reference_comparison_ready: false,
          clan_metric_ready: false
        }
      }
    : null);
  const comparisonState = state.referenceComparisons?.[selectedSession.session_id];
  const referenceComparisonHtml = renderReferenceComparisonPanel({
    session: selectedSession,
    transcript: transcriptRecord,
    features,
    qaResult: referenceQaState,
    aiOutput,
    currentUser: state.currentUser,
    comparisonState
  });

  // Left sidebar files mapping
  const filesList = [
    { name: "dylan", session_id: "SESSION-001", hasPlus: true },
    { name: "erwin", session_id: "SESSION-001-A", hasPlus: true },
    { name: "job", session_id: "SESSION-001-B", hasPlus: false },
    { name: "marcel", session_id: "SESSION-002", hasPlus: true },
    { name: "max", session_id: "SESSION-003", hasPlus: false },
    { name: "pim", session_id: "SESSION-003", hasPlus: true }
  ];

  // QA Check Status block
  let qaStatusHtml = "";
  if (transcriptRecord) {
    qaStatusHtml = renderTranscriptQaPanel({
      session: selectedSession,
      transcript: transcriptRecord,
      transcriptLines,
      qaState
    });
  }

  const selectSessionHtml = `
    <div style="display: none;">
      <select id="qa-session-select">
        ${sessions
          .map(
            s => `
          <option value="${s.session_id}" ${s.session_id === selectedSession.session_id ? "selected" : ""}>
            Session ${s.session_id}
          </option>
        `
          )
          .join("")}
      </select>
    </div>
  `;

  let middleContentHtml = "";
  if (transcriptRecord) {
    const audioFile = state.audioFiles.find(a => a.session_id === selectedSession.session_id);
    const audioUrl = audioFile ? getAudioFileUrl(audioFile.audio_file_id) : null;
    
    const audioPlayerHtml = audioUrl ? `
      <div style="background: var(--violet-soft); border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 0.85rem; font-weight: bold; color: var(--violet-strong);">Session Audio:</span>
        <audio id="transcript-audio-player" src="${audioUrl}" controls style="flex: 1; height: 28px;"></audio>
      </div>
    ` : `
      <div style="background: var(--panel-soft); border: 1px dashed var(--line); border-radius: 8px; padding: 10px; margin-bottom: 16px; font-size: 0.8rem; color: var(--muted); text-align: center;">
        No recorded audio linked to this session. Timeline play buttons are disabled.
      </div>
    `;

    const headerLines = transcriptRecord.transcript_text
      .split("\n")
      .map(line => line.trim())
      .filter(line => line.startsWith("@") && line.toUpperCase() !== "@END")
      .join("\n");

    middleContentHtml = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 2px solid var(--line-dark); padding-bottom: 6px;">
        <h3 style="margin: 0; font-family: sans-serif; font-size: 1.15rem; font-weight: bold; color: var(--ink);">Transcript:</h3>
        <button type="button" class="primary-action" style="padding: 4px 10px; font-size: 0.8rem; min-height: auto;">Collab</button>
      </div>

      <!-- Metadata Table -->
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px; font-family: sans-serif; font-size: 0.72rem; border: 1px solid var(--line-dark); text-align: left;">
        <thead>
          <tr style="background: var(--neutral-glass); border-bottom: 1px solid var(--line-dark);">
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">CHAT</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">path</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">filename</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">languages</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">media</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">date</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">pid</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">design type</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">activity type</th>
            <th style="padding: 4px 6px; font-weight: bold;">group type</th>
          </tr>
        </thead>
        <tbody>
          <tr style="border-bottom: 1px solid var(--line-dark); background: transparent;">
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark);"><a href="#" style="text-decoration: underline; color: var(--primary); font-weight: bold;">${selectedSession.session_id.toLowerCase()}</a></td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">childes/Clinical-Other/BolPool/${selectedSession.session_id.toLowerCase()}</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">${selectedSession.session_id.toLowerCase()}.cha</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">eng</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">${selectedSession.audio_file_id ? 'audio' : '-'}</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">${selectedSession.session_date}</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted); font-family: monospace;">11312/c-00003347-1</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">cross</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">toyplay</td>
            <td style="padding: 5px 6px; color: var(--muted);">ASD</td>
          </tr>
        </tbody>
      </table>

      <!-- Participants Section -->
      <div style="font-weight: bold; margin-bottom: 6px; font-family: sans-serif; font-size: 0.9rem; color: var(--ink);">Participants:</div>
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px; font-family: sans-serif; font-size: 0.72rem; border: 1px solid var(--line-dark); text-align: left;">
        <thead>
          <tr style="background: var(--neutral-glass); border-bottom: 1px solid var(--line-dark);">
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">participant</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">role</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">name</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">language</th>
            <th style="padding: 4px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">age</th>
            <th style="padding: 4px 6px; font-weight: bold;">sex</th>
          </tr>
        </thead>
        <tbody>
          <tr style="border-bottom: 1px solid var(--line-dark); background: transparent;">
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">CHI</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">Target_Child</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">${childCase ? childCase.anonymized_child_code : 'CHI'}</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">eng</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">${childCase ? Math.floor(childCase.age_months / 12) + ';' + String(childCase.age_months % 12).padStart(2, '0') + '.00' : '4;08.00'}</td>
            <td style="padding: 5px 6px; color: var(--muted);">${childCase && childCase.sex ? childCase.sex : '-'}</td>
          </tr>
          <tr style="background: transparent;">
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); font-weight: bold;">MOT</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">Mother</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">Mother</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">eng</td>
            <td style="padding: 5px 6px; border-right: 1px solid var(--line-dark); color: var(--muted);">-</td>
            <td style="padding: 5px 6px; color: var(--muted);">female</td>
          </tr>
        </tbody>
      </table>

      <!-- View Dependent Tiers -->
      <div style="margin-bottom: 16px; font-family: sans-serif; font-size: 0.8rem; display: flex; align-items: center; gap: 8px;">
        <span style="border: 1px solid var(--line-dark); padding: 3px 8px; border-radius: var(--radius-sm); background: var(--neutral-glass); display: inline-flex; align-items: center; gap: 6px; user-select: none;">
          View dependent tiers: <input type="checkbox" id="view-dependent-tiers-checkbox" style="cursor: pointer;" checked />
        </span>
      </div>

      <!-- Audio player if any -->
      ${audioPlayerHtml}

      <!-- Crimson Monospace CHAT Header Block -->
      <pre style="color: var(--primary); font-family: monospace; font-size: 0.82rem; margin: 0 0 16px 0; background: transparent; border: none; padding: 0; line-height: 1.45; white-space: pre-wrap;">${escapeHtml(headerLines)}</pre>

      <!-- Dialogue Rows -->
      <div class="transcript-container transcript-view-scrollbar">
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
          <tbody>
            ${transcriptLines
              .map((line, idx) => renderUtteranceRow(line, idx, selectedSession.session_id))
              .join("")}
          </tbody>
        </table>
      </div>

      <!-- @End marker -->
      <div style="color: var(--primary); font-family: monospace; font-size: 0.82rem; margin-bottom: 24px; padding-left: 8px;">@End</div>

      <!-- Action Buttons -->
      <div style="margin-top: auto; display: flex; gap: 10px; flex-wrap: wrap; border-top: 1px solid var(--line); padding-top: 16px;">
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
    `;
  } else {
    middleContentHtml = `
      <div style="padding: 36px 24px; text-align: center; border: 1px dashed var(--line); border-radius: var(--radius); background: var(--shell); margin-top: 20px; flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center;">
        <h3 style="font-family: sans-serif; font-size: 1.1rem; font-weight: bold; color: var(--ink);">CHAT transcript workflow</h3>
        <p style="font-size: 0.9rem; color: var(--muted); margin-bottom: 8px;">No transcript exists for this session yet.</p>
        <p style="font-size: 0.85rem; color: var(--muted); margin-bottom: 20px; max-width: 450px; line-height: 1.4;">
          To test transcription, please upload a .cha transcript, paste raw conversation text, or click below to generate a mock transcript from case metadata.
        </p>
        
        <div style="display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%; max-width: 320px;">
          <button class="primary-action" id="generate-mock-transcript-btn" data-session-id="${selectedSession.session_id}" style="width: 100%; text-align: center;">
            Generate mock CHAT from audio metadata
          </button>
          <input type="file" id="transcript-upload-input" accept=".cha" style="display: none;" />
          <button class="secondary-action" id="upload-cha-btn" style="width: 100%; text-align: center;">
            Upload/select .cha transcript
          </button>
          <button class="secondary-action" id="paste-raw-dialogue-btn" data-session-id="${selectedSession.session_id}" style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 6px;">
            ✍ Paste Raw Text & Convert
          </button>
        </div>
        <p style="font-size: 0.78rem; color: var(--muted); margin-top: 16px; font-style: italic;">
          * Note: Real audio-to-CHAT execution is deferred. No file bytes are persisted.
        </p>
      </div>
    `;
  }

  return `
    ${renderSafetyBanner()}
    ${selectSessionHtml}
    
    <!-- Pipeline Status & General Safety Gate -->
    <div style="margin-bottom: 16px;">
      ${renderPipelineStatus(selectedSession.processing_status)}
      ${qaStatusHtml}
      <div class="glass-card safety-gate-panel" style="padding: 12px; margin-bottom: 16px;">
        <strong>Transcript review safety gate</strong>
        <p style="font-size: 0.82rem; color: var(--muted); margin-top: 6px; margin-bottom: 8px;">
          ASR-generated transcripts may contain errors, especially for children's speech, noisy audio, overlapping speech, or multilingual speech.
          Features are labeled preliminary until the transcript is reviewed, and edited transcripts require feature extraction to be re-run.
        </p>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px;">
          <span class="status-pill ${transcriptIsReviewed ? "status-good" : "status-warn"}" style="font-size: 0.75rem; padding: 2px 8px;">Transcript: ${transcriptRecord ? transcriptRecord.review_status : 'not_started'}</span>
          <span class="status-pill ${featureStatus === "completed" ? "status-good" : "status-warn"}" style="font-size: 0.75rem; padding: 2px 8px;">Features: ${featureStatus}</span>
          <span class="status-pill ${aiStatus === "awaiting_review" ? "status-good" : "status-warn"}" style="font-size: 0.75rem; padding: 2px 8px;">AI support: ${aiStatus}</span>
        </div>
      </div>
      ${referenceComparisonHtml}
    </div>

    <!-- TalkBank Three Column Grid -->
    <div style="display: grid; grid-template-columns: 240px 1.4fr 0.8fr; gap: 20px; align-items: start; margin-bottom: 30px;">
      <!-- Column 1: Left Sub-sidebar (TalkBank directory browser) -->
      <aside class="glass-card talkbank-sidebar" style="padding: 12px; min-height: 600px; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <!-- Header dropdown -->
          <div style="margin-bottom: 12px; font-weight: bold; border-bottom: 1px solid var(--line-dark); padding-bottom: 8px; display: flex; align-items: center; gap: 6px; font-family: sans-serif; font-size: 0.9rem;">
            <span>TalkBank:</span>
            <select id="talkbank-db-select" style="font-weight: bold; background: transparent; border: none; font-size: 0.9rem; cursor: pointer; color: var(--ink); padding: 2px; outline: none;">
              <option value="childes" selected>CHILDES</option>
              <option value="clinician">Clinician App</option>
            </select>
          </div>
          
          <!-- Folder Path -->
          <div style="font-size: 0.78rem; color: var(--muted); margin-bottom: 16px; font-family: monospace; word-break: break-all; line-height: 1.3;">
            childes / Clinical-Other / BolPool /
          </div>
          
          <!-- Files List -->
          <ul style="list-style: none; padding-left: 6px; margin: 0; display: flex; flex-direction: column; gap: 8px; font-family: monospace; font-size: 0.85rem;">
            ${filesList.map(file => {
              const isActive = selectedSession.session_id === file.session_id;
              return `
                <li style="display: flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: var(--radius-sm); background: ${isActive ? 'rgba(225, 29, 72, 0.06)' : 'transparent'};">
                  <span style="color: var(--muted);">•</span>
                  <span style="font-size: 0.9rem; color: ${isActive ? 'var(--primary)' : 'var(--muted)'};">📄</span>
                  <a class="talkbank-file-link ${isActive ? 'active-file' : ''}" 
                     data-session-id="${file.session_id}" 
                     style="cursor: pointer; text-decoration: none; color: ${isActive ? 'var(--primary)' : 'var(--muted)'}; font-weight: ${isActive ? 'bold' : 'normal'}; transition: color 0.15s ease;">
                    ${file.name}
                  </a>
                  ${file.hasPlus ? '<span style="color: var(--muted); font-size: 0.75rem; margin-left: 2px;">[+]</span>' : ''}
                </li>
              `;
            }).join("")}
          </ul>
        </div>
        
        <!-- Folder Footer -->
        <div style="margin-top: auto; border-top: 1px solid var(--line-dark); padding-top: 12px; font-size: 0.75rem; font-family: monospace; color: var(--muted); display: flex; flex-direction: column; gap: 6px;">
          <div><strong>Folder:</strong> childes/Clinical-Other/BolPool/</div>
          <div style="display: flex; gap: 4px; align-items: center;">
            <select style="font-size: 0.7rem; padding: 2px; border: 1px solid var(--line-dark); border-radius: 2px; background: var(--neutral-glass); color: var(--ink);">
              <option>chains</option>
            </select>
            <input type="text" style="width: 100%; font-size: 0.7rem; padding: 2px; border: 1px solid var(--line-dark); border-radius: 2px; background: var(--neutral-glass); color: var(--ink);" placeholder="filter..." />
          </div>
          <div style="display: flex; gap: 6px; margin-top: 4px;">
            <button type="button" class="secondary-action" style="padding: 2px 8px; font-size: 0.7rem; cursor: pointer; font-weight: bold; width: 50%; min-height: 28px;">Clear</button>
            <button type="button" class="primary-action" style="padding: 2px 8px; font-size: 0.7rem; cursor: pointer; font-weight: bold; width: 50%; min-height: 28px;">Run</button>
          </div>
        </div>
      </aside>

      <!-- Column 2: Center main section (TalkBank Transcript display) -->
      <main class="glass-card transcript-editor-panel" style="padding: 20px; min-height: 600px; display: flex; flex-direction: column; justify-content: flex-start;">
        ${middleContentHtml}
      </main>

      <!-- Column 3: Right section (Evidence Review & Therapist Notes) -->
      <aside class="glass-card evidence-notes-panel" style="padding: 16px;">
        <div class="panel-title" style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line-dark); padding-bottom: 6px;">
          <h3 style="margin: 0; font-size: 0.95rem; font-weight: bold; color: var(--ink);">Evidence Review & Notes</h3>
          <span style="font-size: 0.75rem; color: var(--muted); font-style: italic;">requires signature</span>
        </div>
        <div style="display: grid; gap: 12px;">
          <label style="display: flex; flex-direction: column; gap: 4px; font-size: 0.85rem; font-weight: bold; color: var(--ink);">
            Clinical Notes
            <textarea id="review-notes" style="min-height: 120px; font-weight: normal; font-size: 0.85rem; padding: 8px; border: 1px solid var(--line-dark); border-radius: 4px;" placeholder="Add therapist observations...">${selectedSession.notes || ""}</textarea>
          </label>
          
          <div style="padding: 10px; background: rgba(225, 29, 72, 0.06); border-radius: var(--radius); border: 1px solid rgba(225, 29, 72, 0.15);">
            <strong style="font-size: 0.85rem; color: var(--primary-hover);">Evidence Review Panel</strong>
            <p style="font-size: 0.78rem; margin-top: 4px; color: var(--primary-hover); margin-bottom: 0;">
              Please check and correct flagged transcript lines before interpreting screening support.
            </p>
          </div>
          
          <div class="transcript-view-scrollbar" style="display: grid; gap: 10px; max-height: 520px; overflow-y: auto; padding-right: 4px;">
            ${
              evidenceItems.length
                ? evidenceItems
                    .map(
                      (item, index) => `
              <div style="border: 1px solid var(--line-dark); border-radius: 6px; padding: 10px; background: var(--neutral-glass); display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; justify-content: space-between; gap: 8px; align-items: center;">
                  <strong style="font-size: 0.8rem; color: var(--ink);">${item.line_number ? `<a href="#line-${item.line_number}" style="color: var(--primary); text-decoration: underline;">Line ${item.line_number}</a>` : "Feature summary"}</strong>
                  <span class="status-pill status-warn" style="font-size: 0.65rem; padding: 1px 6px;">${escapeHtml(item.marker_type.replace('_marker', '').replace('_', ' '))}</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--muted); font-family: monospace;">
                  ${escapeHtml(item.speaker)}${item.utterance_text ? `: ${escapeHtml(item.utterance_text)}` : ""}
                </div>
                <p style="font-size: 0.8rem; margin: 0; color: var(--ink); line-height: 1.3;">${escapeHtml(item.explanation)}</p>
                <label style="display: flex; gap: 6px; align-items: center; font-size: 0.78rem; cursor: pointer; user-select: none;">
                  <input type="checkbox" class="evidence-reviewed-checkbox" data-evidence-index="${index}" data-line-index="${item.line_index ?? ""}" data-flag-index="${item.flag_index ?? ""}" ${item.reviewed ? "checked" : ""} style="cursor: pointer;" />
                  Therapist reviewed
                </label>
                <label style="display: block; font-size: 0.78rem; color: var(--ink);">Therapist interpretation
                  <input type="text" class="evidence-interpretation-input" data-evidence-index="${index}" data-line-index="${item.line_index ?? ""}" data-flag-index="${item.flag_index ?? ""}" value="${escapeHtml(item.interpretation_note || "")}" style="width: 100%; border: 1px solid var(--line-dark); border-radius: 4px; padding: 4px 6px; margin-top: 4px; font-size: 0.78rem;" />
                </label>
              </div>
            `
                    )
                    .join("")
                : '<p style="color: var(--muted); font-size: 0.8rem;">No feature or transcript markers need extra evidence review yet.</p>'
            }
          </div>
          <button class="primary-action" id="submit-clinical-review-btn" data-session-id="${selectedSession.session_id}" style="width: 100%; padding: 8px 16px;">
            Sign off Review
          </button>
        </div>
      </aside>

    </div>

    <!-- Paste Dialogue Modal -->
    <div id="paste-dialogue-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 9999; place-items: center;">
      <div class="glass-card" style="width: min(600px, 90%); padding: 24px; display: grid; gap: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <h3>Paste Raw Text & Convert to CHAT</h3>
          <button type="button" id="close-paste-modal-btn" style="border: 0; background: transparent; font-size: 1.5rem; cursor: pointer;">&times;</button>
        </div>
        <p style="font-size: 0.85rem; color: var(--muted); margin: 0;">
          Paste unstructured dialogue. AI will map speaker labels to CHI/MOT/INV and output correct CHAT syntax with default timestamps.
        </p>
        <textarea id="raw-dialogue-text" style="min-height: 180px; font-family: monospace; font-size: 0.9rem; padding: 10px; width: 100%; border: 1px solid var(--line); border-radius: var(--radius);" placeholder="หมอ: สวัสดีครับน้องเอ็ม&#10;แม่: ทักทายคุณหมอเร็วลูก&#10;เด็ก: หวัดดีฮะ"></textarea>
        
        <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px;">
          <button type="button" class="secondary-action" id="cancel-paste-btn">Cancel</button>
          <button type="button" class="primary-action" id="submit-paste-convert-btn" data-session-id="${selectedSession.session_id}">Convert</button>
        </div>
      </div>
    </div>
  `;
}

export function bindTranscriptReview(navigate) {
  // TalkBank Left Sidebar File Links
  const fileLinks = document.querySelectorAll(".talkbank-file-link");
  fileLinks.forEach(link => {
    link.addEventListener("click", () => {
      const sessId = link.getAttribute("data-session-id");
      if (sessId) {
        store.setState({ selectedSessionId: sessId });
        navigate("transcript");
      }
    });
  });

  // TalkBank Database Select
  const dbSelect = document.getElementById("talkbank-db-select");
  if (dbSelect) {
    dbSelect.addEventListener("change", e => {
      alert(`Switched TalkBank database view to: ${e.target.value.toUpperCase()}`);
    });
  }

  // AI Auto-Fix click
  const autofixBtn = document.getElementById("ai-autofix-chat-btn");
  if (autofixBtn) {
    autofixBtn.addEventListener("click", () => {
      const sessId = autofixBtn.getAttribute("data-session-id");
      const state = store.getState();
      const transcriptRecord = state.transcripts[sessId];
      if (!transcriptRecord) return;
      
      const fixedText = autoFixChatText(transcriptRecord.transcript_text);
      const session = state.sessions.find(s => s.session_id === sessId);
      const childCase = state.cases.find(c => c.case_id === session.case_id);
      
      const artifacts = buildTranscriptWorkflowArtifacts({
        session,
        childCase,
        transcriptText: fixedText,
        filename: transcriptRecord.original_filename,
        transcriptCount: Object.keys(state.transcripts).length - 1
      });
      
      store.setState({
        transcripts: { ...state.transcripts, [sessId]: artifacts.transcriptRecord },
        transcriptLines: { ...state.transcriptLines, [sessId]: artifacts.transcriptLines },
        extractedFeatureOutputs: { ...state.extractedFeatureOutputs, [sessId]: artifacts.featuresSet },
        aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: artifacts.aiOutput },
        transcriptQaResults: withoutTranscriptQa(state.transcriptQaResults, sessId),
        referenceComparisons: withoutReferenceComparison(state.referenceComparisons, sessId)
      });
      
      updateSessionStatus(sessId, artifacts.sessionUpdates);
      addAudit("ai_autofix_chat", "Transcript", transcriptRecord.transcript_id, "AI auto-fixed CHAT transcript formatting errors.");
      alert("AI Formatting Auto-Fix complete! Warnings have been cleared.");
      navigate("transcript");
    });
  }

  // Paste raw text modal handlers
  const pasteBtn = document.getElementById("paste-raw-dialogue-btn");
  const pasteModal = document.getElementById("paste-dialogue-modal");
  const closeBtn = document.getElementById("close-paste-modal-btn");
  const cancelBtn = document.getElementById("cancel-paste-btn");
  const submitPasteBtn = document.getElementById("submit-paste-convert-btn");
  const rawTextarea = document.getElementById("raw-dialogue-text");

  if (pasteBtn && pasteModal) {
    pasteBtn.addEventListener("click", () => {
      pasteModal.style.display = "grid";
      rawTextarea.value = "";
    });
    
    const closeModal = () => {
      pasteModal.style.display = "none";
    };
    
    closeBtn.addEventListener("click", closeModal);
    cancelBtn.addEventListener("click", closeModal);
    
    submitPasteBtn.addEventListener("click", () => {
      const text = rawTextarea.value.trim();
      if (!text) {
        alert("Please paste some text first.");
        return;
      }
      
      const sessId = submitPasteBtn.getAttribute("data-session-id");
      const state = store.getState();
      const session = state.sessions.find(s => s.session_id === sessId);
      const childCase = state.cases.find(c => c.case_id === session.case_id);
      
      const chatText = convertRawToCHAT(text);
      
      const artifacts = buildTranscriptWorkflowArtifacts({
        session,
        childCase,
        transcriptText: chatText,
        filename: `pasted_transcript_${sessId}.cha`,
        transcriptCount: Object.keys(state.transcripts).length
      });
      
      store.setState({
        transcripts: { ...state.transcripts, [sessId]: artifacts.transcriptRecord },
        transcriptLines: { ...state.transcriptLines, [sessId]: artifacts.transcriptLines },
        extractedFeatureOutputs: { ...state.extractedFeatureOutputs, [sessId]: artifacts.featuresSet },
        aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: artifacts.aiOutput },
        transcriptQaResults: withoutTranscriptQa(state.transcriptQaResults, sessId),
        referenceComparisons: withoutReferenceComparison(state.referenceComparisons, sessId)
      });
      
      updateSessionStatus(sessId, artifacts.sessionUpdates);
      addAudit("paste_raw_transcript", "Transcript", artifacts.transcriptRecord.transcript_id, `Converted pasted raw text to CHA transcript for session ${sessId}`);
      closeModal();
      navigate("transcript");
    });
  }

  // Play segment clicks
  const audioPlayer = document.getElementById("transcript-audio-player");
  const playBtns = document.querySelectorAll(".play-segment-btn");
  if (audioPlayer && playBtns.length) {
    let checkStopListener = null;
    playBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        const start = parseFloat(btn.getAttribute("data-start"));
        const end = parseFloat(btn.getAttribute("data-end"));
        
        audioPlayer.currentTime = start;
        audioPlayer.play();
        
        if (checkStopListener) {
          audioPlayer.removeEventListener("timeupdate", checkStopListener);
        }
        
        checkStopListener = () => {
          if (audioPlayer.currentTime >= end) {
            audioPlayer.pause();
            audioPlayer.removeEventListener("timeupdate", checkStopListener);
            checkStopListener = null;
          }
        };
        audioPlayer.addEventListener("timeupdate", checkStopListener);
      });
    });
  }

  // Session switcher (kept for backwards compatibility/DOM safety)
  const qaSelect = document.getElementById("qa-session-select");
  if (qaSelect) {
    qaSelect.addEventListener("change", e => {
      store.setState({ selectedSessionId: e.target.value });
      navigate("transcript");
    });
  }

  const bindState = store.getState();
  const selectedSessionId = bindState.selectedSessionId || bindState.sessions[0]?.session_id;
  const selectedTranscript = bindState.transcripts[selectedSessionId];
  const selectedQaState = bindState.transcriptQaResults?.[selectedSessionId];
  if (shouldLoadBackendTranscriptQa({
    transcript: selectedTranscript,
    currentUser: bindState.currentUser,
    qaState: selectedQaState
  })) {
    store.setState({
      transcriptQaResults: {
        ...(bindState.transcriptQaResults || {}),
        [selectedSessionId]: {
          load_status: TRANSCRIPT_QA_LOAD_STATUS.LOADING,
          source: "api",
          quality: selectedTranscript.qa_status || "needs_review",
          score: selectedTranscript.qa_score ?? null,
          issues: selectedTranscript.qa_issues || [],
          readiness: null
        }
      }
    }, { persist: false });
    loadTranscriptQaForSession({
      sessionId: selectedSessionId,
      currentUser: bindState.currentUser
    }).then(result => {
      const latest = store.getState();
      store.setState({
        transcriptQaResults: {
          ...(latest.transcriptQaResults || {}),
          [selectedSessionId]: result
        }
      }, { persist: false });
      navigate("transcript");
    });
  }

  const loadReferenceBtn = document.getElementById("load-reference-comparison-btn");
  if (loadReferenceBtn) {
    loadReferenceBtn.addEventListener("click", async () => {
      const sessId = loadReferenceBtn.getAttribute("data-session-id");
      const state = store.getState();
      const transcript = state.transcripts[sessId];
      const features = state.extractedFeatureOutputs[sessId];
      const qaResult = state.transcriptQaResults?.[sessId];

      store.setState({
        referenceComparisons: {
          ...(state.referenceComparisons || {}),
          [sessId]: {
            status: REFERENCE_COMPARISON_STATUS.LOADING,
            ready: true,
            reasons: [],
            warnings: [],
            payload: null,
            source: "ui"
          }
        }
      }, { persist: false });
      navigate("transcript");

      const nextState = store.getState();
      const result = await loadReferenceComparisonForSession({
        sessionId: sessId,
        transcript: nextState.transcripts[sessId] || transcript,
        features: nextState.extractedFeatureOutputs[sessId] || features,
        qaResult: nextState.transcriptQaResults?.[sessId] || qaResult,
        currentUser: nextState.currentUser
      });

      let similarityResult = null;
      if (result && result.status === REFERENCE_COMPARISON_STATUS.READY) {
        similarityResult = await loadReferenceSimilarity({
          sessionId: sessId,
          currentUser: nextState.currentUser
        });
      }

      store.setState({
        referenceComparisons: {
          ...(store.getState().referenceComparisons || {}),
          [sessId]: {
            ...result,
            similarityPayload: similarityResult
          }
        }
      }, { persist: false });
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
        aiDecisionOutputs: updatedAI,
        transcriptQaResults: withoutTranscriptQa(state.transcriptQaResults, sessId),
        referenceComparisons: withoutReferenceComparison(state.referenceComparisons, sessId)
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

      const promises = [];
      rows.forEach(row => {
        const idx = parseInt(row.getAttribute("data-line-index"));
        const select = row.querySelector(".speaker-edit-select");
        const input = row.querySelector(".text-edit-input");
        const reviewed = row.querySelector(".line-reviewed-checkbox");
        const note = row.querySelector(".interpretation-note-input");
        if (select && input) {
          const res = updateUtterance(sessId, idx, input.value, select.value, {
            reviewed: Boolean(reviewed?.checked),
            interpretation_note: note?.value || ""
          });
          if (res instanceof Promise) {
            promises.push(res);
          }
        }
      });

      const finalize = () => {
        const state = store.getState();
        store.setState({
          transcriptQaResults: withoutTranscriptQa(state.transcriptQaResults, sessId),
          referenceComparisons: withoutReferenceComparison(state.referenceComparisons, sessId)
        }, { persist: false });

        alert("Transcript corrections saved. Extracted features are marked stale until you re-run feature extraction.");
        navigate("transcript");
      };

      if (promises.length > 0) {
        saveCorrectionsBtn.disabled = true;
        Promise.all(promises).then(finalize).catch(err => {
          saveCorrectionsBtn.disabled = false;
          console.error("Failed to save transcript corrections:", err);
          alert("Error saving corrections: " + err.message);
        });
      } else {
        finalize();
      }
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
        aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: aiOutput },
        referenceComparisons: withoutReferenceComparison(state.referenceComparisons, sessId)
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

      const res = saveTherapistReview({
        sessionId: sessId,
        notes,
        approvedSummary: "Approved speech sample review."
      });

      if (res instanceof Promise) {
        submitReviewBtn.disabled = true;
        res.then(() => {
          alert("Clinical review submitted successfully.");
          navigate("dashboard");
        }).catch(err => {
          submitReviewBtn.disabled = false;
          console.error("Clinical review submission failed:", err);
          alert("Error submitting review: " + err.message);
        });
      } else {
        alert("Clinical review submitted successfully.");
        navigate("dashboard");
      }
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
      aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: artifacts.aiOutput },
      transcriptQaResults: withoutTranscriptQa(state.transcriptQaResults, sessId),
      referenceComparisons: withoutReferenceComparison(state.referenceComparisons, sessId)
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

function autoFixChatText(text) {
  let lines = text.split("\n").map(l => l.trim()).filter(Boolean);
  
  // Ensure @Begin and @End
  const hasBegin = lines.some(l => l.toLowerCase() === "@begin");
  const hasEnd = lines.some(l => l.toLowerCase() === "@end");
  if (!hasBegin) lines.unshift("@Begin");
  if (!hasEnd) lines.push("@End");
  
  // Ensure Languages and Participants
  if (!lines.some(l => l.startsWith("@Languages:"))) {
    lines.splice(1, 0, "@Languages:\teng");
  }
  if (!lines.some(l => l.startsWith("@Participants:"))) {
    lines.splice(2, 0, "@Participants:\tCHI Child Target_Child, MOT Mother Mother, INV Investigator");
  }
  
  // Ensure ID lines
  if (!lines.some(l => l.startsWith("@ID:") && l.includes("CHI"))) {
    lines.splice(3, 0, "@ID:\teng|Mock|CHI|4;08.00|male|||Target_Child|||");
  }
  if (!lines.some(l => l.startsWith("@ID:") && l.includes("MOT"))) {
    lines.splice(4, 0, "@ID:\teng|Mock|MOT|||||Mother|||");
  }
  
  // Clean up punctuation and tabs
  lines = lines.map(line => {
    if (line.startsWith("*CHI:") || line.startsWith("*MOT:") || line.startsWith("*INV:") || line.startsWith("*FAT:") || line.startsWith("*CLI:") || line.startsWith("*PAR:")) {
      const colIdx = line.indexOf(":");
      const speaker = line.slice(0, colIdx + 1);
      let utterance = line.slice(colIdx + 1).trim();
      
      // Ensure space-punctuation
      if (!utterance.endsWith(".") && !utterance.endsWith("?") && !utterance.endsWith("!")) {
        utterance += " .";
      } else {
        const punc = utterance.slice(-1);
        if (utterance.charAt(utterance.length - 2) !== " ") {
          utterance = utterance.slice(0, -1) + " " + punc;
        }
      }
      return `${speaker}\t${utterance}`;
    }
    return line;
  });
  
  return lines.join("\n");
}

function convertRawToCHAT(rawText) {
  const lines = rawText.split("\n").map(l => l.trim()).filter(Boolean);
  let chatLines = [
    "@Begin",
    "@Languages:\teng",
    "@Participants:\tCHI Child Target_Child, MOT Mother Mother, INV Investigator",
    "@ID:\teng|Mock|CHI|4;08.00|male|||Target_Child|||",
    "@ID:\teng|Mock|MOT|||||Mother|||",
    "@ID:\teng|Mock|INV|||||Investigator|||"
  ];
  
  lines.forEach((line) => {
    const parts = line.split(/[:：]/);
    let speaker = "INV";
    let content = line;
    if (parts.length >= 2) {
      const label = parts[0].trim().toLowerCase();
      content = parts.slice(1).join(":").trim();
      if (label.includes("เด็ก") || label.includes("chi") || label.includes("child") || label === "c") {
        speaker = "CHI";
      } else if (label.includes("แม่") || label.includes("mot") || label.includes("mother") || label === "m") {
        speaker = "MOT";
      } else if (label.includes("หมอ") || label.includes("inv") || label.includes("therapist") || label.includes("cli") || label === "t") {
        speaker = "INV";
      }
    }
    
    // Ensure space-punctuation
    if (!content.endsWith(".") && !content.endsWith("?") && !content.endsWith("!")) {
      content += " .";
    } else {
      const punc = content.slice(-1);
      if (content.charAt(content.length - 2) !== " ") {
        content = content.slice(0, -1) + " " + punc;
      }
    }
    
    chatLines.push(`*${speaker}:\t${content}`);
  });
  
  chatLines.push("@End");
  return chatLines.join("\n");
}
