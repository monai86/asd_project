# Speech Therapist Web App Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the outer application shell and Therapist Dashboard view of the speech therapist web application into a clean, modern, and unified medical grid dashboard.

**Architecture:** 
1. Modify `styles.css` to remove navigation redundancy, polish active sidebar states, and implement a high-density, 3-tier modular grid system.
2. Refactor `app.js` to remove the redundant horizontal `desktop-header` on desktop view, relying solely on the sticky Left Sidebar for navigation.
3. Update `dashboard-view.js` to render metrics at the top, a split patient context/speech features/charts tier in the middle, and work queues/collapsible activity logs at the bottom.

**Tech Stack:** Vanilla HTML5, CSS3 Custom Properties (OKLCH color system, Backdrop filter blurs), Vanilla JavaScript.

---

## 1. Shell & Dashboard Layout Mapping

We will modify:
*   `therapist-clinician-app/src/styles.css`
*   `therapist-clinician-app/src/app.js`
*   `therapist-clinician-app/src/views/dashboard-view.js`

---

## Proposed Changes

### Task 1: CSS Grid & Aesthetic Polish

**Files:**
*   Modify: `therapist-clinician-app/src/styles.css`

- [ ] **Step 1: Hide redundant desktop header and polish Sidebar layout styles**
  Replace `.desktop-header` block to hide it on desktop, and update active state highlight styling.

  Target:
  ```css
  .desktop-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 34px;
    background: var(--neutral-glass);
    border-bottom: 1px solid var(--line);
    backdrop-filter: var(--backdrop-blur);
    -webkit-backdrop-filter: var(--backdrop-blur);
  }
  ```

  Replacement:
  ```css
  .desktop-header {
    display: none; /* Removed duplicate header navigation on desktop */
  }
  ```

- [ ] **Step 2: Polish active navigation menu items**
  Add a vertical Crimson Rose indicator line on active items, keeping content aligned without layout shifts.

  Target:
  ```css
  .nav-item.active,
  .nav-item:hover {
    background: rgba(20, 184, 166, 0.08);
    color: var(--primary);
    border-color: rgba(20, 184, 166, 0.15);
  }
  ```

  Replacement:
  ```css
  .nav-item.active {
    background: var(--primary-soft);
    color: var(--primary);
    border-left: 3px solid var(--primary);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
  }
  .nav-item:not(.active):hover {
    background: rgba(225, 29, 72, 0.04);
    color: var(--primary);
  }
  ```

- [ ] **Step 3: Define 3-Tier Grid Layout Classes in CSS**
  Add specific classes for the new grid layout at the end of `styles.css`.

  Target: Add to the end of the file.
  ```css
  /* End of file */
  ```

  Replacement:
  ```css
  /* ============================================================================
     3-Tier Modular Grid Dashboard Styles (Crimson Oasis Refined)
     ============================================================================ */
  .dashboard-tier2-grid {
    display: grid;
    grid-template-columns: 1.2fr 0.8fr;
    gap: 18px;
    margin-top: 18px;
    align-items: start;
  }

  .dashboard-tier3-grid {
    display: grid;
    grid-template-columns: 1.35fr 0.65fr;
    gap: 18px;
    margin-top: 18px;
    align-items: start;
  }

  .screening-panel {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .activity-timeline {
    max-height: 380px;
    overflow-y: auto;
    padding-right: 6px;
  }

  /* Custom thin scrollbar for timeline QA & timeline logs */
  .transcript-view-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .transcript-view-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .transcript-view-scrollbar::-webkit-scrollbar-thumb {
    background: var(--line-dark);
    border-radius: 3px;
  }
  .transcript-view-scrollbar::-webkit-scrollbar-thumb:hover {
    background: var(--muted);
  }

  /* Liquid Blobs Hardware Acceleration Boost */
  .liquid-blob {
    will-change: transform;
    transform: translate3d(0,0,0);
  }
  ```

- [ ] **Step 4: Commit CSS styles change**
  Run: `git commit -am "style: unify sidebar menu and define 3-tier modular dashboard grid layouts"`
  Expected: Success

---

### Task 2: Outer Shell Refactor (Remove Top Desktop Header)

**Files:**
*   Modify: `therapist-clinician-app/src/app.js`

