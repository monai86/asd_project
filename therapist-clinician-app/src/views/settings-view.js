import { store } from "../store/state.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { AUTH_MODE, FILE_STORAGE_MODE, PROCESSING_MODE } from "../constants.js";
import { renderEnvironmentModeBanner } from "../components/environment-mode-banner.js";

export function renderSettings() {
  const { currentUser, authStatus } = store.getState();
  const { dataMode, persistenceStatus, privacyOperations = [], asrProvider } = store.getState();

  const activeAsr = asrProvider || "Mock Batchalign2 ASR Provider (Interactive Delay)";

  return `
    ${renderSafetyBanner()}
    ${renderEnvironmentModeBanner(store.getState())}
    
    <div style="display: grid; grid-template-columns: 1fr; gap: 20px; align-items: start;">
      
      <!-- Left side: Profile & Persistence -->
      <div style="display: flex; flex-direction: column; gap: 20px;">
        
        <!-- Clinician Profile Editor -->
        <section class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-lg);">
          <div class="panel-title" style="margin-bottom: 16px;">
            <h3>Clinician Profile</h3>
            <span>Edit your workspace credentials and credentials sign-off metadata</span>
          </div>
          <form id="profile-edit-form" style="display: flex; flex-direction: column; gap: 14px; max-width: 480px;">
            <label style="display: flex; flex-direction: column; gap: 4px; font-weight: 600;">
              Clinician Name
              <input type="text" class="glass-input" id="profile-name" required value="${currentUser?.name || ""}" placeholder="Jane Smith" />
            </label>
            <label style="display: flex; flex-direction: column; gap: 4px; font-weight: 600;">
              Credentials
              <input type="text" class="glass-input" id="profile-credentials" required value="${currentUser?.credentials || ""}" placeholder="M.S., CCC-SLP" />
            </label>
            <label style="display: flex; flex-direction: column; gap: 4px; font-weight: 600;">
              Organization
              <input type="text" class="glass-input" id="profile-org" required value="${currentUser?.organization || ""}" placeholder="Mock Speech Clinic" />
            </label>
            <button class="primary-action" type="submit" style="margin-top: 6px; font-weight: 600; max-width: 150px;">Save Profile</button>
          </form>
        </section>

        <!-- System Configuration Settings -->
        <section class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-lg);">
          <div class="panel-title" style="margin-bottom: 16px;">
            <h3>Workspace Configurations</h3>
            <span>Tweak pipeline and data store parameters</span>
          </div>
          <div style="display: grid; gap: 16px; max-width: 480px;">
            <label style="display: flex; flex-direction: column; gap: 4px; font-weight: 600;">
              Data Mode & Persistence Boundary
              <select id="settings-data-mode" class="glass-input" style="padding: 8px;">
                <option value="mock" ${dataMode === "mock" ? "selected" : ""}>Mock Mode (In-memory + local storage auto-save)</option>
                <option value="localStorage" ${dataMode === "localStorage" ? "selected" : ""}>Client LocalStorage Mode</option>
              </select>
              <span style="font-size: 0.72rem; color: var(--muted); font-weight: 400; margin-top: 2px;">
                Current Hydration Status: <strong>${persistenceStatus}</strong>
              </span>
            </label>

            <label style="display: flex; flex-direction: column; gap: 4px; font-weight: 600;">
              ASR Provider Engine
              <select id="settings-asr-engine" class="glass-input" style="padding: 8px;">
                <option value="mock_batchalign" ${activeAsr.startsWith("Mock") ? "selected" : ""}>Mock Batchalign2 ASR Provider (Interactive Delay)</option>
                <option value="openai_whisper" ${activeAsr === "openai_whisper" ? "selected" : ""}>OpenAI Whisper API (Offline/Future Integration)</option>
                <option value="rev_ai" ${activeAsr === "rev_ai" ? "selected" : ""}>Rev.AI Speech-to-Text (Offline/Future Integration)</option>
              </select>
            </label>

            <div style="padding-top: 10px; border-top: 1px solid var(--line); display: flex; flex-direction: column; gap: 10px;">
              <strong style="font-size: 0.85rem; color: var(--ink);">Metadata Properties:</strong>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.82rem; color: var(--muted);">
                <span>Auth Mode: <strong>${AUTH_MODE}</strong></span>
                <span>Auth Status: <strong>${authStatus}</strong></span>
                <span>User Role: <strong>${currentUser?.role || ""}</strong></span>
                <span>File Storage: <strong>${FILE_STORAGE_MODE}</strong></span>
                <span>Audio Process: <strong>${PROCESSING_MODE}</strong></span>
              </div>
            </div>

            <div style="padding-top: 14px; border-top: 1px dashed var(--line); display: flex; flex-direction: column; gap: 10px;">
              <strong style="font-size: 0.85rem; color: var(--destructive);">Danger Zone</strong>
              <p style="font-size: 0.76rem; color: var(--muted); margin: 0;">Resetting will clear all user-created cases, uploaded audio details, and transcript edits from your browser local storage.</p>
              <button class="secondary-action" id="reset-database-btn" style="border: 1px solid var(--destructive); color: var(--destructive); background: var(--destructive-soft); font-weight: 600; max-width: 220px; min-height: 38px;">
                Reset Demo Database
              </button>
            </div>
          </div>
        </section>
      </div>

      <!-- Right side: Privacy Operations Log -->
      <section class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-lg);">
        <div class="panel-title" style="margin-bottom: 12px;">
          <h3>Privacy Operations</h3>
          <span>export, withdrawal, and deletion request queue</span>
        </div>
        <p style="font-size: 0.85rem; color: var(--muted); max-width: 720px; margin-bottom: 16px;">
          Privacy operations are requests that must be reviewed according to clinic policy. Case deletion requests do not erase audit logs.
        </p>
        <div style="display: grid; gap: 8px;">
          ${privacyOperations
            .slice()
            .reverse()
            .map(
              operation => `
              <div style="padding: 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface);">
                <strong style="font-size: 0.85rem; color: var(--ink);">${operation.operation_type.replaceAll("_", " ")}</strong>
                <div style="font-size: 0.76rem; color: var(--muted); margin-top: 4px;">
                  ${operation.operation_id} · case ${operation.case_id} · status <span class="status-pill status-good" style="font-size: 0.65rem; padding: 1px 6px;">${operation.status}</span> · ${new Date(operation.created_at).toLocaleString()}
                </div>
              </div>
            `
            )
            .join("") || '<p class="empty-state">No privacy operation requests recorded yet.</p>'}
        </div>
      </section>
    </div>
  `;
}

