import { store } from "../store/state.js";
import { getVisibleCases, createCase, toggleStarCase } from "../services/case-service.js";
import { getVisibleSessions } from "../services/session-service.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { renderConsentWarning, renderPrivacyStatusTags } from "../components/privacy-status.js";

export function renderCases() {
  const state = store.getState();
  const allCases = getVisibleCases();
  const sessions = getVisibleSessions();

  // Load active filters from state
  const searchQuery = state.caseSearchQuery || "";
  const filterAgeBand = state.caseFilterAge || "all";
  const filterStatus = state.caseFilterStatus || "all";
  const viewLayout = state.casesViewLayout || "card"; // 'card' or 'table'

  // Apply filtering
  const filteredCases = allCases.filter(c => {
    // Search filter
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const codeMatch = c.anonymized_child_code?.toLowerCase().includes(q);
      const nameMatch = c.display_label?.toLowerCase().includes(q);
      if (!codeMatch && !nameMatch) return false;
    }

    // Age filter
    if (filterAgeBand !== "all") {
      const age = c.age_months;
      if (filterAgeBand === "toddler" && (age < 12 || age > 36)) return false;
      if (filterAgeBand === "preschool" && (age < 37 || age > 60)) return false;
      if (filterAgeBand === "school" && age < 61) return false;
    }

    // Progress status filter
    if (filterStatus !== "all") {
      // Mock categories mapped to score levels or mock property values
      const progressState = c.latest_score < 0.40 ? "improving" : (c.latest_score < 0.67 ? "stable" : "needs_review");
      if (filterStatus !== progressState) return false;
    }

    return true;
  });

  // Render filter bar HTML
  const filterBarHtml = `
    <div class="glass-card" style="padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-md); display: flex; gap: 14px; align-items: center; flex-wrap: wrap; justify-content: space-between;">
      <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center; flex: 1; min-width: 300px;">
        <input type="text" id="case-search" class="glass-input" placeholder="Search case or child code..." value="${searchQuery}" style="max-width: 250px; min-height: 38px; padding: 6px 12px;" />
        
        <select id="filter-age" class="glass-input" style="max-width: 160px; min-height: 38px; padding: 6px;">
          <option value="all" ${filterAgeBand === "all" ? "selected" : ""}>All Ages</option>
          <option value="toddler" ${filterAgeBand === "toddler" ? "selected" : ""}>Toddler (12-36 mo)</option>
          <option value="preschool" ${filterAgeBand === "preschool" ? "selected" : ""}>Preschool (37-60 mo)</option>
          <option value="school" ${filterAgeBand === "school" ? "selected" : ""}>School Age (61+ mo)</option>
        </select>

        <select id="filter-status" class="glass-input" style="max-width: 160px; min-height: 38px; padding: 6px;">
          <option value="all" ${filterStatus === "all" ? "selected" : ""}>All Progress States</option>
          <option value="improving" ${filterStatus === "improving" ? "selected" : ""}>Improving</option>
          <option value="stable" ${filterStatus === "stable" ? "selected" : ""}>Stable</option>
          <option value="needs_review" ${filterStatus === "needs_review" ? "selected" : ""}>Needs Review</option>
        </select>
      </div>

      <!-- Layout toggle buttons -->
      <div style="display: flex; gap: 6px;">
        <button id="layout-card-btn" class="secondary-action ${viewLayout === "card" ? "active" : ""}" style="min-height: 38px; padding: 6px 12px; font-size: 0.85rem; font-weight: 600; background: ${viewLayout === "card" ? "var(--primary-soft)" : ""}; color: ${viewLayout === "card" ? "var(--primary)" : ""};">Card</button>
        <button id="layout-table-btn" class="secondary-action ${viewLayout === "table" ? "active" : ""}" style="min-height: 38px; padding: 6px 12px; font-size: 0.85rem; font-weight: 600; background: ${viewLayout === "table" ? "var(--primary-soft)" : ""}; color: ${viewLayout === "table" ? "var(--primary)" : ""};">Table</button>
      </div>
    </div>
  `;

  // Case Grid Card rendering
  const cardsHtml = filteredCases.map(c => {
    const caseSessions = sessions.filter(s => s.case_id === c.case_id);
    const scoreVal = c.latest_score;
    // Map score levels to clinical progress badges safely
    const progressLabel = scoreVal < 0.40 ? "Improving" : (scoreVal < 0.67 ? "Stable" : "Needs Review");
    const badgeColor = scoreVal < 0.40 ? "var(--mint)" : (scoreVal < 0.67 ? "var(--medical-blue)" : "var(--amber-pending)");
    const badgeBg = scoreVal < 0.40 ? "var(--mint-soft)" : (scoreVal < 0.67 ? "var(--medical-blue-soft)" : "var(--amber-soft)");
    
    // Check if review is pending
    const needsReview = caseSessions.some(s => s.therapist_review_status === "awaiting_review");

    return `
      <div class="case-card glass-card" style="padding: 18px; border: 1px solid var(--line); border-radius: var(--radius-lg); display: flex; flex-direction: column; gap: 12px; position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: start;">
          <div>
            <h4 style="margin: 0; font-size: 1.05rem; color: var(--ink);">${c.display_label}</h4>
            <span style="font-size: 0.75rem; color: var(--muted); font-weight: 500;">${c.anonymized_child_code}</span>
          </div>
          <button class="case-star-btn" data-case-id="${c.case_id}" style="border: none; background: transparent; cursor: pointer; color: ${c.starred ? "var(--warning)" : "var(--muted)"};">
            ${c.starred ? "★" : "☆"}
          </button>
        </div>

        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px;">
          <span class="status-pill" style="font-size: 0.7rem; background: ${badgeBg}; color: ${badgeColor}; font-weight: 700;">${progressLabel}</span>
          ${needsReview ? `<span class="status-pill" style="font-size: 0.7rem; background: var(--amber-soft); color: var(--amber-pending); font-weight: 700;">AI Review Pending</span>` : ""}
          <span class="status-pill" style="font-size: 0.7rem; background: var(--lavender); color: var(--muted);">${c.age_months} mo</span>
        </div>

        <div style="font-size: 0.8rem; color: var(--muted); display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin: 4px 0;">
          <span>Sessions: <strong>${caseSessions.length}</strong></span>
          <span>Sex: <strong style="text-transform: capitalize;">${c.sex}</strong></span>
          <span class="full-span" style="grid-column: 1 / -1;">Status: <strong style="color: var(--ink); font-weight: 600;">${c.external_clinical_status.replaceAll("_", " ")}</strong></span>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--slate); padding-top: 10px; margin-top: 4px;">
          <div style="display: flex; gap: 4px;">
            ${renderPrivacyStatusTags(c)}
          </div>
          <button class="small-action open-case-detail-btn" data-case-id="${c.case_id}" style="min-height: 32px; font-size: 0.8rem; padding: 4px 12px; font-weight: 600;">Open Case</button>
        </div>
      </div>
    `;
  }).join("");

  // Table layout rendering
  const tableHtml = `
    <div class="glass-card" style="padding: 0; border: 1px solid var(--line); border-radius: var(--radius-lg); overflow: hidden;">
      <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem;">
        <thead>
          <tr style="background: var(--lavender); border-bottom: 1.5px solid var(--slate); color: var(--ink); font-weight: 600;">
            <th style="padding: 12px 16px;">Child Name</th>
            <th style="padding: 12px 16px;">Code</th>
            <th style="padding: 12px 16px;">Age</th>
            <th style="padding: 12px 16px;">Sessions</th>
            <th style="padding: 12px 16px;">Progress Status</th>
            <th style="padding: 12px 16px;">External Status</th>
            <th style="padding: 12px 16px; text-align: right;">Action</th>
          </tr>
        </thead>
        <tbody>
          ${filteredCases.map(c => {
            const caseSessions = sessions.filter(s => s.case_id === c.case_id);
            const scoreVal = c.latest_score;
            const progressLabel = scoreVal < 0.40 ? "Improving" : (scoreVal < 0.67 ? "Stable" : "Needs Review");
            const badgeColor = scoreVal < 0.40 ? "var(--mint)" : (scoreVal < 0.67 ? "var(--medical-blue)" : "var(--amber-pending)");
            const badgeBg = scoreVal < 0.40 ? "var(--mint-soft)" : (scoreVal < 0.67 ? "var(--medical-blue-soft)" : "var(--amber-soft)");
            return `
              <tr style="border-bottom: 1px solid var(--slate); transition: background-color 0.2s ease;">
                <td style="padding: 12px 16px; font-weight: 600;">${c.display_label}</td>
                <td style="padding: 12px 16px; color: var(--muted);">${c.anonymized_child_code}</td>
                <td style="padding: 12px 16px;">${c.age_months} mo</td>
                <td style="padding: 12px 16px;">${caseSessions.length} sessions</td>
                <td style="padding: 12px 16px;">
                  <span class="status-pill" style="font-size: 0.7rem; background: ${badgeBg}; color: ${badgeColor}; font-weight: 700; padding: 2px 8px; border-radius: 999px;">${progressLabel}</span>
                </td>
                <td style="padding: 12px 16px; text-transform: capitalize;">${c.external_clinical_status.replaceAll("_", " ")}</td>
                <td style="padding: 12px 16px; text-align: right;">
                  <button class="small-action open-case-detail-btn" data-case-id="${c.case_id}" style="min-height: 32px; font-size: 0.8rem; padding: 4px 12px; font-weight: 600;">Open</button>
                </td>
              </tr>
            `;
          }).join("")}
          ${filteredCases.length === 0 ? `<tr><td colspan="7" style="padding: 24px; text-align: center; color: var(--muted);">No matching cases found.</td></tr>` : ""}
        </tbody>
      </table>
    </div>
  `;

  const selectedCase = allCases.find(c => c.case_id === state.selectedCaseId) || allCases[0];
  const consentWarningHtml = selectedCase ? renderConsentWarning(selectedCase) : "";

  return `
    ${renderSafetyBanner()}
    ${consentWarningHtml}
    <div class="cases-page-layout">
      
      <!-- Left Column: Case Search, filters and Caseload grid/table -->
      <div style="display: flex; flex-direction: column; gap: 16px;">
        ${filterBarHtml}
        
        ${viewLayout === "card" 
          ? `<div class="cases-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px;">
              ${cardsHtml}
              ${filteredCases.length === 0 ? `<p class="empty-state" style="grid-column: 1/-1; text-align: center; padding: 32px;">No matching child cases found.</p>` : ""}
             </div>` 
          : tableHtml
        }
      </div>

      <!-- Right Column: Create Case Form -->
      <section class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-lg);">
        <div class="panel-title" style="margin-bottom: 12px;">
          <h3>Create Case File</h3>
          <span style="font-size: 0.75rem; color: var(--muted);">anonymized indicators only</span>
        </div>
        <form id="create-case-form" style="display: flex; flex-direction: column; gap: 14px;">
          <label>Anonymized Child Code
            <input type="text" class="glass-input" id="case-child-code" required placeholder="CHI-X12" style="margin-top: 4px;" />
          </label>
          <label>Age (months)
            <input type="number" class="glass-input" id="case-age" required min="12" max="120" value="48" style="margin-top: 4px;" />
          </label>
          <label>Sex
            <select id="case-sex" class="glass-input" style="margin-top: 4px; padding: 8px;">
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="not_specified">Not Specified</option>
            </select>
          </label>
          <label>Primary Concerns
            <textarea id="case-concerns" class="glass-input" placeholder="Linguistic markers observed..." style="margin-top: 4px; min-height: 60px;"></textarea>
          </label>
          <label>Consent Status
            <select id="case-consent-status" class="glass-input" style="margin-top: 4px; padding: 8px;">
              <option value="granted">Granted</option>
              <option value="pending">Pending</option>
              <option value="not_recorded">Not recorded</option>
              <option value="declined">Declined</option>
            </select>
          </label>
          <label>Therapist Notes
            <textarea id="case-notes" class="glass-input" placeholder="Clinic notes..." style="margin-top: 4px; min-height: 60px;"></textarea>
          </label>
          <button class="primary-action" type="submit" style="margin-top: 6px; font-weight: 600;">Create Case</button>
        </form>
      </section>
    </div>
  `;
}

