import { ACTIVE_RUNTIME_MODE, AUTH_MODE, DATA_MODE, FILE_STORAGE_MODE, MOCK_MODE, PROCESSING_MODE, RUNTIME_MODES } from "../constants.js";
import { escapeHtml } from "@shared/utils/html.js";
import { iconSvg } from "./icons.js";

export function isSampleDataMode({ dataMode = DATA_MODE, authMode = AUTH_MODE, processingMode = PROCESSING_MODE } = {}) {
  return ACTIVE_RUNTIME_MODE !== RUNTIME_MODES.PILOT_BACKEND || MOCK_MODE || ["mock", "localStorage", "database_placeholder"].includes(dataMode) || ["mock", "local_dev"].includes(authMode) || processingMode === "mock";
}

export function renderEnvironmentModeBanner(state = {}) {
  return `
    <div class="environment-mode-banner-subtle" style="display: none;" aria-hidden="true">
      Sample / mock data mode
      Demo accounts, seeded cases, mock/local development records, or mock processing may be active. Do not enter real child identifiers.
    </div>
  `;
}