- [ ] **Step 1: Remove redundant desktop header HTML scaffolding**
  Locate `root.innerHTML` inside the `render()` function and delete the `<header class="desktop-header">` element. Also remove the redundant `desktop-logout-btn` from the document bindings.

  Target (lines 195-214):
  ```javascript
    <!-- 1. Desktop Top Bar Navigation -->
    <header class="desktop-header">
      <div class="brand">
        <div class="brand-icon">ap</div>
        <div>
          <strong>asd-Project</strong>
          <small>Clinical Workspace</small>
        </div>
      </div>
      <nav>
        ${renderNavItems(state, items)}
      </nav>
      <div class="header-profile">
        <div class="avatar clinician" title="${state.currentUser.name}">${initials(state.currentUser.name)}</div>
        <button class="icon-button logout-btn" id="desktop-logout-btn" title="Log out">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>
        </button>
      </div>
    </header>
  ```

  Replacement:
  ```javascript
    <!-- Desktop Top Header removed in favor of Left Sidebar unified nav -->
  ```

- [ ] **Step 2: Commit shell structural change**
  Run: `git commit -am "feat(app): remove redundant desktop-header navigation"`
  Expected: Success

---

### Task 3: Redesign the Therapist Dashboard View

**Files:**
*   Modify: `therapist-clinician-app/src/views/dashboard-view.js`

