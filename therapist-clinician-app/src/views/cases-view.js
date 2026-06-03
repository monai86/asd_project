import { store } from "../store/state.js";
import { getVisibleCases, createCase, toggleStarCase } from "../services/case-service.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { renderConsentWarning, renderPrivacyStatusTags } from "../components/privacy-status.js";
import {
  requestCaseDeletion,
  requestCasePrivacyExport,
  requestConsentWithdrawal
} from "../services/privacy-operations-service.js";

export function renderCases() {
  const casesList = getVisibleCases();

  return `
    ${renderSafetyBanner()}
    <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 20px;">
      <section class="glass-card" style="padding: 20px; display: flex; flex-direction: column; gap: 16px;">
        <div class="panel-title" style="margin-bottom: 0;">
          <h3>Anonymized Child Cases</h3>
          <span>total cases: ${casesList.length}</span>
        </div>
        <div class="cases-grid">
          ${casesList
            .map(
              c => {
                const scoreColor = c.latest_score < 0.40 ? "var(--primary)" : (c.latest_score < 0.67 ? "var(--warning)" : "var(--destructive)");
                return `
            <div class="case-card ${c.starred ? "starred" : ""}">
              <div class="case-card-header">
                <div class="case-card-title-group">
                  <div class="case-avatar">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="case-avatar-icon"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  </div>
                  <div>
                    <h4 class="case-title">${c.display_label}</h4>
                    <span class="case-code">${c.anonymized_child_code}</span>
                  </div>
                </div>
                <button class="case-star-btn ${c.starred ? "active" : ""}" data-case-id="${c.case_id}" title="${c.starred ? "Unstar case" : "Star case"}">
                  ${c.starred ? `
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="var(--warning)" stroke="var(--warning)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                  ` : `
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                  `}
                </button>
              </div>

              <div class="case-metrics">
                <div class="metric-item">
                  <span class="metric-label">Age</span>
                  <span class="metric-value">${c.age_months} mo</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">Sex</span>
                  <span class="metric-value" style="text-transform: capitalize;">${c.sex === "not_specified" ? "N/A" : c.sex}</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">Concern</span>
                  <span class="metric-value score-badge" style="color: ${scoreColor};">
                    ${c.latest_score.toFixed(2)}
                  </span>
                </div>
              </div>

              <div class="case-privacy-section">
                <div class="privacy-tags-container">
                  ${renderPrivacyStatusTags(c)}
                </div>
                ${renderConsentWarning(c)}
                ${c.privacy_operation_status ? `
                  <div class="privacy-ops-alert">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px; flex-shrink: 0;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    Privacy: ${c.privacy_operation_status.replaceAll("_", " ")}
                  </div>
                ` : ""}
              </div>

              <div class="case-card-actions">
                <button class="small-action select-case-btn" data-case-id="${c.case_id}">Select Case</button>
                <div class="privacy-popover-container">
                  <button class="secondary-action privacy-popover-trigger" data-case-id="${c.case_id}" title="Privacy & PDPA Settings">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                  </button>
                  <div class="privacy-dropdown-menu" id="dropdown-${c.case_id}">
                    <div class="dropdown-header">PDPA Operations</div>
                    <button class="dropdown-item privacy-export-btn" data-case-id="${c.case_id}">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                      Export Case Data
                    </button>
                    <button class="dropdown-item privacy-withdraw-btn" data-case-id="${c.case_id}">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                      Withdraw Consent
                    </button>
                    <button class="dropdown-item privacy-delete-btn destructive" data-case-id="${c.case_id}">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                      Request Deletion
                    </button>
                  </div>
                </div>
              </div>
            </div>
          `;
              }
            )
            .join("")}
        </div>
      </section>

      <section class="glass-card" style="padding: 20px;">
        <div class="panel-title">
          <h3>Create Case</h3>
          <span>anonymized metrics only</span>
        </div>
        <form id="create-case-form" class="form-grid" style="display: grid; gap: 16px; grid-template-columns: 1fr;">
          <label>Anonymized Child Code
            <span style="font-size: 0.75rem; color: var(--muted); display: block; margin-top: 2px; font-weight: normal;">(e.g., CHI-X99. Real names are strictly prohibited.)</span>
            <input type="text" class="glass-input" id="case-child-code" required placeholder="CHI-A03" style="margin-top: 6px;" />
          </label>
          <label>Age (months)
            <input type="number" class="glass-input" id="case-age" required min="12" max="120" value="48" style="margin-top: 6px;" />
          </label>
          <label>Sex
            <select id="case-sex" class="glass-input" style="margin-top: 6px;">
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="not_specified">Not Specified</option>
            </select>
          </label>
          <label>Primary Concerns
            <textarea id="case-concerns" class="glass-input" placeholder="Describe clinical communication markers observed..." style="margin-top: 6px; min-height: 80px;"></textarea>
          </label>
          <label>Consent Status
            <select id="case-consent-status" class="glass-input" style="margin-top: 6px;">
              <option value="pending">Pending</option>
              <option value="granted">Granted</option>
              <option value="not_recorded">Not recorded</option>
              <option value="declined">Declined</option>
            </select>
          </label>
          <label>Therapist Notes
            <textarea id="case-notes" class="glass-input" placeholder="Internal notes..." style="margin-top: 6px; min-height: 80px;"></textarea>
          </label>
          <button class="primary-action" type="submit" style="margin-top: 8px;">Create case</button>
        </form>
      </section>
    </div>
  `;
}

