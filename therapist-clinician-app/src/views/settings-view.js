import { store } from "../store/state.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { AUTH_MODE, FILE_STORAGE_MODE, PROCESSING_MODE } from "../constants.js";
import { renderEnvironmentModeBanner } from "../components/environment-mode-banner.js";

export function renderSettings() {
  const { currentUser, authStatus } = store.getState();
  const { dataMode, persistenceStatus, privacyOperations = [] } = store.getState();

  return `
    ${renderSafetyBanner()}
    ${renderEnvironmentModeBanner(store.getState())}
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
          <strong>Auth Status:</strong>
          <span style="display: block; font-size: 0.9rem; color: var(--muted);">${authStatus}</span>
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
    <section class="panel" style="padding: 16px; margin-top: 16px;">
      <div class="panel-title">
        <h3>Privacy Operations</h3>
        <span>export, withdrawal, and deletion request queue</span>
      </div>
      <p style="font-size: 0.9rem; color: var(--muted); max-width: 720px;">
        Privacy operations are requests that must be reviewed according to clinic policy. Case deletion requests do not erase audit logs.
      </p>
      <div style="display: grid; gap: 8px;">
        ${privacyOperations
          .slice()
          .reverse()
          .map(
            operation => `
            <div style="padding: 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--shell);">
              <strong>${operation.operation_type.replaceAll("_", " ")}</strong>
              <div style="font-size: 0.82rem; color: var(--muted);">
                ${operation.operation_id} · case ${operation.case_id} · status ${operation.status} · ${new Date(operation.created_at).toLocaleString()}
              </div>
            </div>
          `
          )
          .join("") || '<p class="empty-state">No privacy operation requests recorded yet.</p>'}
      </div>
    </section>
  `;
}

export function bindSettings(navigate) {
  // No complex interactive logic for settings settings
}
