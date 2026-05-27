import { store } from "../store/state.js";
import { renderSafetyBanner } from "../components/safety-banner.js";

export function renderSettings() {
  const { currentUser } = store.getState();

  return `
    ${renderSafetyBanner()}
    <section class="panel" style="padding: 16px;">
      <div class="panel-title">
        <h3>Settings</h3>
        <span>preferences & credentials</span>
      </div>
      <div style="display: grid; gap: 14px; max-width: 400px;">
        <div>
          <strong>Name:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">${currentUser?.name}</span>
        </div>
        <div>
          <strong>Email:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">${currentUser?.email}</span>
        </div>
        <div>
          <strong>Credentials:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">${currentUser?.credentials}</span>
        </div>
        <div>
          <strong>Organization:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">${currentUser?.organization}</span>
        </div>
        <div>
          <strong>ASR Provider Engine:</strong>
          <select style="margin-top: 6px; padding: 6px; border-radius: 4px; border: 1px solid var(--line);">
            <option>Mock Batchalign2 ASR Provider (Interactive Delay)</option>
            <option disabled>OpenAI Whisper API (Offline/Future Integration)</option>
            <option disabled>Rev.AI Speech-to-Text (Offline/Future Integration)</option>
          </select>
        </div>
      </div>
    </section>
  `;
}

export function bindSettings(navigate) {
  // No complex interactive logic for settings settings
}
