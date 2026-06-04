# Design Specification: Speech Therapist Web App Redesign (Unified Shell & Clean Modular Grid Dashboard)

**Creative North Star: The Crimson Oasis Refined**

---

## 1. Context & Goal

The current speech therapist web application contains visual inconsistencies, redundant navigation mechanisms (e.g., dual-nav layout with both a top desktop header and a sidebar), and suboptimal spacing density. 

The goal of this redesign is to:
1.  **Unify the Application Shell:** Merge the desktop navigation into a single vertical Sidebar navigation hub and simplify the workspace Topbar.
2.  **Modularize the Therapist Dashboard:** Restructure the main view (`dashboard-view.js`) into a clean, 3-tier modular grid layout (Stats -> Workspace Grid -> Work Queues Hub & Activity Feed), inspired by modern healthcare dashboard templates like AdminLTE and ThemeForest medical EMR systems.
3.  **Refine the "Crimson Oasis" Theme:** Polish color contrast, soft drop-shadow animations, and glassmorphic card edges to meet WCAG AA requirements ($\ge 4.5:1$ text contrast) and improve responsiveness.

---

## 2. Shell & Navigation Architecture

### Desktop Layout (`grid-template-columns: 280px minmax(0, 1fr)`)
*   **Persistent Left Sidebar:**
    *   *Brand Header:* Contains the "ap asd-Project" logo and clinical subtitle.
    *   *Navigation Menu:* Single vertical list of tabs (Dashboard, Children, Sessions, Assessments, Progress Tracking, Caregiver Portal, Reports, Library, Settings, and Admin-only Audit Logs) with clean SVG vector icons.
    *   *Today's Schedule Widget:* Displays the next 3 sessions for quick context.
    *   *User Profile Card:* Contains avatar initials, user name, role badge, and a logout action anchored at the bottom of the sidebar.
*   **Workspace Topbar:**
    *   Displays current view title, welcome message, status badges (API mode, data mode, authentication mode), global search trigger, notifications trigger (with badges), and a help button.
*   **Content Workspace:** The scrollable area where the active views are loaded.

### Tablet Layout
*   The Left Sidebar slides out of view.
    *   Topbar displays a hamburger menu button to toggle the sidebar drawer menu.
    *   Sidebar drawer menu floats as a translucent overlay with a dark scrim to isolate foreground actions.

### Mobile Layout
*   Top header displays only the branding and the current view name pill.
*   **Mobile Bottom Navigation Bar:** Displays 4 primary buttons:
    1.  *Dashboard*
    2.  *Children*
    3.  *Sessions*
    4.  *Assessments*
    5.  *More* (triggering a slide-up drawer for secondary views: Progress, Caregiver, Reports, Library, Settings).

---

## 3. Modular Dashboard Grid Spec

The redesigned Dashboard contains 3 main vertical tiers:

```
+---------------------------------------------------------------------------------------+
|  Active Cases (Card)  |  Pending Transcripts  |  Pending Reports  |  Uploaded Files   |
+-----------------------+-----------------------+-------------------+-------------------+
|  [60%] Focus Patient Case Details             |  [40%] Screening support score       |
|  - Child Code, concerns, tags, privacy warning|  - Gauge & Trend Charts (Unified)    |
|  - Sessions / Uploads / Reports horizontal run|  - Increasing/reducing concern lists |
|  - 5-Domain speech features analysis table    |                                       |
+-----------------------------------------------+---------------------------------------+
|  [70%] Caseload Work Queues Hub               |  [30%] Activity Timeline Feed        |
|  - High review-priority cases                 |  - Scrollable feed of recent logs    |
|  - Transcripts QA review queue                |  - Timestamps, actor tags, events     |
|  - Reports compilation queue                  |                                       |
+---------------------------------------------------------------------------------------+
```

