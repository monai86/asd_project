import { escapeHtml } from "@shared/utils/html.js";

export function labelStatus(value) {
  return String(value || "not_recorded").replaceAll("_", " ");
}

export function isConsentMissing(caseItem) {
  return !caseItem?.consent_status || ["not_recorded", "pending", "declined"].includes(caseItem.consent_status);
}

export function renderPrivacyStatusTags(caseItem) {
  const consentStatus = caseItem?.consent_status || "not_recorded";
  const anonymizationStatus = caseItem?.anonymization_status || "needs_review";
  const consentClass = consentStatus === "granted" ? "status-good" : "status-warn";
  const anonymizationClass = anonymizationStatus === "anonymized" ? "status-good" : "status-warn";

  return `
    <span class="mini-tag status-pill ${consentClass}">Consent: ${escapeHtml(labelStatus(consentStatus))}</span>
    <span class="mini-tag status-pill ${anonymizationClass}">Anonymization: ${escapeHtml(labelStatus(anonymizationStatus))}</span>
  `;
}

export function renderConsentWarning(caseItem) {
  if (!isConsentMissing(caseItem)) return "";
  return `
    <div class="status-pill status-warn" style="display: inline-flex; margin-top: 8px;">
      Consent status needs review before real clinical upload or interpretation.
    </div>
  `;
}
