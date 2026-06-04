# Speech Therapist Interface Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Therapist Clinician Web Application using the Sleek Trustworthy Clinical Theme (Deep Navy, Slate Blue, Teal Accent, soft glassmorphism) and replace the raw talkbank layout with a Document-Style Script Editor.

**Architecture:** A lightweight, vanilla JavaScript SPA that updates state and re-renders components using template literals and event bindings. Styling is driven entirely by Vanilla CSS custom properties.

**Tech Stack:** Vanilla HTML/CSS, JavaScript (ES6 Modules), Vite, Vitest.

---

### Task 1: Initialize Google Fonts & Document Settings
**Files:**
- Modify: `therapist-clinician-app/index.html`

- [ ] **Step 1: Check index.html imports**
Verify Outfit and Inter fonts are present in index.html (already verified, line 13: Outfit & Inter).
- [ ] **Step 2: Update index.html Title & Description**
Change document titles if needed (already has appropriate descriptions).
- [ ] **Step 3: Run dev server to check syntax**
Run: `npm run build` inside `therapist-clinician-app` to verify layout builds without issue.
Expected: Build passes.

---

### Task 2: Refactor CSS Token Palette (Sleek Trustworthy Clinical Theme)
**Files:**
- Modify: `therapist-clinician-app/src/styles.css:1-46`