export function bindCases(navigate) {
  // Bind create form
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
        navigate("cases");
      } catch (err) {
        alert(`Failed to create case: ${err.message || err}`);
      }
    });
  }

  // Search input binding
  const searchInput = document.getElementById("case-search");
  if (searchInput) {
    searchInput.addEventListener("input", e => {
      store.setState({ caseSearchQuery: e.target.value }, { persist: false });
      navigate("cases");
    });
  }

  // Filter bindings
  const filterAge = document.getElementById("filter-age");
  if (filterAge) {
    filterAge.addEventListener("change", e => {
      store.setState({ caseFilterAge: e.target.value }, { persist: false });
      navigate("cases");
    });
  }

  const filterStatus = document.getElementById("filter-status");
  if (filterStatus) {
    filterStatus.addEventListener("change", e => {
      store.setState({ caseFilterStatus: e.target.value }, { persist: false });
      navigate("cases");
    });
  }

  // Layout view bindings
  const cardBtn = document.getElementById("layout-card-btn");
  if (cardBtn) {
    cardBtn.addEventListener("click", () => {
      store.setState({ casesViewLayout: "card" });
      navigate("cases");
    });
  }

  const tableBtn = document.getElementById("layout-table-btn");
  if (tableBtn) {
    tableBtn.addEventListener("click", () => {
      store.setState({ casesViewLayout: "table" });
      navigate("cases");
    });
  }

  // Star binding
  const starBtns = document.querySelectorAll(".case-star-btn");
  starBtns.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const caseId = btn.getAttribute("data-case-id");
      toggleStarCase(caseId);
      navigate("cases");
    });
  });

  // Open detail binding
  const openBtns = document.querySelectorAll(".open-case-detail-btn");
  openBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const caseId = btn.getAttribute("data-case-id");
      store.setState({ selectedCaseId: caseId, caseDetailTab: "overview" });
      navigate("case_detail");
    });
  });
}
