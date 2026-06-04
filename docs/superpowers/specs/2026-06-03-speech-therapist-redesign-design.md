# Design Spec: Speech Therapist Interface Redesign (Sleek Trustworthy Clinical Theme)

- **Date**: 2026-06-03
- **Status**: Validated & Approved by User
- **Target App**: `therapist-clinician-app` (Vite SPA)

---

## 1. Context & Goals

The speech therapist prototype (`therapist-clinician-app`) is a clinical decision-support dashboard. The current interface has been flagged by the user as cluttered, unorganized, and inconsistent.

The goal of this redesign is to implement the **"Sleek Trustworthy Clinical Theme"** and a unified workspace layout:
- **Clean Structure**: A structured layout that reduces cognitive load during transcript reviews.
- **Calming Aesthetics**: A minimalist, clean clinical interface featuring floating translucent glass panels over a deep navy and slate base.
- **Professional Palette**: Deep Navy (#0F172A), Slate Blue (#1E293B), Soft Lavender, Teal Accent, and clear green/red status tags.

---

## 2. Redesign Scope by View

The redesign covers the entire Single Page Application. The following views will be modified:

### 2.1. App Shell & Layout (`src/app.js` & `src/styles.css`)
- **Background**: Deep Navy (#0F172A) base with subtle glowing glass gradients.
- **Sidebar**: Floating glass panel with a translucent border, soft slate-blue and teal highlights for active tabs, and premium SVG icons (instead of Unicode symbols like `⌂`, `◌`, `□`).
- **Topbar**: Clean up topbar actions, replacing generic badges with structured glass badges.

### 2.2. Login View (`src/views/login-view.js`)
- **Structure**: Center the login container on a single large glass panel container.
- **Styling**: Replace all hard input boxes with rounded, translucent input fields.

### 2.3. Dashboard View (`src/views/dashboard-view.js`)
- **Bento Grid Layout**: Organize the dashboard into clear bento card sections.
  - Case Hero Card: Large profile summary with a clean consent tag and safety warning.
  - Concern Score Gauge: Styled SVG gauge chart (`src/components/gauge-chart.js`) matching the Outfit typeface.
  - Longitudinal Trend Chart: Curved SVG Spline Area Chart (`src/components/trend-chart.js`) with gradient fills.
  - Recent Clinical Activity Feed: Timeline of recent audit events or pipeline status updates.
- **Clinical Disclaimer**: Prominently displayed to align with medical/legal guidelines.

### 2.4. Caseload/Children View (`src/views/cases-view.js`)
- **Caseload Grid**: Card-based caseload items showing concern status badges, ages, and stars.
- **Privacy Drawer**: Hide PDPA options (Export, Withdraw, Delete) inside a clean popover Drawer instead of cluttered buttons.

### 2.5. Session View (`src/views/session-view.js`)
- **Stepper Pipeline**: Visual pipeline steps indicating session progression (Setup ➔ Recording ➔ Transcription ➔ Clinical Review ➔ Report).
- **Audio Wave Visualizer**: Interactive SVG waveform visualizer for mic recording.
- **Sidebar Session Timeline**: Chronological sidebar listing sessions.

### 2.6. Transcript & Assessment View (`src/views/transcript-view.js` & `src/components/utterance-editor.js`)
- **65/35 Split Workspace**:
  - **Left Panel (65%)**: Document-Style Transcript Editor. Displays a continuous, borderless sheet of text (similar to Word or Google Docs). Line numbers on the left, speaker dropdown selectors, and inline editing fields that have no border when not focused. Quick play buttons and reviewed checkboxes are aligned to the right.
  - **Right Panel (35%)**: Sticky control dashboard containing QA results, AI Decision-Support metrics, and clinical evidence notes.
  - **Top Area**: A collapsible metadata header block to toggle raw CHAT data.

### 2.7. Progress & Reports View (`src/views/progress-view.js`)
- **Analytics Layout**: Side-by-side session comparisons, word tag cloud for new words.
- **Print Optimization**: Clean print layouts using `@media print` CSS directives to print beautifully on white paper, stripping out dark backdrops, sidebars, and buttons.

---

## 3. Design Tokens (Sleek Trustworthy Clinical Theme)

### 3.1. Colors (Hex sRGB)
- **Primary / Background**: Deep Navy (`#0F172A`)
- **Secondary Background**: Slate Blue (`#1E293B`)
- **Accent Color**: Clinical Teal (`#14B8A6`)
- **Lavender Highlight**: Soft Lavender (`#E2E8F0`)
- **Neutral Ink**: Off-White (`#F8FAFC`)
- **Neutral Muted**: Cool Gray (`#94A3B8`)
- **Glass Card Background**: Translucent white (`rgba(30, 41, 59, 0.7)`)
- **Glass Border**: Translucent border (`rgba(255, 255, 255, 0.08)`)

### 3.2. Typography
- **Headings (Display, Headline, Title)**: Outfit (sans-serif)
- **Body & Labels**: Inter (sans-serif)

### 3.3. Rounded Scale
- `sm`: 6px (table cells, mini badges)
- `md`: 12px (buttons, input fields, queues)
- `lg`: 20px (glass card panels)

### 3.4. Elevation
- **Glass Shadow**: `0 8px 32px 0 rgba(15, 23, 42, 0.3)`
- **Backdrop Blur**: `backdrop-filter: blur(12px)`

---

## 4. Implementation Checklist

- [ ] Add Outfit and Inter font links to `index.html`.
- [ ] Refactor `:root` CSS custom properties in `src/styles.css` with the new design tokens.
- [ ] Implement premium SVG icons (Lucide-like inline SVGs) for the sidebar and controls.
- [ ] Redesign `app.js` shell layout (Sidebar, Topbar, and environmental banner).
- [ ] Update `login-view.js` with center-aligned glass panel styling.
- [ ] Update `dashboard-view.js` with Bento layout, activity timeline, and SVG charts.
- [ ] Update `cases-view.js` with card caselists and a clean privacy drawer.
- [ ] Update `session-view.js` with pipeline stepper stepper, record visualizer, and timeline list.
- [ ] Update `transcript-view.js` and `utterance-editor.js` with the 65/35 split workspace, collapsible metadata, and Word-like borderless inline editor.
- [ ] Update `progress-view.js` with session comparison cards and print-ready CSS rules.
- [ ] Verify that all text contrast values meet or exceed 4.5:1 on all surfaces.
