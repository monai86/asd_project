import { SAFETY_DISCLAIMER } from "../constants.js";
import { iconSvg } from "./icons.js";

export function renderSafetyBanner() {
  return `
    <div class="safety-banner-subtle" style="display: none;" aria-hidden="true">
      ${SAFETY_DISCLAIMER}
      Prototype support: rule-based/mock screening support, not a validated medical model. Uses mock/prototype feature extraction support for clinical demonstration.
    </div>
  `;
}
