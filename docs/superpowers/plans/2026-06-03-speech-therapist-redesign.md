# Speech Therapist Interface Redesign (Crimson Oasis) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the entire Single Page Application to follow the approved "The Crimson Oasis" style: a minimalist, calming clinical grid with Outfit & Inter typography, warm deep-wine text contrast, and floating glass panels over slow-moving rose and peach liquid background blobs.

**Architecture:** We will declare the Crimson Oasis tokens as CSS variables on `:root` in `styles.css` to govern sizing, colors, shadows, and backdrop blurs. We will then refactor the layout, markup, and CSS grids of individual views and SVG chart components to use these variables, replacing hard-edged borders and crowded alignments with spacious glass layers.

**Tech Stack:** Vanilla JavaScript (ES Modules), Vite SPA bundling, Vitest unit/smoke tests, CSS3 grid/flexbox/variables.

---

### Task 1: Fonts & HTML Shell Setup

**Files:**
- Modify: `therapist-clinician-app/index.html`

- [ ] **Step 1: Load Outfit and Inter fonts**
  Insert the Google Fonts `<link>` declarations inside `<head>` in `therapist-clinician-app/index.html`.
  
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@500;600;700&display=swap" rel="stylesheet">
  ```

- [ ] **Step 2: Commit**
  ```bash
  git add therapist-clinician-app/index.html
  git commit -m "style: add google fonts outfit and inter to index.html"
  ```

---

### Task 2: CSS Base Variables & Liquid Background Setup

**Files:**
- Modify: `therapist-clinician-app/src/styles.css`

- [ ] **Step 1: Declare Design Tokens & Reset Typography**
  Edit the top of `therapist-clinician-app/src/styles.css` to declare the Crimson Oasis variables under `:root` and style the main document body with the liquid background container.

  Target content at line 1-24:
  ```css
  :root {
    color-scheme: light;
    --bg: #FDFAF9;
    --primary: #E11D48; /* Crimson Rose */
    --primary-hover: #BE123C;
    --peach: #FB923C;
    --peach-soft: #FFEDD5;
    --neutral-glass: rgba(255, 255, 255, 0.45);
    --ink: #1F080E;
    --muted: #644A50;
    --line: rgba(255, 255, 255, 0.6);
    --line-dark: #F3E8E6;
    --radius-sm: 6px;
    --radius-md: 12px;
    --radius-lg: 20px;
    --shadow-glass: 0 8px 32px 0 rgba(190, 18, 60, 0.03);
    --backdrop-blur: blur(16px);
    font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
  }
  
  body {
    margin: 0;
    min-height: 100vh;
    color: var(--ink);
    background-color: var(--bg);
    font-family: 'Inter', sans-serif;
    position: relative;
    overflow-x: hidden;
  }
  ```

- [ ] **Step 2: Add Liquid Background Animation CSS**
  Add the following class declarations and keyframes to `styles.css` for floating background blobs.

  ```css
  /* Liquid Blobs Background */
  .liquid-background-container {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: -10;
    overflow: hidden;
    pointer-events: none;
  }
  
  .liquid-blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(85px);
    opacity: 0.22;
    animation: floatBlob 25s ease-in-out infinite alternate;
  }
  
  .blob-rose {
    width: 500px;
    height: 500px;
    background: #FDA4AF;
    top: -100px;
    left: -100px;
  }
  
  .blob-peach {
    width: 600px;
    height: 600px;
    background: #FED7AA;
    bottom: -150px;
    right: -100px;
    animation-delay: -5s;
  }
  
  .blob-coral {
    width: 400px;
    height: 400px;
    background: #FECDD3;
    top: 40%;
    right: 20%;
    animation-delay: -10s;
  }
  
  @keyframes floatBlob {
    0% {
      transform: translate(0, 0) scale(1) rotate(0deg);
    }
    50% {
      transform: translate(60px, 40px) scale(1.08) rotate(180deg);
    }
    100% {
      transform: translate(-30px, -50px) scale(0.92) rotate(360deg);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .liquid-blob {
      animation: none;
    }
  }
  ```

- [ ] **Step 3: Define Glass Panel Utility Classes**
  Add the generic glass panel class definitions to `styles.css` to allow views to use unified card structures.

  ```css
  .glass-card {
    background: var(--neutral-glass);
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-glass);
    backdrop-filter: var(--backdrop-blur);
    -webkit-backdrop-filter: var(--backdrop-blur);
    padding: 24px;
    color: var(--ink);
    transition: all 0.3s ease;
  }
  ```

- [ ] **Step 4: Commit**
  ```bash
  git add therapist-clinician-app/src/styles.css
  git commit -m "style: initialize design variables and liquid background blob animations in styles.css"
  ```

---

### Task 3: App Shell Layout & Navigation Redesign

**Files:**
- Modify: `therapist-clinician-app/src/app.js`
- Modify: `therapist-clinician-app/src/styles.css`

- [ ] **Step 1: Inject Liquid Background Container in App Shell**
  Edit `therapist-clinician-app/src/app.js` to render the `.liquid-background-container` as the first layer under the root shell template inside the `render()` function.
  
  Target lines 142-153:
  ```javascript
  root.innerHTML = `
    <div class="liquid-background-container">
      <div class="liquid-blob blob-rose"></div>
      <div class="liquid-blob blob-peach"></div>
      <div class="liquid-blob blob-coral"></div>
    </div>
    <div class="app-shell">
      ${renderSidebar(state)}
      <main class="main-shell">
        ${renderTopbar(state)}
        ${renderEnvironmentModeBanner(state)}
        <div class="content-shell" id="content-area">
          ${renderActiveView(state.activeView)}
        </div>
      </main>
    </div>
  `;
  ```

- [ ] **Step 2: Update Sidebar Layout to Glass panel**
  Modify the `renderSidebar(state)` function in `app.js` to use class naming that links to glass panel styling.
  Ensure navigation active highlight transitions to Crimson Rose: `nav-item active` must render with a soft rose backdrop (`rgba(225, 29, 72, 0.08)`) and Crimson text (`#E11D48`).

