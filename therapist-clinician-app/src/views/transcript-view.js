import { store } from "../store/state.js";
import { getVisibleSessions } from "../services/session-service.js";
import { getVisibleCases } from "../services/case-service.js";
import { updateUtterance, saveTherapistReview } from "../services/review-service.js";
import { api } from "../services/api-client.js";
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
          ? `<div style="font-size: 0.8rem; color: var(--destructive); font-weight: 700; margin-bottom: 8px;">${escapeHtml(qa.error_detail || "Backend Transcript QA request failed.")}</div>`
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
          <div style="color: ${issue.severity === "error" ? "var(--destructive)" : "var(--amber)"}; font-weight: 700;">
            [${escapeHtml(issue.code || "QA_WARNING")}] ${escapeHtml(issue.message || "Review transcript before interpretation.")}
          </div>
        `
                )
                .join("") + `
          <button type="button" class="primary-action" id="ai-autofix-chat-btn" data-session-id="${escapeHtml(session.session_id)}" style="margin-top: 6px; background: var(--primary); width: fit-content; padding: 4px 10px; font-size: 0.8rem; border-radius: 4px;">
            AI Auto-Fix CHAT Format
          </button>
        `
            : '<div style="color: var(--success); font-weight: 700;">No transcript validation issues found.</div>'
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
      <p style="font-size: 0.8rem; color: var(--destructive); margin: 6px 0 0;">
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
                  <span style="color: var(--primary);">dist: ${res.distance}</span>
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

  const caseOptions = cases.map(c => 
    `<option value="${escapeHtml(c.case_id)}" ${c.case_id === selectedSession.case_id ? "selected" : ""}>${escapeHtml(c.display_label)} (${escapeHtml(c.anonymized_child_code)})</option>`
  ).join("");

  const caseSessions = sessions.filter(s => s.case_id === selectedSession.case_id);
  const sessionOptions = caseSessions.map(s => 
    `<option value="${escapeHtml(s.session_id)}" ${s.session_id === selectedSession.session_id ? "selected" : ""}>Session ${escapeHtml(s.session_id.replace("SESSION-", ""))} — ${escapeHtml(s.session_date)}</option>`
  ).join("");
  const transcriptLines = state.transcriptLines[selectedSession.session_id] || [];
  const transcriptRecord = state.transcripts[selectedSession.session_id];
  const features = state.extractedFeatureOutputs[selectedSession.session_id];
  const aiOutput = state.aiDecisionOutputs[selectedSession.session_id];
  
  let screeningScoreWidgetHtml = "";
  if (aiOutput) {
    const inferenceStatus = aiOutput.inference_status || (aiOutput.therapist_review_status === "reviewed" ? "reviewed" : "preliminary");
    const statusLabel = inferenceStatus === "reviewed" ? "Reviewed" : "Preliminary";
    const statusBg = inferenceStatus === "reviewed" ? "var(--mint-soft)" : "var(--amber-soft)";
    const statusColor = inferenceStatus === "reviewed" ? "var(--mint)" : "var(--amber-pending)";
    const diff = aiOutput.reference_cohort_probabilities || aiOutput.differential_probabilities || { ASD: 0.65, DD: 0.22, TD: 0.13 };
    const mostSimilar = aiOutput.most_similar_reference_cohort || Object.entries(diff).sort((a, b) => b[1] - a[1])[0]?.[0] || "reference cohort";
    const similarityProbability = aiOutput.similarity_probability ?? diff[mostSimilar] ?? aiOutput.screening_support_score ?? 0;
    const pAsd = Math.round((diff.ASD ?? 0) * 100);
    const pDd = Math.round((diff.DD ?? 0) * 100);
    const pTd = Math.round((diff.TD ?? 0) * 100);
    const warnings = aiOutput.safety_warnings || [];
    const isUnavailable = aiOutput.status === "unavailable" || warnings.some(warning =>
      String(warning.code || "").includes("UNAVAILABLE")
    );

    if (isUnavailable) {
      screeningScoreWidgetHtml = `
      <div class="glass-card" style="padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-lg); background: #fff; display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h4 style="margin: 0; font-size: 0.95rem; color: var(--ink); font-weight: 600;">Reference Cohort Similarity</h4>
          <span class="status-pill status-warn" style="font-weight: 700; font-size: 0.72rem;">Unavailable</span>
        </div>
        <p style="margin: 0; font-size: 0.82rem; line-height: 1.45; color: var(--ink); background: var(--amber-soft); border: 1px solid var(--warning); border-radius: var(--radius-sm); padding: 8px 10px;">
          ${escapeHtml(aiOutput.plain_language_explanation || "Reference cohort similarity is unavailable for this transcript. Transcript review and feature summary can continue.")}
        </p>
        ${warnings.length ? `
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${warnings.slice(0, 3).map(warning => `
              <div style="font-size: 0.75rem; color: var(--ink); background: var(--amber-soft); border: 1px solid var(--warning); border-radius: var(--radius-sm); padding: 6px 8px;">
                ${escapeHtml(warning.message || warning.code || "Reference cohort similarity is unavailable.")}
              </div>
            `).join("")}
          </div>
        ` : ""}
        <p style="margin: 0; font-size: 0.72rem; color: var(--muted);">
          AI output is for clinical decision support only and must be reviewed by a qualified clinician.
        </p>
      </div>
    `;
    } else {
      screeningScoreWidgetHtml = `
      <div class="glass-card" style="padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-lg); background: #fff; display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h4 style="margin: 0; font-size: 0.95rem; color: var(--ink); font-weight: 600;">Reference Cohort Similarity</h4>
          <span class="status-pill" style="background: ${statusBg}; color: ${statusColor}; font-weight: 700; font-size: 0.72rem;">
            ${statusLabel}
          </span>
        </div>
        
        <div style="display: flex; align-items: center; justify-content: space-between; padding-bottom: 8px; border-bottom: 1px solid var(--line);">
          <span style="font-size: 0.85rem; color: var(--muted);">Most similar reference cohort:</span>
          <strong style="font-size: 1rem; color: var(--ink); text-align: right;">${escapeHtml(mostSimilar)} · ${(similarityProbability * 100).toFixed(0)}%</strong>
        </div>

        <div style="display: flex; flex-direction: column; gap: 8px;">
          <span style="font-size: 0.78rem; font-weight: 600; color: var(--ink);">Reference cohort probability profile:</span>
          
          <div style="display: grid; grid-template-columns: 80px 1fr 45px; align-items: center; gap: 8px; font-size: 0.75rem;">
            <strong>ASD ref:</strong>
            <div style="height: 8px; background: var(--line); border-radius: 4px; overflow: hidden; position: relative;">
              <div style="width: ${pAsd}%; height: 100%; background: var(--primary); border-radius: 4px;"></div>
            </div>
            <span style="text-align: right; font-weight: bold; color: var(--primary);">${pAsd}%</span>
          </div>

          <div style="display: grid; grid-template-columns: 80px 1fr 45px; align-items: center; gap: 8px; font-size: 0.75rem;">
            <strong>DD ref:</strong>
            <div style="height: 8px; background: var(--line); border-radius: 4px; overflow: hidden; position: relative;">
              <div style="width: ${pDd}%; height: 100%; background: var(--amber-pending); border-radius: 4px;"></div>
            </div>
            <span style="text-align: right; font-weight: bold; color: var(--amber-pending);">${pDd}%</span>
          </div>

          <div style="display: grid; grid-template-columns: 80px 1fr 45px; align-items: center; gap: 8px; font-size: 0.75rem;">
            <strong>TD ref:</strong>
            <div style="height: 8px; background: var(--line); border-radius: 4px; overflow: hidden; position: relative;">
              <div style="width: ${pTd}%; height: 100%; background: var(--mint); border-radius: 4px;"></div>
            </div>
            <span style="text-align: right; font-weight: bold; color: var(--mint);">${pTd}%</span>
          </div>
        </div>

        <p style="margin: 0; font-size: 0.78rem; line-height: 1.45; color: var(--ink); background: var(--primary-soft); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 8px 10px;">
          ${(aiOutput.plain_language_explanation || "This transcript has feature patterns most similar to a reference cohort. This output is for clinical decision support only and must be reviewed by a qualified clinician.").replace(/</g, "&lt;").replace(/>/g, "&gt;")}
        </p>

        ${warnings.length ? `
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${warnings.slice(0, 3).map(warning => `
              <div style="font-size: 0.75rem; color: var(--ink); background: var(--amber-soft); border: 1px solid var(--warning); border-radius: var(--radius-sm); padding: 6px 8px;">
                ${escapeHtml(warning.message || warning.code || "Review transcript quality before interpreting this output.")}
              </div>
            `).join("")}
          </div>
        ` : ""}

        <div style="display: flex; justify-content: flex-end; margin-top: 6px; border-top: 1px dashed var(--line); padding-top: 8px;">
          <button type="button" class="secondary-action" id="retrain-model-btn" style="min-height: 28px; padding: 2px 10px; font-size: 0.72rem; display: flex; align-items: center; gap: 4px;">
            Review model card
          </button>
        </div>
      </div>
    `;
    }
  }

  // Track observation status (Accept, Reject, Edit)
  const reviews = state.observationsReviews || {};
  const sessReviews = reviews[selectedSession.session_id] || {};

  // Extract real flags from the actual transcript lines for this session
  const allFlags = [];
  transcriptLines.forEach((line, index) => {
    (line.clinical_flags || []).forEach(flag => {
      allFlags.push({
        key: flag.marker_type,
        name: flag.marker_type.replace(/_marker/g, "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
        snippet: `Line ${line.line_number} (${line.speaker}): "${line.text}"`,
        confidence: "90%",
        type: "Linguistic",
        explanation: flag.explanation
      });
    });
  });

  let middleContentHtml = "";
  if (transcriptRecord) {
    const audioFile = state.audioFiles.find(a => a.session_id === selectedSession.session_id);
    const audioUrl = audioFile ? getAudioFileUrl(audioFile.audio_file_id) : null;
    
    const audioPlayerHtml = audioUrl ? `
      <div style="background: var(--primary-soft); border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 0.85rem; font-weight: bold; color: var(--primary);">Session Audio:</span>
        <audio id="transcript-audio-player" src="${audioUrl}" controls style="flex: 1; height: 28px;"></audio>
      </div>
    ` : `
      <div style="background: var(--lavender); border: 1px dashed var(--line); border-radius: 8px; padding: 10px; margin-bottom: 16px; font-size: 0.8rem; color: var(--muted); text-align: center;">
        No recorded audio linked to this session. Timeline play buttons are disabled.
      </div>
    `;

    const headerLines = transcriptRecord.transcript_text
      .split("\n")
      .map(line => line.trim())
      .filter(line => line.startsWith("@") && line.toUpperCase() !== "@END")
      .join("\n");

    const actionButtonsHtml = state.isEditingTranscript ? `
      <button class="primary-action" id="save-transcript-edits-btn" data-session-id="${selectedSession.session_id}">
        Save Transcript Corrections
      </button>
      <button class="secondary-action" id="cancel-transcript-edit-btn" style="min-height: 44px; padding: 9px 14px;">
        Cancel
      </button>
    ` : `
      <button class="primary-action" id="edit-transcript-toggle-btn" style="background: var(--primary); border-color: var(--primary);">
        Edit Transcript
      </button>
      <button class="primary-action" id="rerun-feature-extraction-btn" data-session-id="${selectedSession.session_id}">
        Re-run feature extraction
      </button>
      <button class="secondary-action" id="export-reviewed-chat-btn" data-session-id="${selectedSession.session_id}" style="min-height: 44px; padding: 9px 14px;">
        Export reviewed .cha
      </button>
    `;

    middleContentHtml = `
      <!-- View Dependent Tiers & Audio Player -->
      <div style="margin-bottom: 12px; font-family: sans-serif; font-size: 0.8rem; display: flex; flex-direction: column; gap: 12px;">
        ${audioPlayerHtml}
      </div>

      <!-- Dialogue Rows (Continuous Word Document Sheet) -->
      <div class="word-sheet transcript-view-scrollbar" style="max-height: 520px; overflow-y: auto; padding: 12px; background: #fff; border: 1px solid var(--line); border-radius: var(--radius-md);">
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 12px;">
          <tbody>
            ${transcriptLines
              .map((line, idx) => renderUtteranceRow(line, idx, selectedSession.session_id, state.isEditingTranscript))
              .join("")}
          </tbody>
        </table>
      </div>

      <div style="color: var(--primary); font-family: monospace; font-size: 0.82rem; margin-top: 8px; padding-left: 8px;">@End</div>

      <!-- Action Buttons -->
      <div style="margin-top: 12px; display: flex; gap: 10px; flex-wrap: wrap; border-top: 1px solid var(--line); padding-top: 16px;">
        ${actionButtonsHtml}
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
        </div>
      </div>
    `;
  }

  // Right column: AI Observations card list (Dynamic)
  let observationsCardsHtml = "";
  if (allFlags.length > 0) {
    observationsCardsHtml = allFlags.map(obs => {
      const rev = sessReviews[obs.key] || { status: "pending", note: "" };
      
      let badgeColor = "var(--muted)";
      let badgeBg = "var(--lavender)";
      if (rev.status === "accepted") {
        badgeColor = "var(--mint)";
        badgeBg = "var(--mint-soft)";
      } else if (rev.status === "rejected") {
        badgeColor = "var(--red-alert)";
        badgeBg = "var(--red-soft)";
      } else if (rev.status === "edited") {
        badgeColor = "var(--medical-blue)";
        badgeBg = "var(--medical-blue-soft)";
      }

      return `
        <div class="glass-card ai-observation-card">
          <div class="ai-observation-header">
            <strong class="ai-observation-title">${escapeHtml(obs.name)}</strong>
            <div class="ai-observation-badges">
              <span class="status-pill ai-observation-confidence">Conf: ${obs.confidence}</span>
              <span class="status-pill ai-observation-status" style="background: ${badgeBg}; color: ${badgeColor};">${rev.status}</span>
            </div>
          </div>
          <p class="ai-observation-snippet">
            ${escapeHtml(obs.snippet)}
          </p>
          <div class="ai-observation-explanation">
            ${escapeHtml(obs.explanation)}
          </div>
          
          <!-- Note Field -->
          <input type="text" class="obs-note-input glass-input ai-observation-note" data-obs-key="${escapeHtml(obs.key)}" value="${escapeHtml(rev.note)}" placeholder="Add clinician note/annotation..." />

          <!-- Clinician Action Buttons -->
          <div class="ai-observation-actions">
            <button class="small-action obs-accept-btn ${rev.status === "accepted" ? "active" : ""}" data-obs-key="${escapeHtml(obs.key)}" style="flex: 1; min-height: 28px; font-size: 0.75rem; background: ${rev.status === "accepted" ? "var(--mint)" : "transparent"}; color: ${rev.status === "accepted" ? "#fff" : "var(--muted)"}; border: 1px solid var(--line);">Accept</button>
            <button class="small-action obs-edit-btn ${rev.status === "edited" ? "active" : ""}" data-obs-key="${escapeHtml(obs.key)}" style="flex: 1; min-height: 28px; font-size: 0.75rem; background: ${rev.status === "edited" ? "var(--medical-blue)" : "transparent"}; color: ${rev.status === "edited" ? "#fff" : "var(--muted)"}; border: 1px solid var(--line);">Edit</button>
            <button class="small-action obs-reject-btn ${rev.status === "rejected" ? "active" : ""}" data-obs-key="${escapeHtml(obs.key)}" style="flex: 1; min-height: 28px; font-size: 0.75rem; background: ${rev.status === "rejected" ? "var(--red-alert)" : "transparent"}; color: ${rev.status === "rejected" ? "#fff" : "var(--muted)"}; border: 1px solid var(--line);">Reject</button>
          </div>
        </div>
      `;
    }).join("");
  } else {
    observationsCardsHtml = `
      <div class="glass-card" style="padding: 20px; text-align: center; background: #fff; border: 1px solid var(--line); border-radius: var(--radius-md);">
        <div style="color: var(--mint); font-size: 1.5rem; margin-bottom: 8px;">✓</div>
        <strong style="font-size: 0.85rem; color: var(--ink);">No Atypical Markers</strong>
        <p style="font-size: 0.78rem; color: var(--muted); margin: 4px 0 0;">This transcript is clear of flagged pronoun reversals, echolalia-like patterns, or unintelligible segments.</p>
      </div>
    `;
  }

  const activeTab = state.activeWorkspaceTab || "observations";
  const qaState = state.transcriptQaResults[selectedSession.session_id];
  const comparisonState = state.referenceComparisons[selectedSession.session_id];

  const tabsHeaderHtml = `
    <div class="workspace-tabs-header" style="display: flex; gap: 8px; border-bottom: 1px solid var(--line); padding-bottom: 8px; margin-bottom: 8px;">
      <button type="button" class="workspace-tab-btn ${activeTab === "observations" ? "active" : ""}" data-tab="observations" style="flex: 1; padding: 8px 12px; font-size: 0.85rem; font-weight: 600; border-radius: var(--radius-md); border: 1px solid ${activeTab === "observations" ? "var(--primary)" : "var(--line)"}; background: ${activeTab === "observations" ? "var(--primary-soft)" : "transparent"}; color: ${activeTab === "observations" ? "var(--primary)" : "var(--muted)"}; cursor: pointer; text-align: center;">
        AI Observations
      </button>
      <button type="button" class="workspace-tab-btn ${activeTab === "features" ? "active" : ""}" data-tab="features" style="flex: 1; padding: 8px 12px; font-size: 0.85rem; font-weight: 600; border-radius: var(--radius-md); border: 1px solid ${activeTab === "features" ? "var(--primary)" : "var(--line)"}; background: ${activeTab === "features" ? "var(--primary-soft)" : "transparent"}; color: ${activeTab === "features" ? "var(--primary)" : "var(--muted)"}; cursor: pointer; text-align: center;">
        Extracted Features
      </button>
      <button type="button" class="workspace-tab-btn ${activeTab === "cohort" ? "active" : ""}" data-tab="cohort" style="flex: 1; padding: 8px 12px; font-size: 0.85rem; font-weight: 600; border-radius: var(--radius-md); border: 1px solid ${activeTab === "cohort" ? "var(--primary)" : "var(--line)"}; background: ${activeTab === "cohort" ? "var(--primary-soft)" : "transparent"}; color: ${activeTab === "cohort" ? "var(--primary)" : "var(--muted)"}; cursor: pointer; text-align: center;">
        Cohort Comparison
      </button>
    </div>
  `;

  const observationsTabHtml = `
    <div style="display: flex; flex-direction: column; gap: 16px;">
      ${screeningScoreWidgetHtml}
      <div class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-lg); background: #fff;">
        <h4 style="margin: 0 0 4px; font-size: 0.95rem; color: var(--ink); font-weight: 600;">AI-assisted Observations</h4>
        <p style="font-size: 0.78rem; color: var(--muted); margin: 0 0 16px;">Inspect and verify each speech-language marker.</p>
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${observationsCardsHtml}
        </div>
      </div>
    </div>
  `;

  const FEATURE_METADATA = {
    age_months: { label: "Age (Months)", desc: "Child's age in months" },
    total_utterances: { label: "Total Utterances", desc: "Number of utterances in transcription" },
    mlu: { label: "Mean Length of Utterance (MLU)", desc: "Average morphemes/words per child utterance" },
    mluw: { label: "MLU in Words (MLU-w)", desc: "Average words per child utterance" },
    mlu_s: { label: "Thai Syllable MLU (MLU-s)", desc: "Average Thai syllables per child utterance" },
    ttr: { label: "Type-Token Ratio (TTR)", desc: "Vocabulary diversity (unique / total words)" },
    total_words: { label: "Total Words Spoken", desc: "Total child words" },
    unintelligible_count: { label: "Unintelligible Utterances", desc: "Turns marked as unintelligible (xxx, yyy)" },
    unintelligible_ratio: { label: "Unintelligible Ratio", desc: "Ratio of unintelligible utterances" },
    zero_vocalization_count: { label: "Zero Spoken Responses", desc: "Child turns with zero vocal/verbal response" },
    nonverbal_vocalization_count: { label: "Nonverbal Vocalizations", desc: "Child nonverbal turns (e.g. gesture, grunt)" },
    question_ratio: { label: "Question Ratio", desc: "Ratio of child utterances that are questions" },
    echolalia_count: { label: "Echolalia Repetitions", desc: "Turns flagged with echolalia-like repetitions" },
    echolalia_ratio: { label: "Echolalia Ratio", desc: "Ratio of child turns containing echolalia" },
    pronoun_reversal_count: { label: "Pronoun Reversals", desc: "Turns flagged with pronoun reversal" }
  };

  const featureValues = features?.features || {};
  const featuresRowsHtml = Object.entries(FEATURE_METADATA).map(([key, meta]) => {
    let rawVal = featureValues[key];
    let displayVal = "-";
    if (rawVal !== undefined && rawVal !== null) {
      if (typeof rawVal === "number") {
        if (key.includes("ratio") || key === "ttr" || key.includes("percent")) {
          if (key === "ttr") {
            displayVal = rawVal.toFixed(2);
          } else {
            displayVal = `${(rawVal * 100).toFixed(1)}%`;
          }
        } else if (Number.isInteger(rawVal)) {
          displayVal = rawVal.toString();
        } else {
          displayVal = rawVal.toFixed(2);
        }
      } else {
        displayVal = String(rawVal);
      }
    }
    return `
      <tr style="border-bottom: 1px solid var(--line);">
        <td style="padding: 10px 8px; font-size: 0.8rem; font-weight: 600; color: var(--ink);">${escapeHtml(meta.label)}</td>
        <td style="padding: 10px 8px; font-size: 0.75rem; color: var(--muted); line-height: 1.3;">${escapeHtml(meta.desc)}</td>
        <td style="padding: 10px 8px; font-size: 0.8rem; font-weight: 700; color: var(--primary); text-align: right;">${escapeHtml(displayVal)}</td>
      </tr>
    `;
  }).join("");

  const featuresTabHtml = `
    <div class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-lg); background: #fff;">
      <h4 style="margin: 0 0 4px; font-size: 0.95rem; color: var(--ink); font-weight: 600;">14-Feature Extraction Profile</h4>
      <p style="font-size: 0.78rem; color: var(--muted); margin: 0 0 16px;">Derived NLP features extracted automatically from the CHAT transcript.</p>
      <div class="transcript-view-scrollbar" style="max-height: 500px; overflow-y: auto;">
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr style="border-bottom: 2px solid var(--line); text-align: left; font-size: 0.75rem; color: var(--muted); font-weight: 700;">
              <th style="padding: 6px 8px;">Feature</th>
              <th style="padding: 6px 8px;">Description</th>
              <th style="padding: 6px 8px; text-align: right;">Value</th>
            </tr>
          </thead>
          <tbody>
            ${featuresRowsHtml || '<tr><td colspan="3" class="empty-state" style="font-size: 0.8rem; text-align: center; padding: 20px;">No features extracted yet. Please run Feature Extraction.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
  `;

  const cohortTabHtml = renderReferenceComparisonPanel({
    session: selectedSession,
    transcript: transcriptRecord,
    features: features,
    qaResult: qaState,
    aiOutput: aiOutput,
    currentUser: state.currentUser,
    comparisonState: comparisonState
  });

  return `
    ${renderSafetyBanner()}
    
    <!-- Top info bar -->
    <div class="glass-card" style="padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-md); display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
      <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
        <div>
          <span style="font-size: 0.8rem; color: var(--muted); font-weight: 500; display: block;">SESSION REVIEW</span>
          <h3 style="margin: 2px 0 0; font-size: 1.2rem; font-weight: 700; color: var(--ink);">${escapeHtml(childCase?.display_label || "Child case")}</h3>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <select id="transcript-case-select" class="case-select-filter" style="max-width: 250px;" aria-label="Select child case">
            ${caseOptions}
          </select>
          <select id="transcript-session-select" class="case-select-filter" style="max-width: 250px;" aria-label="Select session">
            ${sessionOptions}
          </select>
        </div>
      </div>
      <div>
        <span class="status-pill" style="background: var(--amber-soft); color: var(--amber-pending); font-weight: 700; font-size: 0.75rem;">
          ${selectedSession.therapist_review_status.replaceAll("_", " ")}
        </span>
      </div>
    </div>

    <!-- Split Analysis Workspace Layout -->
    <div class="transcript-split-layout">
      
      <!-- Left Column: Audio and Transcript -->
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-lg);">
          <h4 style="margin-bottom: 12px; font-size: 0.95rem; color: var(--ink); font-weight: 600;">Interactive Transcript & Audio</h4>
          ${middleContentHtml}
        </div>
      </div>

      <!-- Right Column: AI-assisted Observations Panel -->
      <div style="display: flex; flex-direction: column; gap: 16px;">
        ${tabsHeaderHtml}
        
        <div class="workspace-tab-content" id="w-tab-content-observations" style="display: ${activeTab === "observations" ? "block" : "none"};">
          ${observationsTabHtml}
        </div>
        
        <div class="workspace-tab-content" id="w-tab-content-features" style="display: ${activeTab === "features" ? "block" : "none"};">
          ${featuresTabHtml}
        </div>
        
        <div class="workspace-tab-content" id="w-tab-content-cohort" style="display: ${activeTab === "cohort" ? "block" : "none"};">
          ${cohortTabHtml}
        </div>

        <!-- Clinical Notes Box -->
        <div class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-lg);">
          <h4 style="margin: 0 0 10px; font-size: 0.95rem; color: var(--ink); font-weight: 600;">Therapist Workspace Notes</h4>
          <textarea id="review-notes" class="glass-input" style="min-height: 80px; font-size: 0.8rem; padding: 8px;" placeholder="Add internal case notes / review details...">${selectedSession.notes || ""}</textarea>
        </div>
      </div>
    </div>

    <!-- Bottom Sticky Action Bar -->
    <div style="position: fixed; bottom: 0; left: 0; right: 0; background: rgba(255, 255, 255, 0.95); backdrop-filter: var(--backdrop-blur); border-top: 1px solid var(--line); padding: 12px 34px; display: flex; justify-content: space-between; align-items: center; z-index: 1000; box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.025);">
      <span style="font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; gap: 6px;">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--primary);"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
        AI-assisted observation decision support gate.
      </span>
      <div style="display: flex; gap: 10px;">
        <button class="secondary-action" id="session-save-draft-btn" data-session-id="${selectedSession.session_id}" style="min-height: 38px; padding: 6px 14px; font-weight: 600;">Save Draft</button>
        <button class="primary-action" id="session-reviewed-btn" data-session-id="${selectedSession.session_id}" style="min-height: 38px; padding: 6px 14px; font-weight: 600;">Mark as Reviewed</button>
        <button class="primary-action" id="session-generate-report-btn" data-session-id="${selectedSession.session_id}" style="min-height: 38px; padding: 6px 14px; font-weight: 600; background: var(--mint); border-color: var(--mint);">Generate Report</button>
      </div>
    </div>
  `;
}

export function bindTranscriptReview(navigate) {
  // Bind Workspace Tab Switching
  const tabBtns = document.querySelectorAll(".workspace-tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tabName = btn.getAttribute("data-tab");
      store.setState({ activeWorkspaceTab: tabName });
      navigate("transcript");
    });
  });

  // Helpers to update observation review state
  const setObsStatus = (sessId, key, status) => {
    const state = store.getState();
    const reviews = state.observationsReviews || {};
    const sessReviews = reviews[sessId] || {};
    sessReviews[key] = { ...sessReviews[key], status };
    store.setState({
      observationsReviews: { ...reviews, [sessId]: sessReviews }
    });
    navigate("transcript");
  };

  const setObsNote = (sessId, key, note) => {
    const state = store.getState();
    const reviews = state.observationsReviews || {};
    const sessReviews = reviews[sessId] || {};
    sessReviews[key] = { ...sessReviews[key], note };
    store.setState({
      observationsReviews: { ...reviews, [sessId]: sessReviews }
    });
  };

  // Bind toggle buttons
  const editToggleBtn = document.getElementById("edit-transcript-toggle-btn");
  if (editToggleBtn) {
    editToggleBtn.addEventListener("click", () => {
      store.setState({ isEditingTranscript: true });
      navigate("transcript");
    });
  }

  const cancelEditBtn = document.getElementById("cancel-transcript-edit-btn");
  if (cancelEditBtn) {
    cancelEditBtn.addEventListener("click", () => {
      store.setState({ isEditingTranscript: false });
      navigate("transcript");
    });
  }

  const retrainBtn = document.getElementById("retrain-model-btn");
  if (retrainBtn) {
    retrainBtn.addEventListener("click", async () => {
      retrainBtn.innerText = "Retraining Model...";
      retrainBtn.disabled = true;
      try {
        const response = await api.post("/model/retrain");
        if (response && response.status === "success") {
          let msg = "Screening model retrained successfully!\n\nMetrics:\n";
          if (response.metrics) {
            Object.keys(response.metrics).forEach(key => {
              msg += `- ${key}: Accuracy = ${response.metrics[key].accuracy}, F1 = ${response.metrics[key].f1}\n`;
            });
          }
          alert(msg);
        } else {
          alert("Model retraining failed: " + (response?.message || "Unknown error"));
        }
      } catch (err) {
        alert("Model retraining failed: " + err.message);
      } finally {
        retrainBtn.innerText = "Retrain Screening Model";
        retrainBtn.disabled = false;
      }
    });
  }

  const exportReviewedChatBtn = document.getElementById("export-reviewed-chat-btn");
  if (exportReviewedChatBtn) {
    exportReviewedChatBtn.addEventListener("click", async () => {
      const sessId = exportReviewedChatBtn.getAttribute("data-session-id");
      exportReviewedChatBtn.disabled = true;
      const originalText = exportReviewedChatBtn.innerText;
      exportReviewedChatBtn.innerText = "Exporting .cha...";
      try {
        const result = await api.text(`/api/sessions/${sessId}/transcript/export.cha`);
        const blob = new Blob([result.body], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${sessId}_reviewed.cha`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        addAudit("chat_exported", "Session", sessId, "Exported reviewed CHAT transcript.");
      } catch (err) {
        const detail = err?.payload?.detail || err.message || "Reviewed CHAT export failed.";
        alert(`Reviewed CHAT export failed: ${detail}`);
      } finally {
        exportReviewedChatBtn.disabled = false;
        exportReviewedChatBtn.innerText = originalText;
      }
    });
  }

  // Bind Observation buttons (Accept, Edit, Reject)
  const acceptBtns = document.querySelectorAll(".obs-accept-btn");
  acceptBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const sessId = store.getState().selectedSessionId || "SESSION-001";
      const key = btn.getAttribute("data-obs-key");
      setObsStatus(sessId, key, "accepted");
    });
  });

  const editBtns = document.querySelectorAll(".obs-edit-btn");
  editBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const sessId = store.getState().selectedSessionId || "SESSION-001";
      const key = btn.getAttribute("data-obs-key");
      setObsStatus(sessId, key, "edited");
    });
  });

  const rejectBtns = document.querySelectorAll(".obs-reject-btn");
  rejectBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const sessId = store.getState().selectedSessionId || "SESSION-001";
      const key = btn.getAttribute("data-obs-key");
      setObsStatus(sessId, key, "rejected");
    });
  });

  // Bind Note inputs
  const noteInputs = document.querySelectorAll(".obs-note-input");
  noteInputs.forEach(input => {
    input.addEventListener("input", (e) => {
      const sessId = store.getState().selectedSessionId || "SESSION-001";
      const key = input.getAttribute("data-obs-key");
      setObsNote(sessId, key, e.target.value);
    });
  });

  // Sticky bottom bar actions
  const saveDraftBtn = document.getElementById("session-save-draft-btn");
  if (saveDraftBtn) {
    saveDraftBtn.addEventListener("click", () => {
      const sessId = saveDraftBtn.getAttribute("data-session-id");
      const notes = document.getElementById("review-notes").value;
      saveEvidenceReviewEdits(sessId);
      
      // Update session notes in store
      const sessions = store.getState().sessions.map(s => {
        if (s.session_id === sessId) {
          return { ...s, notes };
        }
        return s;
      });
      store.setState({ sessions });
      
      alert("Workspace draft saved successfully.");
    });
  }

  const markReviewedBtn = document.getElementById("session-reviewed-btn");
  if (markReviewedBtn) {
    markReviewedBtn.addEventListener("click", async () => {
      const sessId = markReviewedBtn.getAttribute("data-session-id");
      const notes = document.getElementById("review-notes").value;
      markReviewedBtn.disabled = true;
      const originalText = markReviewedBtn.innerText;
      markReviewedBtn.innerText = "Saving review...";
      try {
        await saveTherapistReview({
          sessionId: sessId,
          notes,
          approvedSummary: "Transcript reviewed for CHAT export and feature extraction."
        });
        addAudit("reviewed", "Session", sessId, "Marked session transcript and observations as reviewed.");
        alert("Session marked as reviewed.");
        navigate("dashboard");
      } catch (err) {
        const detail = err?.payload?.detail || err.message || "Could not mark transcript reviewed.";
        alert(`Review sign-off failed: ${detail}`);
      } finally {
        markReviewedBtn.disabled = false;
        markReviewedBtn.innerText = originalText;
      }
    });
  }

  const generateReportBtn = document.getElementById("session-generate-report-btn");
  if (generateReportBtn) {
    generateReportBtn.addEventListener("click", () => {
      const sessId = generateReportBtn.getAttribute("data-session-id");
      store.setState({ selectedSessionId: sessId });
      navigate("progress"); // Route to progress report
    });
  }

  // Fallback upload trigger
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

  // Generate mock button
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

      store.setState({
        transcripts: { ...state.transcripts, [sessId]: transcriptRecord },
        transcriptLines: { ...state.transcriptLines, [sessId]: transcriptLines },
        extractedFeatureOutputs: { ...state.extractedFeatureOutputs, [sessId]: featuresSet },
        aiDecisionOutputs: { ...state.aiDecisionOutputs, [sessId]: aiOutput },
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
  // File Links
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

  // Highlight and auto-scroll active utterance during audio playback
  if (audioPlayer) {
    audioPlayer.addEventListener("timeupdate", () => {
      const currentTime = audioPlayer.currentTime;
      const rows = document.querySelectorAll(".utterance-row");
      rows.forEach(row => {
        const start = parseFloat(row.getAttribute("data-start"));
        const end = parseFloat(row.getAttribute("data-end"));
        if (!isNaN(start) && !isNaN(end) && currentTime >= start && currentTime <= end) {
          row.style.background = "var(--primary-soft)";
          if (!row.classList.contains("highlighted-playing")) {
            row.classList.add("highlighted-playing");
            row.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
        } else {
          row.style.background = "";
          row.classList.remove("highlighted-playing");
        }
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

  // Case switcher
  const caseSelect = document.getElementById("transcript-case-select");
  if (caseSelect) {
    caseSelect.addEventListener("change", e => {
      const caseId = e.target.value;
      const state = store.getState();
      const visibleSessions = getVisibleSessions();
      const filteredSessions = visibleSessions.filter(s => s.case_id === caseId);
      if (filteredSessions.length > 0) {
        store.setState({ selectedSessionId: filteredSessions[0].session_id });
      }
      navigate("transcript");
    });
  }

  // Session switcher
  const sessionSelect = document.getElementById("transcript-session-select");
  if (sessionSelect) {
    sessionSelect.addEventListener("change", e => {
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
          isEditingTranscript: false,
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

      if (state.dataMode === "api" || state.dataMode === "supabase") {
        rerunFeaturesBtn.disabled = true;
        api.post(`/api/sessions/${sessId}/features/extract`, {}).then(async (features) => {
          const [aiOutput, referenceComparison] = await Promise.all([
            api.post(`/api/sessions/${sessId}/reference-cohort-similarity`, {}),
            api.get(`/api/sessions/${sessId}/reference-comparison`)
          ]);

          const nextState = store.getState();
          store.setState({
            extractedFeatureOutputs: { ...nextState.extractedFeatureOutputs, [sessId]: features },
            aiDecisionOutputs: { ...nextState.aiDecisionOutputs, [sessId]: aiOutput },
            referenceComparisons: { ...nextState.referenceComparisons, [sessId]: referenceComparison }
          });

          updateSessionStatus(sessId, {
            feature_extraction_status: features.extraction_status || features.status || "completed",
            ai_analysis_status: aiOutput.therapist_review_status
          });

          addAudit("rerun_feature_extraction", "Session", sessId, "Re-ran feature extraction after transcript review/correction.");
          alert(reviewed ? "Feature extraction re-run complete." : "Feature extraction re-run complete and remains preliminary until transcript review is signed off.");
          navigate("transcript");
        }).catch(err => {
          console.error("Failed to rerun feature extraction:", err);
          alert("Error rerunning feature extraction: " + err.message);
        }).finally(() => {
          rerunFeaturesBtn.disabled = false;
        });
        return;
      }

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
