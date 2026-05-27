import { renderSafetyBanner } from "../components/safety-banner.js";

export function renderResourceLibrary() {
  return `
    ${renderSafetyBanner()}
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
          <p style="font-size: 0.85rem; color: var(--muted);">Suggested scripts to frame language trends without diagnostics.</p>
        </div>
      </div>
    </section>
  `;
}

export function bindResourceLibrary(navigate) {
  // No interactive bindings needed
}
