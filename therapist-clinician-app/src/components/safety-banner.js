import { SAFETY_DISCLAIMER } from "../constants.js";
import { iconSvg } from "./icons.js";

export function renderSafetyBanner() {
  return `
    <div class="safety-banner clinical-status-banner" role="note" aria-label="Clinical decision-support notice">
      <span class="status-icon" aria-hidden="true">${iconSvg.shield}</span>
      <span>
        <strong>AI-assisted clinical support</strong>
        <span>${SAFETY_DISCLAIMER}</span>
      </span>
    </div>
  `;
}