- [ ] **Step 1: Replace `:root` variables in `styles.css`**
Update `:root` variables to use the Deep Navy (#0F172A), Slate Blue (#1E293B), Clinical Teal (#14B8A6), Soft Lavender (#E2E8F0), Off-White (#F8FAFC), and Cool Gray (#94A3B8).
Replace lines 1-46 of `styles.css` with:
```css
:root {
  color-scheme: dark;
  --bg: #0F172A; /* Deep Navy */
  --primary: #14B8A6; /* Clinical Teal */
  --primary-hover: #0D9488;
  --primary-soft: rgba(20, 184, 166, 0.1);
  --peach: #38BDF8; /* Sky Blue accent instead of peach */
  --peach-soft: rgba(56, 189, 248, 0.1);
  --neutral-glass: rgba(30, 41, 59, 0.7); /* Translucent Slate */
  --ink: #F8FAFC; /* Off-white text */
  --muted: #94A3B8; /* Cool Gray */
  --line: rgba(255, 255, 255, 0.08); /* Dark Glass border */
  --line-dark: rgba(255, 255, 255, 0.15);
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --shadow-glass: 0 8px 32px 0 rgba(15, 23, 42, 0.3);
  --backdrop-blur: blur(12px);
  font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;

  /* Status variables */
  --success: #10B981;
  --success-soft: rgba(16, 185, 129, 0.1);
  --warning: #F59E0B;
  --warning-soft: rgba(245, 158, 11, 0.1);
  --destructive: #EF4444;
  --destructive-soft: rgba(239, 68, 68, 0.1);

  /* Backward compatibility mappings */
  --shell: var(--neutral-glass);
  --panel: var(--neutral-glass);
  --panel-soft: rgba(30, 41, 59, 0.85);
  --violet: var(--primary);
  --violet-strong: var(--primary-hover);
  --violet-soft: var(--primary-soft);
  --blue: #3B82F6;
  --blue-soft: rgba(59, 130, 246, 0.1);
  --green: var(--success);
  --green-soft: var(--success-soft);
  --rose: var(--destructive);
  --rose-soft: var(--destructive-soft);
  --amber: var(--warning);
  --amber-soft: var(--warning-soft);
  --radius: var(--radius-md);
  --shadow: var(--shadow-glass);
}
```
- [ ] **Step 2: Run frontend test to ensure variables are valid**
Run: `npm test`
Expected: Tests pass.
- [ ] **Step 3: Commit CSS changes**
Run: `git commit -m "style: update CSS tokens to Sleek Trustworthy Clinical Theme"`

---

### Task 3: Redesign Sidebar & Topbar Shell Layout
**Files:**
- Modify: `therapist-clinician-app/src/app.js`

- [ ] **Step 1: Replace hardcoded Sidebar Unicode icons with inline SVGs**
Modify the icons in `renderSidebar` (lines 165-175 in `app.js`) to use inline SVG outline strings representing Home, Users, Folder, Search, Activity, Heart, FileText, Book, Settings.
- [ ] **Step 2: Update sidebar structure & glass effects**
Add clean border-radius adjustments (`--radius-lg` / `20px`) and borders matching the translucent style.
- [ ] **Step 3: Run Vitest tests to ensure navigation triggers still work**
Run: `npm test`
Expected: 148 tests pass.
- [ ] **Step 4: Commit shell changes**
Run: `git commit -m "style: redesign app layout sidebar and topbar with premium SVGs"`

---

### Task 4: Redesign Login View
**Files:**
- Modify: `therapist-clinician-app/src/views/login-view.js`

- [ ] **Step 1: Modify login-view.js layout**
Apply the glassmorphism container styling centered on the page. Use rounded translucent input boxes (`var(--radius-md)`), and replace solid badges with glass/teals.
- [ ] **Step 2: Run Vitest tests to check auth hydration**
Run: `npm test src/__tests__/auth-session.test.js`
Expected: PASS
- [ ] **Step 3: Commit login view**
Run: `git commit -m "style: update login view to centered glass card layout"`

---

### Task 5: Redesign Dashboard Bento Grid & activity feed
**Files:**
- Modify: `therapist-clinician-app/src/views/dashboard-view.js`

- [ ] **Step 1: Apply Bento Grid layout using CSS Grid**
Configure the grid template blocks to separate the Focus Case summary card, Metric SVG gauges, Curved Area Trend, and a vertical Activity Feed.
- [ ] **Step 2: Bind audit logs statefully into the Activity Feed**
Extract recent audit logs from `store` state and render them as a timeline in `renderDashboard()`.
- [ ] **Step 3: Run Vitest to check dashboard queues rendering**
Run: `npm test src/__tests__/safety-guardrails.test.js`
Expected: PASS (checks safety disclaimers presence in dashboard outputs).
- [ ] **Step 4: Commit dashboard layout**
Run: `git commit -m "style: refactor dashboard into bento grid layout with audit log activity feed"`

---

### Task 6: Refactor SVG Charts (Gauge & Trend Charts)
**Files:**
- Modify: `therapist-clinician-app/src/components/gauge-chart.js`
- Modify: `therapist-clinician-app/src/components/trend-chart.js`

- [ ] **Step 1: Smooth the SVG Gauge Chart**
Modify `gauge-chart.js` to draw a clean, curved gradient gauge using Teal (`--primary`) or Rose/Amber depending on score severity. Fix fonts to use Outfit/Inter.
- [ ] **Step 2: Convert Trend Chart bars to Spline Area Chart**
Modify `trend-chart.js` to draw a smooth SVG spline path with gradient area fills (`stop-color: var(--primary)`) and circular data points.
- [ ] **Step 3: Run Vitest to verify charts render clean SVG text**
Run: `npm test`
Expected: PASS
- [ ] **Step 4: Commit charts**
Run: `git commit -m "style: refactor gauge and trend charts to high-fidelity SVG graphics"`

---

### Task 7: Redesign Caseload (Children) Card Grid & Privacy popover
**Files:**
- Modify: `therapist-clinician-app/src/views/cases-view.js`

- [ ] **Step 1: Change Caseload List to a Grid of cards**
Display each case as a card, with stars, sex, age (months), and concern levels.
- [ ] **Step 2: Group Privacy actions (Withdraw, Export, Delete) into a popover Settings menu**
Add an interactive "Privacy Settings" button for each case. Clicking it displays a localized popover container containing the three PDPA buttons instead of rendering all buttons directly on the cards.
- [ ] **Step 3: Run Vitest to check cases render and actions fire**
Run: `npm test src/__tests__/case-service-api.test.js`
Expected: PASS
- [ ] **Step 4: Commit Caseload**
Run: `git commit -m "feat: redesign caseload view with cards grid and a popover privacy menu"`

---

### Task 8: Implement Stepper Pipeline & Record Visualizer in Session View
**Files:**
- Modify: `therapist-clinician-app/src/views/session-view.js`

- [ ] **Step 1: Render Stepper pipeline at the top of Selected Session details**
Render a horizontal stepper showing the session's pipeline status.
- [ ] **Step 2: Add SVG recording visualizer for microphone input**
When a recording starts in `session-view.js`, animate/oscillate an SVG line graph mimicking live microphone audio wave input.
- [ ] **Step 3: Align sessions lists as a timeline sidebar**
List sessions in a clean vertical timeline.
- [ ] **Step 4: Run Vitest to ensure session workflows still match backend mock criteria**
Run: `npm test src/__tests__/session-service-api.test.js`
Expected: PASS
- [ ] **Step 5: Commit sessions**
Run: `git commit -m "feat: add pipeline stepper and audio recording wave visualizer to session view"`

---

### Task 9: Redesign Transcript Review Workspace (65/35 Split & Collapsible Header Drawer)
**Files:**
- Modify: `therapist-clinician-app/src/views/transcript-view.js`

- [ ] **Step 1: Refactor transcript view to split screen**
Establish a 65% left panel for script editor and a 35% right panel for sticky controls (QA warnings, AI decision outputs, evidence notes checklist).
- [ ] **Step 2: Add collapsible `<details>` wrapper for CHAT header text**
Move the pre-formatted monospace text headers at the top of the transcript inside a collapsible `<details>` component.
- [ ] **Step 3: Run Vitest to confirm transcript and headers render properly**
Run: `npm test src/__tests__/transcript-workflow.test.js`
Expected: PASS
- [ ] **Step 4: Commit workspace structure**
Run: `git commit -m "style: restructure transcript workspace into a 65/35 split screen with collapsible header drawer"`

---

### Task 10: Implement Document-Style Script Editor with borderless hover inputs
**Files:**
- Modify: `therapist-clinician-app/src/components/utterance-editor.js`

- [ ] **Step 1: Change the table structure to unified script lines**
Remove the raw grid layout. Style the container as a white-on-dark document sheet.
- [ ] **Step 2: Render borderless inputs and selectors**
Set text edit inputs and speaker select elements to have borderless transparent backgrounds. Add `:hover` and `:focus` styles in `styles.css` to show subtle border glows when active, enabling click-to-edit inline corrections.
- [ ] **Step 3: Align play buttons, badges, and reviewed checkbox to the right**
Ensure all metadata/action elements are neatly right-aligned to fit a professional document layout.
- [ ] **Step 4: Run Vitest tests to confirm utterance edits are parsed properly**
Run: `npm test src/__tests__/review-service-api.test.js`
Expected: PASS
- [ ] **Step 5: Commit editor**
Run: `git commit -m "feat: implement document-style script editor with borderless inline hover inputs"`

---

### Task 11: Implement Progress Side-by-side comparison & Word Tag Cloud
**Files:**
- Modify: `therapist-clinician-app/src/views/progress-view.js`

- [ ] **Step 1: Organize Session comparison into side-by-side card displays**
Update `renderProgressReports()` to lay out session data comparisons side-by-side.
- [ ] **Step 2: Render word cloud tags for new words**
Render lists of newly spoken words as dynamic tags inside a tag cloud.
- [ ] **Step 3: Run Vitest to confirm progress outputs match metric tests**
Run: `npm test src/__tests__/progress.test.js`
Expected: PASS
- [ ] **Step 4: Commit progress views**
Run: `git commit -m "feat: redesign progress report with side-by-side diff cards and word cloud tags"`

---

### Task 12: Add print CSS layout optimizations
**Files:**
- Modify: `therapist-clinician-app/src/styles.css:1732-1765`

- [ ] **Step 1: Update `@media print` CSS rules in `styles.css`**
Set rules to hide navigation buttons, sidebars, header details, and dark translucent backdrops. Force text to deep black on solid white background for clinical printable formatting.
- [ ] **Step 2: Add page breaks on major section divisions**
Apply `page-break-before: always` to clinical disclaimers or session tables.
- [ ] **Step 3: Run build command to confirm compiling**
Run: `npm run build`
Expected: PASS
- [ ] **Step 4: Commit print styles**
Run: `git commit -m "style: optimize print CSS sheets for clinical PDF compilation"`