- [ ] **Step 1: Rewrite `renderDashboard` layout structure**
  Update the templates for Focus Patient, metric cards, Speech Features table, charts column, work queues, and activity timeline logs. Organise them cleanly into the 3-tier modular grid containers.

  Target: Entire contents of `renderDashboard()` in `dashboard-view.js`
  Replace lines 12 to 333 with the new grid structure layout.

  Code replacement details:
  ```javascript
  export function renderDashboard() {
    const state = store.getState();
    const ownedCases = getVisibleCases();
    const ownedSessions = getVisibleSessions();

    const selectedVisibleCase = ownedCases.find(c => c.case_id === state.selectedCaseId);
    const selectedCaseExists = state.cases.some(c => c.case_id === state.selectedCaseId);
    if (!selectedVisibleCase && selectedCaseExists) {
      return `
        ${renderSafetyBanner()}
        ${renderAccessDenied()}
      `;
    }
    const caseItem = selectedVisibleCase || ownedCases[0];
    if (!caseItem) {
      return `<p class="empty-state">No visible anonymized cases. Please create a case.</p>`;
    }

    const transcriptQueue = ownedSessions.filter(
      s => s.therapist_review_status === "awaiting_review" || s.therapist_review_status === "needs_correction"
    );
    const reportQueue = ownedSessions.filter(s => s.report_status === "pending");

    // Tier 1: Caseload Statistics Row
    const statsRow = `
      <section class="metric-strip">
        <div class="glass-card metric-card">
          <span>Active caseload</span>
          <strong>${ownedCases.length}</strong>
          <small>visible anonymized children</small>
        </div>
        <div class="glass-card metric-card warn">
          <span>Awaiting Review</span>
          <strong style="color: var(--warning);">${transcriptQueue.length}</strong>
          <small>transcripts QA pending</small>
        </div>
        <div class="glass-card metric-card accent" style="background: var(--primary-soft);">
          <span>Pending Reports</span>
          <strong style="color: var(--primary);">${reportQueue.length}</strong>
          <small>ready after clinical QA</small>
        </div>
        <div class="glass-card metric-card">
          <span>Uploaded Files</span>
          <strong>${state.audioFiles.length}</strong>
          <small>metadata only</small>
        </div>
      </section>
    `;

    // Tier 2 Left: Focus Case Details + Features Table
    const focusCaseCard = `
      <div class="glass-card case-hero">
        <div class="case-top">
          <div class="avatar child">CH</div>
          <div>
            <p class="eyebrow">${caseItem.case_id}</p>
            <h3>${caseItem.display_label || caseItem.case_id} (${caseItem.anonymized_child_code})</h3>
            <p class="lead" style="font-size: 0.9rem;">${caseItem.primary_concerns}</p>
          </div>
          <button class="star-button icon-button star" data-case-id="${caseItem.case_id}">
            ${caseItem.starred ? iconSvg.star : iconSvg.starOutline}
          </button>
        </div>
        <div class="tag-row">
          <span class="mini-tag">Age: ${caseItem.age_months}m</span>
          <span class="mini-tag">Sex: ${caseItem.sex}</span>
          ${renderPrivacyStatusTags(caseItem)}
          <span class="mini-tag status-pill status-warn">${caseItem.external_clinical_status.replaceAll("_", " ")}</span>
        </div>
        ${renderConsentWarning(caseItem)}
        <div class="support-box" style="margin-top: 10px;">
          <span>Clinical screening status:</span>
          <strong><i></i>${caseItem.support_level} Support Needed</strong>
        </div>
        <div class="case-stats">
          <div>
            <strong>${ownedSessions.filter(s => s.case_id === caseItem.case_id).length}</strong>
            <span>Sessions</span>
          </div>
          <div>
            <strong>${state.audioFiles.filter(a => a.case_id === caseItem.case_id).length}</strong>
            <span>Audio Uploads</span>
          </div>
          <div>
            <strong>${state.generatedReports.filter(r => r.case_id === caseItem.case_id).length}</strong>
            <span>Reports</span>
          </div>
        </div>
      </div>
    `;

    const featureSummaryCard = `
      <div class="glass-card feature-panel" style="grid-column: span 1;">
        <div class="panel-title">
          <h3>Speech-Language Feature Summary (Latest Session)</h3>
        </div>
        <p class="safety-contract-label">mock/prototype feature extraction support</p>
        <div class="feature-table">
          <div class="feature-head">
            <div>Domain</div>
            <div>Linguistic Feature</div>
            <div>Value</div>
            <div>Trend</div>
          </div>
          <div class="feature-row">
            <div class="feature-domain"><i class="sc"></i><span>Turn-taking</span></div>
            <div>Spontaneous interaction turn count</div>
            <div>0.62 / 1.00</div>
            <div class="trend-badge positive">+0.12</div>
          </div>
          <div class="feature-row">
            <div class="feature-domain"><i></i><span>MLU</span></div>
            <div>Mean length of utterance in words</div>
            <div>3.25 words</div>
            <div class="trend-badge positive">+0.45</div>
          </div>
          <div class="feature-row">
            <div class="feature-domain"><i></i><span>Vocabulary</span></div>
            <div>Type-token ratio (TTR)</div>
            <div>0.38</div>
            <div class="trend-badge positive">+0.05</div>
          </div>
          <div class="feature-row">
            <div class="feature-domain"><i class="rp"></i><span>Phrases</span></div>
            <div>Echolalia / Repetitive words</div>
            <div class="negative">High</div>
            <div class="trend-badge negative">-0.08</div>
          </div>
          <div class="feature-row">
            <div class="feature-domain"><i class="am"></i><span>Pronouns</span></div>
            <div>Referring to self as 'you'</div>
            <div>Occasional</div>
            <div class="trend-badge negative">+0.10</div>
          </div>
        </div>
      </div>
    `;

    // Tier 2 Right: Screening Analytics + Factors
    const screeningPanel = `
      <div class="screening-panel">
        ${renderGaugeChart(caseItem.latest_score)}
        ${renderTrendChart(caseItem.score_trend)}
        <div class="glass-card">
          <div class="panel-title">
            <h3>Screening Concern Factors</h3>
          </div>
          <div class="factor-columns">
            <div>
              <h4 class="negative" style="font-size: 0.8rem; margin-bottom: 6px;">Increasing Concern</h4>
              <ul style="padding-left: 14px; margin: 0; font-size: 0.8rem; line-height: 1.4;">
                <li>Repetitive phrase frequency (+0.23)</li>
                <li>Limited reciprocal response (+0.18)</li>
                <li>Restricted interests (+0.12)</li>
              </ul>
            </div>
            <div>
              <h4 class="positive" style="font-size: 0.8rem; margin-bottom: 6px;">Reducing Concern</h4>
              <ul style="padding-left: 14px; margin: 0; font-size: 0.8rem; line-height: 1.4;">
                <li>Improved turn-taking (-0.15)</li>
                <li>More varied vocabulary (-0.10)</li>
                <li>Better eye contact (-0.08)</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    `;

    // Tier 3 Left: Caseload Work Queues Hub
    const recentCases = ownedCases
      .slice()
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
      .slice(0, 3);

    const queuesCard = `
      <div class="glass-card">
        <div class="panel-title">
          <h3>Caseload Work Queues</h3>
          <span>manage clinical tasks</span>
        </div>
        <div class="queues-grid" style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px;">
          <div>
            <h4 style="font-size: 0.85rem; color: var(--muted); margin-bottom: 8px;">High Review-Priority</h4>
            <div class="queue-list" style="display: grid; gap: 8px;">
              ${recentCases
                .map(
                  c => `
                <div class="queue-item-card glass-card" style="padding: 10px; font-size: 0.8rem;">
                  <strong>${c.display_label}</strong>
                  <span class="status-pill status-warn" style="font-size: 0.7rem; min-height: auto; padding: 2px 6px;">Score: ${c.latest_score.toFixed(2)}</span>
                </div>
              `
                )
                .join("")}
            </div>
          </div>
          <div>
            <h4 style="font-size: 0.85rem; color: var(--muted); margin-bottom: 8px;">Transcript QA Queue</h4>
            <div class="queue-list" style="display: grid; gap: 8px;">
              ${transcriptQueue
                .map(
                  s => `
                <div class="queue-item-card glass-card" style="padding: 10px; font-size: 0.8rem; display: flex; justify-content: space-between; align-items: center;">
                  <span>Session ${s.session_id.replace("SESSION-", "")}</span>
                  <button class="small-action navigate-transcript" data-session-id="${s.session_id}">Review</button>
                </div>
              `
                )
                .join("")}
              ${transcriptQueue.length === 0 ? '<p class="empty-state" style="font-size: 0.8rem;">Queue is empty.</p>' : ""}
            </div>
          </div>
          <div>
            <h4 style="font-size: 0.85rem; color: var(--muted); margin-bottom: 8px;">Pending Reports</h4>
            <div class="queue-list" style="display: grid; gap: 8px;">
              ${reportQueue
                .map(
                  s => `
                <div class="queue-item-card glass-card" style="padding: 10px; font-size: 0.8rem; display: flex; justify-content: space-between; align-items: center;">
                  <span>Session ${s.session_id.replace("SESSION-", "")}</span>
                  <button class="small-action navigate-report" data-session-id="${s.session_id}">Report</button>
                </div>
              `
                )
                .join("")}
              ${reportQueue.length === 0 ? '<p class="empty-state" style="font-size: 0.8rem;">Queue is empty.</p>' : ""}
            </div>
          </div>
        </div>
      </div>
    `;

    // Tier 3 Right: Audit Logs / Recent Activity Feed
    const auditLogs = state.auditLogs || [];
    const recentLogs = auditLogs
      .slice()
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .slice(0, 5);

    const recentActivityTimelineCard = `
      <div class="glass-card">
        <div class="panel-title">
          <h3>Activity Feed</h3>
          <span>live log timeline</span>
        </div>
        <div class="activity-timeline transcript-view-scrollbar">
          ${recentLogs
            .map(
              log => `
            <div class="activity-item" style="border-bottom: 1px solid var(--line); padding: 8px 0; font-size: 0.8rem;">
              <div class="activity-header" style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                <span class="activity-type" style="font-weight: 700; color: var(--primary);">${labelize(log.event_type)}</span>
                <span class="activity-date" style="color: var(--muted); font-size: 0.7rem;">${new Date(log.created_at).toLocaleTimeString()}</span>
              </div>
              <div class="activity-msg">${log.message}</div>
            </div>
          `
            )
            .join("")}
          ${recentLogs.length === 0 ? '<p class="empty-state" style="font-size: 0.8rem;">No recent logs.</p>' : ""}
        </div>
      </div>
    `;

    return `
      ${renderSafetyBanner()}
      
      <!-- Command Bar Filter & Quick Actions -->
      <section class="dashboard-command">
        <div>
          <p>Caseload overview and speech-language screening logs</p>
        </div>
        <div class="action-row">
          <select id="case-filter" aria-label="Select child case" class="case-select-filter">
            ${ownedCases
              .map(
                c =>
                  `<option value="${c.case_id}" ${c.case_id === caseItem.case_id ? "selected" : ""}>${c.display_label} (${c.anonymized_child_code})</option>`
              )
              .join("")}
          </select>
          <button class="primary-action" id="dashboard-new-session-btn">+ New Session</button>
        </div>
      </section>

      <!-- Tier 1: Metric Statistics Cards -->
      ${statsRow}
      
      <!-- Tier 2: Primary Focus Workspace & Screening Metrics -->
      <div class="dashboard-tier2-grid">
        <div style="display: flex; flex-direction: column; gap: 18px;">
          ${focusCaseCard}
          ${featureSummaryCard}
        </div>
        <div>
          ${screeningPanel}
        </div>
      </div>

      <!-- Tier 3: Workflow queues & timeline feed -->
      <div class="dashboard-tier3-grid">
        <div>
          ${queuesCard}
        </div>
        <div>
          ${recentActivityTimelineCard}
        </div>
      </div>

      <!-- Bottom Clinical Safety Reminder Disclaimer -->
      <section class="clinical-callout clinical-note-callout" style="margin-top: 18px;">
        <strong>${iconSvg.shield} Clinical Reminder</strong>
        <span>
          All language analysis, scores, and feature trends are meant to supplement clinician observations. The system is designed for progress tracking and clinical decision support only.
        </span>
      </section>
    `;
  }
  ```

- [ ] **Step 2: Commit view file changes**
  Run: `git commit -am "feat(views): redesign Therapist Dashboard to 3-tier modular grid"`
  Expected: Success

---

### Task 4: Verification and Smoke Testing

**Files:**
*   Test: `therapist-clinician-app/src/__tests__/e2e-smoke.test.js`

- [ ] **Step 1: Run the full test suite**
  Run: `npm run test`
  Expected: All 151 tests pass successfully, confirming that the redesign does not disrupt the application routing, sign-off logic, and reports generation pipeline.