### Tier 1: Statistics Row
*   4 compact metric widget cards.
*   Each card features a prominent count, description, and accent coloring:
    *   **Active Cases:** Uses Ink colors.
    *   **Pending Transcripts:** Highlighted in **Amber** if counts exceed 0.
    *   **Pending Reports:** Highlighted in **Violet** if counts exceed 0.
    *   **Uploaded Files:** Highlighted in Slate.

### Tier 2: Patient Context & Feature Analysis
*   **Left Widget (60%): Patient Overview & Speech Features Table**
    *   *Header Section:* Focus Case ID (clickable, star toggleable) with age, sex, consent, and clinical status badges.
    *   *Caseload Insets:* Total sessions, audio uploads, and generated reports for the patient.
    *   *Features Table:* Standardized domains (Turn-taking, Mean Length of Utterance, Vocabulary Diversity, Repetitive Phrases, Pronoun Reversal).
        *   Each domain displays value, change trend (+/- badge), and a visual progress bar.
*   **Right Widget (40%): Screening Score Analytics Panel**
    *   *Charts:* Inline SVG Gauge Chart and Trend Chart stacked vertically.
    *   *Factors:* Symmetrical grids for "Increasing Concern Factors" (red text/tints) and "Reducing Concern Factors" (green text/tints).

### Tier 3: Work Queues & Activity Timeline
*   **Left Widget (70%): Caseload Work Queues**
    *   3-column panel:
        1.  *High Review-Priority Cases:* Cases with high screening concern scores.
        2.  *Transcript QA Queue:* Sessions awaiting therapist QA check. Clicking "Review" navigates to the Assessments view.
        3.  *Reports Queue:* Sessions ready for progress reports. Clicking "Report" navigates to the Reports view.
*   **Right Widget (30%): Activity Timeline**
    *   A compact vertical timeline of recent audit logs. Height-restricted with a clean, low-contrast scrollbar.

---

## 4. UI/UX Style & Contrast Tokens

All tokens are defined in OKLCH in `styles.css`.

*   **Background Canvas:** `#FDFAF9` (oklch(98% 0.005 15))
*   **Primary Active Accent (Crimson Rose):** `#E11D48` (oklch(56% 0.20 15))
*   **Primary Accent Hover:** `#BE123C` (oklch(47% 0.18 15))
*   **Secondary Accent (Calm Peach):** `#FB923C` (oklch(70% 0.16 48))
*   **Wine Ink Typography (Ink):** `#1F080E` (oklch(18% 0.04 15)) — used for all body text on glass to achieve $\ge 4.5:1$ contrast.
*   **Muted Typography:** `#644A50` (oklch(40% 0.04 15))
*   **Card Container Glass:** `rgba(255, 255, 255, 0.45)` with `backdrop-filter: blur(16px)` and border `1px solid rgba(255, 255, 255, 0.6)`.
*   **Drop Shadow:** `0 12px 32px 0 rgba(190, 18, 60, 0.02)`.
*   **Responsive Breakpoints:**
    *   Mobile: $< 768px$ (displays bottom tab bar)
    *   Tablet: $768px - 1024px$ (sidebar drawer)
    *   Desktop: $\ge 1024px$ (fixed Left Sidebar grid)

---

## 5. Verification Plan

### Automated Checks
*   Run the smoke test to verify all routes and views mount correctly:
    ```bash
    npm run test:e2e:smoke
    ```
*   Verify no syntax errors in CSS and JS.

### Manual Visual Verification
1.  **Navigation Check:** Confirm the top header is hidden on desktop and the sidebar is the single navigation hub.
2.  **Drawer Check:** Shrink the viewport to tablet width (768px) and verify that the sidebar collapses into a drawer triggered by the hamburger icon.
3.  **Bottom Nav Check:** Shrink viewport to mobile width (375px) and verify the bottom tab bar is visible and operational.
4.  **Modular Grid Check:** Verify that the dashboard features the 3-tier structure (top stats, middle split patient overview/speech features/charts, bottom queues).
5.  **A11y/Contrast Check:** Run contrast audits to verify that the Wine Ink text over the light glass panel background passes the 4.5:1 AA contrast ratio.
