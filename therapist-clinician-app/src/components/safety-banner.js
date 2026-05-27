import { SAFETY_DISCLAIMER } from "../constants.js";

export function renderSafetyBanner() {
  return `
    <div class="safety-banner" style="margin-bottom: 16px;">
      <span style="font-weight: 900; margin-right: 6px;">⚠️ AI-Assisted Clinical Support:</span>
      <span>${SAFETY_DISCLAIMER}</span>
    </div>
  `;
}
