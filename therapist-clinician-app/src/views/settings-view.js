import { store } from "../store/state.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { AUTH_MODE, FILE_STORAGE_MODE, PROCESSING_MODE } from "../constants.js";

export function renderSettings() {
  const { currentUser } = store.getState();
  const { dataMode, persistenceStatus } = store.getState();

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
          <strong>Data Mode:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">${dataMode} (${persistenceStatus})</span>
        </div>
        <div>
          <strong>Auth Mode:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">${AUTH_MODE}</span>
        </div>
        <div>
          <strong>Role:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">${currentUser?.role}</span>
        </div>
        <div>
          <strong>Persistence Boundary:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">Demo records stay within the active data mode. Mock, localStorage, and database-placeholder records are not silently mixed.</span>
        </div>
        <div>
          <strong>File Storage Mode:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">${FILE_STORAGE_MODE}</span>
        </div>
        <div>
          <strong>Audio Processing Mode:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">${PROCESSING_MODE}</span>
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
