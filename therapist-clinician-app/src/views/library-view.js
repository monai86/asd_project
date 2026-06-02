import { renderSafetyBanner } from "../components/safety-banner.js";
import { store } from "../store/state.js";
import { loadReferenceReadiness } from "../services/reference-readiness-service.js";

export function renderResourceLibrary() {
  const state = store.getState();
  const readiness = state.referenceReadiness || {
    status: "loading",
    summary: { ok: 0, low_n: 0, not_cohort_ready: 0 }
  };

  let readinessHtml = "";
  if (readiness.status === "loading") {
    readinessHtml = `<p style="font-size: 0.85rem; color: var(--muted);">Loading Reference Readiness Index...</p>`;
  } else if (readiness.status === "error") {
    readinessHtml = `<p style="font-size: 0.85rem; color: var(--rose); font-weight: bold;">Error loading index: ${readiness.error_detail || "API failed."}</p>`;
  } else {
    readinessHtml = `
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 16px;">
        <div style="padding: 10px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--shell); text-align: center;">
          <h5 style="margin: 0; font-size: 0.8rem; color: var(--muted);">Ready Cohorts</h5>
          <span style="font-size: 1.6rem; font-weight: bold; color: var(--violet);">${readiness.summary.ok}</span>
        </div>
        <div style="padding: 10px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--shell); text-align: center;">
          <h5 style="margin: 0; font-size: 0.8rem; color: var(--muted);">Low-count Cohorts (Caution)</h5>
          <span style="font-size: 1.6rem; font-weight: bold; color: var(--amber);">${readiness.summary.low_n}</span>
        </div>
        <div style="padding: 10px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--shell); text-align: center;">
          <h5 style="margin: 0; font-size: 0.8rem; color: var(--muted);">Excluded / Not Ready</h5>
          <span style="font-size: 1.6rem; font-weight: bold; color: var(--muted);">${readiness.summary.not_cohort_ready}</span>
        </div>
      </div>
      <p style="font-size: 0.78rem; color: var(--muted); font-style: italic; margin-top: 4px;">
        * Note: All descriptive reference comparisons are research-only and do not diagnose. Low-count cells are marked for caution.
      </p>
    `;
  }

  return `
    ${renderSafetyBanner()}
    <section class="panel" style="padding: 16px; margin-bottom: 16px;">
      <div class="panel-title">
        <h3>Reference Cohort Readiness</h3>
        <span>Summary of available descriptive reference cells</span>
      </div>
      ${readinessHtml}
    </section>

    <section class="panel" style="padding: 16px;">
      <div class="panel-title">
        <h3>Resource Library</h3>
        <span>Clinical support materials</span>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
        <div style="padding: 12px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--shell);">
          <h4>Transcript QA checklist</h4>
          <p style="font-size: 0.85rem; color: var(--muted);">Guidelines for verifying participant tiers, headers, and transcription fidelity.</p>
        </div>
        <div style="padding: 12px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--shell);">
          <h4>Session sampling guide</h4>
          <p style="font-size: 0.85rem; color: var(--muted);">Standardized protocols for recording free play and structured assessments.</p>
        </div>
        <div style="padding: 12px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--shell);">
          <h4>Safety wording for caregiver conversations</h4>
          <p style="font-size: 0.85rem; color: var(--muted);">Suggested scripts to frame language trends using descriptive explanations only.</p>
        </div>
      </div>
    </section>
  `;
}

export function bindResourceLibrary(navigate) {
  const state = store.getState();
  if (!state.referenceReadiness) {
    store.setState({
      referenceReadiness: {
        status: "loading",
        summary: { ok: 0, low_n: 0, not_cohort_ready: 0 },
        cells: []
      }
    }, { persist: false });

    loadReferenceReadiness({
      currentUser: state.currentUser
    }).then(result => {
      store.setState({
        referenceReadiness: result
      }, { persist: false });
      navigate("library");
    });
  }
}