- [ ] **Step 3: Define Sidebar & Navigation CSS in styles.css**
  Search for `.sidebar`, `.nav-item`, `.topbar` in `styles.css` and align them with the Glass Oasis:
  - Sidebar background: `rgba(255, 255, 255, 0.4)` with backdrop-filter.
  - Active nav item: `background: rgba(225, 29, 72, 0.08); color: var(--primary); font-weight: 600;`.
  - Brand logo background: `var(--primary)`.

- [ ] **Step 4: Run unit tests to verify**
  Run: `npm --prefix therapist-clinician-app run test`
  Expected: PASS (all 114 tests)

- [ ] **Step 5: Commit**
  ```bash
  git add therapist-clinician-app/src/app.js therapist-clinician-app/src/styles.css
  git commit -m "style: convert app-shell sidebar and topbar layout to glass design and clean typography"
  ```

---

### Task 4: Login Page Redesign

**Files:**
- Modify: `therapist-clinician-app/src/views/login-view.js`
- Modify: `therapist-clinician-app/src/styles.css`

- [ ] **Step 1: Refactor login markup**
  Refactor `therapist-clinician-app/src/views/login-view.js` to render the clean split-screen glass container layout.
  
  ```javascript
  export function renderLogin() {
    return `
      <div class="login-layout-wrapper">
        <div class="login-glass-container">
          <div class="login-brand-info">
            <h2>asd-Project</h2>
            <p>Research prototype for extracting speech-language features to support ASD clinical assessment.</p>
            <div class="safety-warning-badge">⚠️ Clinical Decision-Support Only</div>
          </div>
          <div class="login-form-area">
            <h4>Welcome Back</h4>
            <p>Please sign in to access your clinic dashboard.</p>
            
            <div id="login-error-container" class="form-error" style="display: none;"></div>
            
            <form id="login-form" class="login-input-grid">
              <div class="input-field-group">
                <label for="login-email">Username / Email</label>
                <input type="email" id="login-email" class="glass-input" value="therapist@example.test" required>
              </div>
              <div class="input-field-group">
                <label for="login-password">Password</label>
                <input type="password" id="login-password" class="glass-input" value="demo-password" required>
              </div>
              <button type="submit" class="btn-submit-primary">Sign In</button>
            </form>
          </div>
        </div>
      </div>
    `;
  }
  ```

- [ ] **Step 2: Add Login CSS Styles in styles.css**
  Define `.login-layout-wrapper`, `.login-glass-container`, `.login-brand-info`, `.glass-input`, and `.btn-submit-primary` inside `styles.css`. Ensure inputs have a 12px border radius, custom 3px Crimson focus glow, and high-contrast labels.

- [ ] **Step 3: Run smoke tests to verify login flow**
  Run: `npm --prefix therapist-clinician-app run test`
  Expected: PASS

- [ ] **Step 4: Commit**
  ```bash
  git add therapist-clinician-app/src/views/login-view.js therapist-clinician-app/src/styles.css
  git commit -m "style: redesign login view with split-screen glass layout and crimson rose buttons"
  ```

---

### Task 5: Dashboard Grid & Case Hero Redesign

**Files:**
- Modify: `therapist-clinician-app/src/views/dashboard-view.js`
- Modify: `therapist-clinician-app/src/styles.css`

- [ ] **Step 1: Clean up Dashboard View grid structure**
  Open `therapist-clinician-app/src/views/dashboard-view.js` and clean up the grid styling in sections to match a uniform gap of `20px` and use the defined glass panel layouts.
  Convert the focus case card structure (`focusCaseCard`), features summary card (`featureSummaryCard`), and active queues (`queuesCard`) into `.glass-card` elements with a border radius of 20px.

- [ ] **Step 2: Refactor features summary table**
  Make the feature summary table headers and rows highly readable. Ensure labels use `Wine Ink` or `Soft Muted Wine` rather than low contrast grey-on-grey. Adjust progress trend badges to sage green for positive trend and coral red for negative trend.

