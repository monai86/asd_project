import { AUTH_MODE, DATA_MODE, FILE_STORAGE_MODE, MOCK_MODE, PROCESSING_MODE } from "../constants.js";
import { escapeHtml } from "@shared/utils/html.js";

export function isSampleDataMode({ dataMode = DATA_MODE, authMode = AUTH_MODE, processingMode = PROCESSING_MODE } = {}) {
  return MOCK_MODE || ["mock", "localStorage", "database_placeholder"].includes(dataMode) || ["mock", "local_dev"].includes(authMode) || processingMode === "mock";
}

export function renderEnvironmentModeBanner(state = {}) {
  const sampleMode = isSampleDataMode({
    dataMode: state.dataMode,
    authMode: AUTH_MODE,
    processingMode: PROCESSING_MODE
  });
  const label = sampleMode ? "Sample / mock data mode" : "Controlled clinical mode";
  const detail = sampleMode
    ? "Demo accounts, seeded cases, mock/local development records, or mock processing may be active. Do not enter real child identifiers."
    : "Real authentication, storage, processing, and ownership controls are expected to be active.";

  return `
    <div class="environment-mode-banner ${sampleMode ? "sample-mode" : "real-mode"}" role="status">
      <strong>${label}</strong>
      <span>${escapeHtml(detail)}</span>
      <small>data=${escapeHtml(state.dataMode || DATA_MODE)} · auth=${escapeHtml(AUTH_MODE)} · storage=${escapeHtml(FILE_STORAGE_MODE)} · processing=${escapeHtml(PROCESSING_MODE)}</small>
    </div>
  `;
}
