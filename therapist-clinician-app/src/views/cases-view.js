import { store } from "../store/state.js";
import { getVisibleCases, createCase, toggleStarCase } from "../services/case-service.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { renderConsentWarning, renderPrivacyStatusTags } from "../components/privacy-status.js";

export function renderCases() {
  const casesList = getVisibleCases();

  return `
    ${renderSafetyBanner()}
    <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 20px;">
      <section class="panel" style="padding: 16px;">
        <div class="panel-title">
          <h3>Anonymized Child Cases</h3>
          <span>total cases: ${casesList.length}</span>
        </div>
        <div style="display: grid; gap: 10px;">
          ${casesList
            .map(
              c => `
            <div style="padding: 12px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--shell); display: flex; justify-content: space-between; align-items: center;">
              <div>
                <strong>${c.display_label} (${c.anonymized_child_code})</strong>
                <div style="font-size: 0.8rem; color: var(--muted); margin-top: 4px;">
                  Case ID: ${c.case_id} · Age: ${c.age_months} months · Sex: ${c.sex} · Concern Score: ${c.latest_score.toFixed(2)}
                </div>
                <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px;">
                  ${renderPrivacyStatusTags(c)}
                </div>
                ${renderConsentWarning(c)}
              </div>
              <div style="display: flex; gap: 8px;">
                <button class="icon-button case-star-btn" data-case-id="${c.case_id}">
                  ${c.starred ? "★" : "☆"}
                </button>
                <button class="small-action select-case-btn" data-case-id="${c.case_id}">Select</button>
              </div>
            </div>
          `
            )
            .join("")}
        </div>
      </section>

      <section class="panel" style="padding: 16px;">
        <div class="panel-title">
          <h3>Create case</h3>
          <span>anonymized metrics only</span>
        </div>
        <form id="create-case-form" class="form-grid" style="display: grid; gap: 12px; grid-template-columns: 1fr;">
          <label>Anonymized Child Code (e.g. CHI-X99)
            <input type="text" id="case-child-code" required placeholder="CHI-A03" />
          </label>
          <label>Age (months)
            <input type="number" id="case-age" required min="12" max="120" value="48" />
          </label>
          <label>Sex
            <select id="case-sex">
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="not_specified">Not Specified</option>
            </select>
          </label>
          <label>Primary Concerns
            <textarea id="case-concerns" placeholder="Describe clinical communication markers observed..."></textarea>
          </label>
          <label>Consent Status
            <select id="case-consent-status">
              <option value="pending">Pending</option>
              <option value="granted">Granted</option>
              <option value="not_recorded">Not recorded</option>
              <option value="declined">Declined</option>
            </select>
          </label>
          <label>Therapist Notes
            <textarea id="case-notes" placeholder="Internal notes..."></textarea>
          </label>
          <button class="primary-action" type="submit">Create case</button>
        </form>
      </section>
    </div>
  `;
}

export function bindCases(navigate) {
  const form = document.getElementById("create-case-form");
  if (form) {
    form.addEventListener("submit", e => {
      e.preventDefault();
      const childCode = document.getElementById("case-child-code").value;
      const age = document.getElementById("case-age").value;
      const sex = document.getElementById("case-sex").value;
      const concerns = document.getElementById("case-concerns").value;
      const notes = document.getElementById("case-notes").value;
      const consentStatus = document.getElementById("case-consent-status").value;

      createCase({
        anonymized_child_code: childCode,
        age_months: age,
        sex,
        primary_concerns: concerns,
        consent_status: consentStatus,
        anonymization_status: "anonymized",
        notes
      });

      navigate("dashboard");
    });
  }

  // Star and select handlers
  const starBtns = document.querySelectorAll(".case-star-btn");
  starBtns.forEach(btn => {
    btn.addEventListener("click", () => {
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
}