- [ ] **Step 3: Update Dashboard layout CSS in styles.css**
  Define layout classes such as `.dashboard-grid` and `.metric-strip` inside `styles.css` to enforce strict spacing and rounded glass aesthetics. Remove outdated solid borders and dark block shadows.

- [ ] **Step 4: Run unit tests to verify dashboard state is intact**
  Run: `npm --prefix therapist-clinician-app run test`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add therapist-clinician-app/src/views/dashboard-view.js therapist-clinician-app/src/styles.css
  git commit -m "style: restructure dashboard layout grid, case card, and feature table with glass aesthetics"
  ```

---

### Task 6: SVG Chart Component Redesigns

**Files:**
- Modify: `therapist-clinician-app/src/components/gauge-chart.js`
- Modify: `therapist-clinician-app/src/components/trend-chart.js`

- [ ] **Step 1: Refactor Gauge Chart text & strokes**
  Update `therapist-clinician-app/src/components/gauge-chart.js` to replace hard-coded fonts with the Outfit family, and ensure stroke colors are aligned with the crimson-rose theme.
  
- [ ] **Step 2: Refactor Trend Chart SVG bars**
  Update `therapist-clinician-app/src/components/trend-chart.js` to style the SVG bars with a soft rounded radius and use the Crimson Rose color accent. Make sure axis labels are readable in the wine-chocolate font.

- [ ] **Step 3: Run Vitest to check charting integrity**
  Run: `npm --prefix therapist-clinician-app run test`
  Expected: PASS

- [ ] **Step 4: Commit**
  ```bash
  git add therapist-clinician-app/src/components/gauge-chart.js therapist-clinician-app/src/components/trend-chart.js
  git commit -m "style: update gauge and trend chart SVGs to use outfit typography and crimson rose strokes"
  ```

---

### Task 7: Transcript Review & Session View Redesign

**Files:**
- Modify: `therapist-clinician-app/src/views/transcript-view.js`
- Modify: `therapist-clinician-app/src/views/session-view.js`
- Modify: `therapist-clinician-app/src/styles.css`

- [ ] **Step 1: Redesign Transcript Review workspace layout**
  Refactor the workspace in `therapist-clinician-app/src/views/transcript-view.js`. Place the CHAT transcript editor and QA results side-by-side inside spacious glass panels.
  Ensure text highlights, action icons, and selected transcript lines use Crimson Rose and soft rose outlines instead of pure blue.

- [ ] **Step 2: Redesign Session View metadata panel**
  Refactor `therapist-clinician-app/src/views/session-view.js` to render the session scheduler, audio upload progress, and clinical assistant indicators inside unified glass panels.

- [ ] **Step 3: Adjust CSS for scrollable tables & editors**
  Update `styles.css` to style the transcript table container with rounded corners and soft glass dividers to ensure it looks premium and does not clip when scrollbars appear.

- [ ] **Step 4: Run unit tests**
  Run: `npm --prefix therapist-clinician-app run test`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add therapist-clinician-app/src/views/transcript-view.js therapist-clinician-app/src/views/session-view.js therapist-clinician-app/src/styles.css
  git commit -m "style: redesign transcript review workspace and session view panels with consistent glass grids"
  ```

---

### Task 8: Progress Reports, Case List, Caregiver Portal & Settings Redesign

**Files:**
- Modify: `therapist-clinician-app/src/views/progress-view.js`
- Modify: `therapist-clinician-app/src/views/cases-view.js`
- Modify: `therapist-clinician-app/src/views/caregiver-view.js`
- Modify: `therapist-clinician-app/src/views/settings-view.js`
- Modify: `therapist-clinician-app/src/styles.css`

- [ ] **Step 1: Update Remaining Views to use glass cards**
  Modify the layout code of `progress-view.js`, `cases-view.js`, `caregiver-view.js`, and `settings-view.js` to replace hard container panels with `.glass-card` classes.
  Ensure all form layouts, settings switches, and case grids are neat and aligned to the 8px grid.

- [ ] **Step 2: Add print safety rule to styles.css**
  Add a print media rule in `styles.css` to strip background liquid animations, backdrop filters, and shadows during print/PDF generation. This ensures printable reports export cleanly on paper.
  
  ```css
  @media print {
    body {
      background: #FFFFFF !important;
      color: #000000 !important;
    }
    .liquid-background-container,
    .liquid-blob {
      display: none !important;
    }
    .glass-card,
    .panel,
    .case-hero {
      background: #FFFFFF !important;
      border: 1px solid #000000 !important;
      box-shadow: none !important;
      backdrop-filter: none !important;
      -webkit-backdrop-filter: none !important;
    }
  }
  ```

- [ ] **Step 3: Run final Vitest suite and verify all test results**
  Run: `npm --prefix therapist-clinician-app run test`
  Expected: PASS

- [ ] **Step 4: Commit**
  ```bash
  git add -A therapist-clinician-app/src/
  git commit -m "style: finalize redesign across progress, cases, caregiver, and settings views with print support"
  ```
