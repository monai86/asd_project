import { store } from "../store/state.js";
import { getVisibleSessions } from "../services/session-service.js";
import { getVisibleCases } from "../services/case-service.js";

export function renderAIReview() {
  const state = store.getState();
  const sessions = getVisibleSessions();
  const cases = getVisibleCases();

  // Find sessions where review is pending or AI observations are generated
  const pendingSessions = sessions.filter(s => {
    // In our prototype, sessions that have ASR/AI outputs are waiting for review
    return s.therapist_review_status === "awaiting_review" || s.therapist_review_status === "needs_correction" || s.processing_stage === "awaiting_review";
  });

  const completedSessions = sessions.filter(s => s.therapist_review_status === "reviewed");

  return `
    <div class="glass-card" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
      <div class="panel-title" style="margin-bottom: 0;">
        <div>
          <h3>AI-Assisted Observations Review Queue</h3>
          <p class="lead" style="font-size: 0.9rem; margin-top: 4px;">Clinician-in-the-loop validation queue. Accept, edit, or reject observations before generating progress reports.</p>
        </div>
        <span class="mini-tag" style="background: var(--primary-soft); color: var(--primary); font-weight: 600;">${pendingSessions.length} Pending</span>
      </div>

      <div style="display: grid; grid-template-columns: 1fr; gap: 16px; margin-top: 8px;">
        <div class="clinical-status-banner status-good-soft" style="margin-bottom: 0; padding: 12px 16px; display: flex; align-items: center; gap: 8px; border-radius: var(--radius-md);">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/></svg>
          <span style="font-size: 0.85rem; color: var(--ink); font-weight: 500;">
            <strong>Human-in-the-Loop Gate:</strong> AI-assisted observations are descriptive decision-support screening support only. Final interpretation must be reviewed and signed off by a qualified clinician. This system does not diagnose ASD.
          </span>
        </div>
      </div>

      <div class="review-sections-grid two-column wide-left" style="margin-top: 12px; gap: 24px;">
        <!-- Left: Awaiting Review List -->
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <h4 style="font-size: 1rem; color: var(--ink); margin-bottom: 4px;">Awaiting Clinician Review</h4>
          
          <div class="queue-list" style="display: flex; flex-direction: column; gap: 12px;">
            ${pendingSessions.map(s => {
              const c = cases.find(item => item.case_id === s.case_id);
              const ageLabel = c ? `${c.age_months} mo` : "N/A";
              return `
                <div class="queue-item-card glass-card" style="display: flex; justify-content: space-between; align-items: center; padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-md); transition: all 0.2s ease;">
                  <div style="display: flex; flex-direction: column; gap: 4px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <strong style="font-size: 0.95rem; color: var(--ink);">${c?.display_label || s.case_id}</strong>
                      <span class="mini-tag" style="background: var(--lavender); color: var(--muted);">${ageLabel}</span>
                    </div>
                    <span style="font-size: 0.8rem; color: var(--muted);">Session Date: ${s.session_date} · ID: ${s.session_id}</span>
                    <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
                      <span class="status-pill" style="font-size: 0.7rem; background: var(--amber-soft); color: var(--amber-pending); font-weight: 600;">AI observations generated</span>
                      <span style="font-size: 0.75rem; color: var(--muted);">Confidence: Medium-High</span>
                    </div>
                  </div>
                  <button class="primary-action start-review-btn" data-session-id="${s.session_id}" style="min-height: 38px; padding: 6px 14px; font-size: 0.85rem; font-weight: 600;">
                    Open Workspace
                  </button>
                </div>
              `;
            }).join("")}
            
            ${pendingSessions.length === 0 ? `
              <div class="empty-state" style="text-align: center; padding: 48px; border: 1.5px dashed var(--line); border-radius: var(--radius-lg); background: #ffffff;">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 12px; opacity: 0.5;"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
                <h4 style="margin-bottom: 4px; color: var(--ink);">All Session Reviews Completed</h4>
                <p style="font-size: 0.85rem; color: var(--muted);">There are no sessions currently waiting for AI observation verification.</p>
              </div>
            ` : ""}
          </div>
        </div>

        <!-- Right: Recent Sign-offs & Summary -->
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <h4 style="font-size: 1rem; color: var(--ink); margin-bottom: 4px;">Reviewed & Certified Sessions</h4>
          <div class="glass-card" style="padding: 16px; background: var(--panel); border: 1px solid var(--line); display: flex; flex-direction: column; gap: 12px;">
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${completedSessions.slice(0, 5).map(s => {
                const c = cases.find(item => item.case_id === s.case_id);
                return `
                  <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 1px solid var(--lavender);">
                    <div style="display: flex; flex-direction: column; gap: 2px;">
                      <span style="font-weight: 600; font-size: 0.85rem; color: var(--ink);">${c?.display_label || s.case_id}</span>
                      <span style="font-size: 0.75rem; color: var(--muted);">${s.session_date}</span>
                    </div>
                    <span class="status-pill" style="font-size: 0.7rem; background: var(--mint-soft); color: var(--mint); font-weight: 600;">Reviewed</span>
                  </div>
                `;
              }).join("")}
              ${completedSessions.length === 0 ? `<p class="empty-state" style="font-size: 0.8rem; text-align: center; padding: 16px;">No reviewed sessions recorded yet.</p>` : ""}
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

export function bindAIReview(navigate) {
  const btns = document.querySelectorAll(".start-review-btn");
  btns.forEach(btn => {
    btn.addEventListener("click", () => {
      const sessId = btn.getAttribute("data-session-id");
      store.setState({ selectedSessionId: sessId });
      navigate("transcript"); // Navigate to Split Workspace
    });
  });
}