export function bindCases(navigate) {
  const form = document.getElementById("create-case-form");
  if (form) {
    form.addEventListener("submit", async e => {
      e.preventDefault();
      const childCode = document.getElementById("case-child-code").value.trim();
      
      const codePattern = /^[A-Z0-9\-]+$/i;
      if (!codePattern.test(childCode)) {
        alert("Error: Anonymized Child Code must only contain alphanumeric characters and hyphens (e.g., CHI-A01). Real names or identifiers are strictly prohibited.");
        return;
      }

      const age = document.getElementById("case-age").value;
      const sex = document.getElementById("case-sex").value;
      const concerns = document.getElementById("case-concerns").value;
      const notes = document.getElementById("case-notes").value;
      const consentStatus = document.getElementById("case-consent-status").value;

      try {
        await createCase({
          anonymized_child_code: childCode,
          age_months: age,
          sex,
          primary_concerns: concerns,
          consent_status: consentStatus,
          anonymization_status: "anonymized",
          notes
        });
        navigate("dashboard");
      } catch (err) {
        alert(`Failed to create case: ${err.message || err}`);
      }
    });
  }

  // Star and select handlers
  const starBtns = document.querySelectorAll(".case-star-btn");
  starBtns.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const caseId = btn.getAttribute("data-case-id");
      toggleStarCase(caseId);
      navigate("cases");
    });
  });

  const selectBtns = document.querySelectorAll(".select-case-btn");
  selectBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const caseId = btn.getAttribute("data-case-id");
      store.setState({ selectedCaseId: caseId });
      navigate("dashboard");
    });
  });

  // Privacy dropdown popover handlers
  const triggers = document.querySelectorAll(".privacy-popover-trigger");
  triggers.forEach(trigger => {
    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      const caseId = trigger.getAttribute("data-case-id");
      const dropdown = document.getElementById(`dropdown-${caseId}`);
      document.querySelectorAll(".privacy-dropdown-menu").forEach(d => {
        if (d !== dropdown) d.classList.remove("show");
      });
      dropdown.classList.toggle("show");
    });
  });

  // Close dropdowns on outer clicks
  document.addEventListener("click", () => {
    document.querySelectorAll(".privacy-dropdown-menu").forEach(d => {
      d.classList.remove("show");
    });
  });

  document.querySelectorAll(".privacy-export-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const caseId = btn.getAttribute("data-case-id");
      const { operation } = requestCasePrivacyExport(caseId);
      alert(`Privacy export request recorded: ${operation.operation_id}`);
      navigate("cases");
    });
  });

  document.querySelectorAll(".privacy-withdraw-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const caseId = btn.getAttribute("data-case-id");
      requestConsentWithdrawal(caseId, "Requested from case privacy controls.");
      navigate("cases");
    });
  });

  document.querySelectorAll(".privacy-delete-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const caseId = btn.getAttribute("data-case-id");
      requestCaseDeletion(caseId, "Requested from case privacy controls.");
      navigate("cases");
    });
  });
}