export function bindSettings(navigate) {
  // Bind profile save
  const profileForm = document.getElementById("profile-edit-form");
  if (profileForm) {
    profileForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const name = document.getElementById("profile-name").value.trim();
      const credentials = document.getElementById("profile-credentials").value.trim();
      const organization = document.getElementById("profile-org").value.trim();

      const state = store.getState();
      const nextUser = {
        ...state.currentUser,
        name,
        credentials,
        organization
      };
      
      store.setState({ currentUser: nextUser });
      alert("Clinician profile updated successfully! Changes applied to active workspace session sign-offs.");
      navigate("settings");
    });
  }

  // Bind configurations
  const dataModeSelect = document.getElementById("settings-data-mode");
  if (dataModeSelect) {
    dataModeSelect.addEventListener("change", (e) => {
      const mode = e.target.value;
      store.setState({ dataMode: mode });
      alert(`Data Mode switched to ${mode}. Hydration state updated.`);
      window.location.reload();
    });
  }

  const asrEngineSelect = document.getElementById("settings-asr-engine");
  if (asrEngineSelect) {
    asrEngineSelect.addEventListener("change", (e) => {
      const engine = e.target.options[e.target.selectedIndex].text;
      store.setState({ asrProvider: engine });
      alert(`ASR Provider Engine set to: ${engine}`);
      navigate("settings");
    });
  }

  // Reset database
  const resetBtn = document.getElementById("reset-database-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      if (confirm("Are you sure you want to restore the prototype database to its original seed configuration? All custom cases, sessions, and edits will be permanently deleted from your browser.")) {
        localStorage.removeItem("asdProject.therapistClinician.repository.v1.mock");
        localStorage.removeItem("asdProject.therapistClinician.repository.v1.localStorage");
        alert("Local cache cleared. Restoring demo database...");
        window.location.reload();
      }
    });
  }
}
