# LinguaLens UX/UI Modernization Master Design

Date: 2026-07-13  
Product version: v1.6.3  
Status: Approved design contract  
Canonical frontend: `apps/lingualens-app/`  
Canonical backend: `apps/api/`

## 1. Purpose and boundaries

LinguaLens will become a session-centered clinical workflow workbench for speech therapists across mobile, tablet, laptop, and desktop. The interface will prioritize the therapist's next task, keep one canonical session workspace, clearly distinguish data modes, and preserve backend-confirmed clinical safety gates.

This modernization does not add clinical or ML capability. It does not change transcript eligibility, consent rules, report safety rules, ML behavior, backend contracts, or signed-report immutability to simplify the UI.

Required safety boundaries:

- Decision-support only.
- Therapist review and sign-off remain required.
- Transcript review, QA, and attestation gates remain authoritative.
- No autonomous diagnosis or diagnostic labels.
- No unsupported Thai norms or claims of Thai clinical validation.
- Experimental audio transcription remains clearly labeled as draft.
- Signed reports remain immutable; edits create a new draft revision.
- Raw audio is never persisted in browser storage.
- UI success appears only after backend confirmation.

## 2. Evidence baseline and worktree protection

The mandatory baseline is recorded in `docs/frontend/UX_UI_BASELINE_AUDIT.md`. Forty full-page screenshots are stored under `docs/frontend/baseline-screenshots/` at the required viewports.

The pre-modernization tracked worktree backup is:

```text
/tmp/lingualens-pre-modernization-worktree-2026-07-13.patch
```

The existing uncommitted frontend changes are intentional work-in-progress. They must be preserved and built on. No implementation phase may reset, revert, discard, check out over, or silently overwrite them.

Baseline evidence includes:

- dirty-worktree inventory and relevant frontend diffs;
- current route map and navigation;
- frontend component line counts;
- direct API/data access inventory;
- backend fallback behavior;
- current API and safety boundaries;
- screenshots at 390x844, 768x1024, 1024x1366, 1280x800, and 1440x900;
- production bundle route sizes;
- unit, typecheck, lint, build, and smoke results;
- known deterministic smoke failure at the pasted-transcript save transition;
- current workflow behavior and design-system inconsistencies.

## 3. Approved strategic approach

Use an incremental strangler refactor inside the existing Next.js application.

The sequence is:

1. Establish explicit capability, data-mode, remote-state, route, and authorization contracts.
2. Extract focused services, hooks/reducers, and presentational sections from existing components.
3. Consolidate routes and navigation behind those stable contracts.
4. Consolidate the live visual system.
5. Modernize screens in workflow order.
6. Harden states, accessibility, performance, and end-to-end behavior.

This approach preserves existing safe behavior and ongoing work while removing one responsibility at a time from the monoliths. A route-first migration was rejected because it would carry the current smoke failure and fallback ambiguity into new URLs. A parallel feature-tree rewrite was rejected because it would duplicate workflow logic and increase safety regression risk.

## 4. Target frontend architecture

```text
apps/lingualens-app/src/
  app/                       route composition and server-side guards
  components/
    ui/                      accessible reusable primitives
    shell/                   navigation, context headers, responsive shell
  features/
    work-queue/
    cases/
      components/
      hooks/
      services/
      types.ts
    sessions/
      intake/
      transcript/
      findings/
      report/
      components/
      hooks/
      services/
      state/
      types.ts
    reports/
    settings/
  services/
    api/                     transport and schema decoding only
    capabilities/            runtime capability derivation
    adapters/                backend, sample, local-draft boundaries
  design-system/
    tokens.css
    components.css
```

Adapt this structure to existing conventions rather than moving files mechanically. Ordinary UI components should usually stay below 250 lines; complex feature containers should usually stay below 500 lines. A larger file requires a documented cohesion reason. Splitting into meaningless fragments is not a goal.

No new global state library will be added. Focused reducers, hooks, server composition, and the existing backend remain sufficient.

## 5. Data flow and state contracts

### 5.1 Data flow

```text
Authenticated server route/data boundary
→ feature service or adapter
→ decoded backend contract
→ typed remote state and explicit data mode
→ feature hook or reducer
→ presentational component
→ explicit mutation state
→ backend confirmation
→ confirmed UI state
```

Presentational components receive typed data, view state, and callbacks. They never call APIs directly.

### 5.2 Remote state

All backend-driven features use a discriminated remote state:

```ts
type RemoteState<T> =
  | { status: "idle" }
  | { status: "loading"; previous?: T }
  | { status: "success"; data: T }
  | { status: "empty" }
  | { status: "error"; error: SafeUiError; previous?: T }
  | { status: "unavailable"; reason: CapabilityReason }
  | { status: "stale"; data: T; invalidatedBy: StaleCause };
```

Mutation state is explicit: idle, saving, saved, failed, retrying. No clinical mutation is presented as successful before a confirmed backend response.

### 5.3 Data mode

Every backend-driven page exposes exactly one data mode:

```ts
type DataMode = "backend" | "sample" | "local-draft" | "unavailable";
```

Rules:

- Product routes never import sample records.
- Sample records exist only inside environment-gated `/demo/*` adapters.
- Sample mode has a persistent Sample Data label and isolated storage namespace.
- Local drafts contain only safe UI/workflow metadata and never raw audio.
- Backend failure never swaps in sample data.
- Previously confirmed data may remain visible only when safe and visibly marked stale/error.

### 5.4 Capability model

Frontend capabilities are derived from decoded runtime settings and authenticated backend responses. They are not guessed from page behavior.

```ts
type BackendCapabilities = {
  cases: "available" | "unavailable";
  audioUpload: "available" | "experimental" | "unavailable";
  transcription: "available" | "experimental" | "unavailable";
  transcriptQa: "available" | "unavailable";
  featureExtraction: "available" | "unavailable";
  aiReview: "available" | "disabled" | "unavailable";
  reportDrafting: "available" | "disabled" | "unavailable";
  pdfExport: "available" | "unavailable";
};
```

Frontend types must not drift from backend schemas. Contract validation covers runtime capability payloads, workflow status values, authorization errors, remote/stale-state responses, and report/transcript version provenance.

## 6. Canonical routes and navigation

### 6.1 Canonical routes

```text
/
/today
/cases
/cases/[caseId]
/sessions/[sessionId]?view=intake|transcript|findings|report
/reports
/settings
/login
```

`/` applies the existing authentication gate, then redirects authenticated users to `/today` and unauthenticated users to `/login`.

Session `view` is validated against `intake`, `transcript`, `findings`, and `report`. Missing or invalid values resolve safely to `intake`.

### 6.2 Navigation

Primary navigation order:

1. Today
2. Cases
3. Session
4. Reports
5. Settings

Session links to the active authorized session when one is known. Otherwise it links to `/cases?intent=start-session`. Mobile uses bottom navigation. Tablet uses a collapsible rail or drawer. Desktop uses an expanded sidebar.

### 6.3 Legacy compatibility

Legacy routes become identifier-aware redirects:

- `/record` → Session `view=intake`
- `/review-transcript` and `/transcript` → Session `view=transcript`
- `/results` → Session `view=findings`
- `/report-summary` → Session `view=report`

With a valid authorized `session_id`, redirect to the matching canonical Session view. Without one, redirect to `/cases?intent=start-session`. Invalid or unauthorized IDs never open a demo, first, or unrelated session.

### 6.4 Demo routes

All `/demo/*` routes:

- require an explicit build/runtime flag;
- return not-found when disabled;
- remain absent from ordinary navigation;
- display a persistent Sample Data banner;
- use isolated adapters and storage namespaces;
- never share case, session, report, organization, or browser state with product routes.

## 7. Settings and authorization contract

`/settings` is the single canonical route.

Therapist sections:

- profile;
- organization context;
- credentials;
- accessibility and display preferences;
- sample-data status;
- owned privacy requests.

Organization-admin sections:

- team and role management;
- invitations;
- audit log;
- privacy operation queue;
- runtime diagnostics;
- integration status.

Deep links use validated `?section=` values. Authorization is enforced at the backend and authenticated server route/data boundary, not only in rendered UI.

Ordinary therapists do not receive admin navigation, admin data requests, disabled admin controls, or developer/ML diagnostics. Unauthorized direct links return a safe 403 state or redirect to the first authorized therapist section before admin data loads.

Role, invitation, privacy, and organization-management mutations preserve backend audit logging. The implementation documents and tests the therapist versus organization-admin role matrix.

## 8. Approved product direction and visual concept

The product direction is a calm clinical editorial workbench. The approved layout direction is **Focused workbench**.

Today uses:

- one prioritized queue;
- one next action per row;
- one prominent Start session action;
- a quiet contextual rail;
- status grouping from the triage concept only inside the queue;
- no full Kanban layout.

The case-first split-view pattern is used only inside Cases and Session Workspace on tablet and desktop. It is not the Today landing page.

Approved visual companion artifacts are stored locally under:

```text
.superpowers/brainstorm/23243-1783881109/content/
```

The responsive Transcript contract is represented by `transcript-responsive-contract-v2-approved.html`.

## 9. Screen specifications

### 9.1 Today

Today answers what requires attention, what is processing, what is ready, and what the therapist should do next.

Primary queue groups, in priority order:

1. Needs action
2. Processing
3. Ready for review
4. Ready for sign-off
5. Recently completed

Each row shows anonymized case label, session date, task, workflow status, reason, data mode when relevant, and one next action. Secondary content includes recent cases, today's sessions, and compact system status only when it affects work. The first viewport is not filled with equal-weight statistics.

### 9.2 Cases

Case list supports search, workflow-status filter, consent filter, authorized clinician filter, and sorting by activity or next action.

Desktop/tablet may use a split view with list and selected-case context. Mobile uses compact rows and a dedicated detail view rather than a compressed table.

Case detail contains Overview, Sessions, Goals, Progress, Reports, and authorized Care team sections. Progress language remains descriptive and requires therapist interpretation.

`/cases?intent=start-session` opens a deliberate case/session selector and never invents a session.

### 9.3 Session context

All Session views share a persistent context header showing case label, session date, source type, consent state, transcript state, workflow stage, and data mode.

Technical provenance lives in an expandable inspector, not primary navigation.

### 9.4 Intake

Intake supports existing CHAT upload, transcript paste, audio upload, and audio recording. Audio is always experimental.

It shows selected source, consent, upload state, safe metadata, processing state, quality warnings, capability state, and the next therapist action. Draft ASR output is never presented as accurate or final.

### 9.5 Transcript

Desktop:

- Transcript editor is dominant and always receives at least 60% of usable workspace width.
- Audio/QA inspector is bounded, collapsible, and optionally resizable.
- Inspector popovers and menus escape clipping containers.

Tablet portrait:

- True two-pane layout when minimum transcript width is maintained.
- Secondary Audio/QA pane can collapse or switch segmented views.
- Transcript never shrinks below its tested readable width.

Mobile:

- Single column.
- Safe-area-aware sticky audio player.
- Sticky save/review action bar with matching content padding.
- QA/attestation in accordion or bottom sheet.
- Secondary line actions in an accessible overflow menu.

At every viewport, transcript lines remain directly editable. Selected-line treatment uses background, full border, focus semantics, and `aria-selected`. Scroll-to-selected-line preserves focus. Merge, split, mark unclear, and delete remain keyboard accessible.

### 9.6 Findings

Findings are unavailable or preliminary until backend gates permit them. They show transcript provenance, reviewed transcript version, feature-set version, descriptive language-sample cues, missing-data warnings, limitations, and AI-assisted review disposition. They never use diagnostic labels or appear as a generic Results page before review.

### 9.7 Report

Report uses one shared Session implementation. It shows editable draft, source summary, safety validation, limitations, therapist edits, sign-off/export state, and provenance.

Large desktop may use evidence/safety inspector plus report editor. Tablet portrait and mobile use one column. Signed reports are read-only; subsequent changes create a draft revision that references the signed source.

### 9.8 Reports

Reports is a library and task queue, not a second editor. It groups Draft, Needs review, Blocked by safety, Ready for sign-off, and Signed. Each row has one next action and routes to Session `view=report`.

No speculative completion percentages are shown.

### 9.9 Settings

Settings uses the authorization contract in section 7. Admin-only sections never render or fetch for therapists.

## 10. Responsive shell contract

### Mobile, 360–479 px

- bottom navigation;
- one-column layout;
- no permanent sidebar;
- 44 px touch hit areas;
- safe-area-aware sticky controls;
- drawers/bottom sheets for secondary inspectors;
- no page-level horizontal overflow.

### Large mobile, 480–767 px

- bottom navigation retained;
- primary clinical workflow remains one column;
- compact two-column metadata only where readable.

### Tablet portrait, 768–1023 px

- collapsible navigation rail or drawer;
- dedicated Session two-pane behavior;
- switchable/collapsible inspector;
- no squeezed desktop transcript grid.

### Tablet landscape and small desktop, 1024–1279 px

- compact expanded sidebar;
- two or three bounded workspace regions;
- collapsible inspector;
- readable list/table density.

### Desktop, 1280 px and above

- expanded navigation;
- dominant transcript editor;
- contextual inspector;
- keyboard-efficient controls;
- constrained readable prose width.

Required exact verification viewports are 390x844, 768x1024, 1024x1366, 1280x800, and 1440x900.

## 11. Design system contract

### 11.1 Source of truth

Preserve the live restrained clinical teal identity in `src/styles/globals.css`, then consolidate it into `design-system/tokens.css` and `design-system/components.css`.

Replace stale/conflicting design documentation with documentation that matches the implemented product. Existing safe visual normalization is a foundation, not disposable work.

### 11.2 Color and surfaces

- true-white reading surfaces;
- cool low-chroma page background;
- near-black primary text;
- dark readable secondary text;
- teal only for primary action, focus, selection, active navigation, and key workflow state;
- amber for caution;
- red only for blocking or destructive state;
- restrained green for confirmed safe success;
- borders or tight shadows, never decorative glass or wide ghost-card shadows.

Panels use 6–10 px radii. Pills are reserved for compact tags and status controls. Status is never communicated by color alone.

### 11.3 Typography

Use `Noto Sans Thai` and `Noto Sans` as the unified Thai-Latin product font stack with system fallbacks. Atkinson Hyperlegible is reserved for an optional accessibility mode or Latin-only transcript contexts to avoid mixed-script metric inconsistencies.

Use a fixed rem hierarchy with one product family. Transcript text is 15–16 px with generous line height. Timestamps and metadata are compact but meet AA contrast. Prose is capped near 70 characters; dense data may be wider.

### 11.4 Components and naming

Standardize variants for buttons, navigation, status badges, fields, panels, lists/tables, skeletons, empty/error states, sticky action bars, drawers, transcript rows, popovers, and overflow menus.

Migrate away from misleading `GlassCard`, `GradientButton`, and `liquid` naming. Do not add a new UI dependency without accessibility, complexity, and bundle evidence.

## 12. Motion and interaction contract

Motion communicates state only:

- selection and hover: 80–120 ms;
- popovers and menus: 150–180 ms;
- drawers and panels: 180–240 ms;
- pane resizing: immediate or minimally animated.

Use ease-out curves and avoid layout-property animation. `prefers-reduced-motion` produces immediate state changes.

Touch devices preserve at least a 44 px hit area without forcing visually oversized desktop controls. Popovers, menus, and drawers use native popover/dialog or portals so overflow containers cannot clip them.

Every interactive component defines default, hover, focus, active, disabled, loading, and error states where applicable.

## 13. Accessibility contract

Target WCAG 2.2 AA where practical.

Required acceptance checks:

- logical headings and landmarks;
- keyboard-complete navigation and transcript editing;
- visible focus and focus-preserving scroll-to-selected-line behavior;
- `aria-selected` on selected transcript lines;
- `aria-live` save, job, success, and error announcements;
- focus trapping and restoration for dialogs/drawers/menus;
- `forced-colors` support;
- field errors linked through `aria-describedby`;
- semantic tables where tables are used;
- no state communicated by color alone;
- keyboard shortcuts that do not conflict with browser defaults;
- 44 px touch hit areas;
- no sticky-control overlap at safe areas;
- usable 200% zoom;
- no horizontal page overflow;
- sufficient text and control contrast;
- reduced-motion support.

## 14. Error handling and concurrency

### 14.1 Error presentation

- Initial loading uses structural skeletons.
- Empty states explain the surface and offer one valid next action.
- Local failures use inline retry when the rest of the page remains usable.
- Page-level failure is reserved for unusable surfaces.
- Unavailable capabilities remain visibly unavailable and never appear successful.
- Safe prior data may remain visible only with explicit stale/error state.
- Raw backend errors and clinical identifiers never appear in UI telemetry or logs.

### 14.2 Race and cancellation behavior

Tests and implementation cover:

- session changes during requests;
- stale responses arriving after newer responses;
- navigation during save;
- duplicate submissions;
- retry after backend recovery;
- transcript edits invalidating downstream findings and reports;
- cancellation/ignore behavior on unmount and identity change;
- idempotency or disabled-submit behavior for clinical mutations.

Older responses never overwrite newer session or organization state.

## 15. Performance contract and budgets

Performance is measured before optimization.

### 15.1 Initial budgets

These are implementation gates and may be tightened after Phase 0 measurement:

- Shared first-load JavaScript should not exceed the Phase 0 baseline of 102 kB by more than 10 kB gzip without approved exception.
- Today, Cases, Reports, and Settings route first-load JavaScript should not exceed their Phase 0 route baseline by more than 15%.
- Session route first-load JavaScript should remain at or below its Phase 0 baseline of 230 kB, with a target below 210 kB after feature extraction and justified dynamic loading.
- No individual new client chunk should exceed 80 kB gzip without approved exception.
- Interaction feedback for ordinary controls should begin within 100 ms on the reference development device.
- Transcript keystroke processing p95 should remain below 50 ms at 500 lines and below 100 ms at 1,000 lines on the reference test device.
- Scrolling should maintain at least 50 fps at 500 lines and 45 fps at 1,000 lines during benchmark runs.

The implementation plan must record the reference device/browser, exact measurement method, cold/warm conditions, and raw results. Exceeding a budget requires remediation or a documented, user-approved exception.

### 15.2 Transcript benchmarks

Benchmark approximately 100, 500, and 1,000 lines for:

- initial render;
- keystroke latency;
- selected-line change;
- audio-time highlighting;
- filter changes;
- QA state updates;
- scrolling;
- memory growth.

Dynamic loading requires bundle evidence showing that a heavy feature is not needed for the initial task. Virtualization is added only when benchmark evidence shows the non-virtualized editor misses a budget and the chosen editor preserves selection, focus, keyboard behavior, accessibility, and audio synchronization.

### 15.3 React and Next.js rules

- Preserve Server Components for route/auth composition.
- Do not convert whole pages to client components.
- Fetch independent data concurrently.
- Keep high-frequency audio time updates outside broad workspace state.
- Replace repeated transcript `findIndex` scans with indexed lookup.
- Memoize only measured expensive derivations.
- Minimize serialized props and avoid large barrel imports.
- Use stable keys.

## 16. Testing strategy

### 16.1 Test selection

- Existing behavior first receives passing characterization tests.
- Bug fixes begin with a failing regression test that reproduces the defect.
- New behavior begins with a failing test.
- Pure visual changes use approved-concept comparison, exact responsive screenshots, accessibility checks, and visual regression evidence rather than artificial unit tests.

### 16.2 Test layers

Unit tests:

- view/section validators;
- capability derivation and schema decoding;
- remote-state and data-mode reducers;
- stale downstream invalidation;
- redirect helpers;
- role matrix;
- indexed transcript utilities.

Component tests:

- all remote and mutation states;
- save/job/error announcements;
- direct transcript editing and overflow actions;
- selected-line semantics;
- inspector collapse/switch/resize;
- safe error and retry behavior;
- therapist versus admin rendering;
- signed report immutability.

Route and contract tests:

- `/` auth-aware redirect;
- legacy redirects with and without identifiers;
- invalid Session view fallback;
- unauthorized case/session/settings access;
- demo gating and isolation;
- capability payloads and workflow statuses;
- authorization error shapes;
- stale-state responses;
- transcript/report provenance versions.

Backend tests:

- therapist versus admin authorization;
- invitation, role, privacy, and organization-management audit events;
- signed report and transcript version contracts;
- generic safe authorization errors.

Playwright:

- core backend-confirmed therapist workflow;
- negative transcript QA path;
- report safety and signed immutability;
- explicit demo/sample mode;
- real backend contract or contract-faithful environment;
- backend failure, recovery, retry, and duplicate submission;
- navigation/session change during requests;
- required viewport layout and overflow checks;
- keyboard, focus, safe-area, and touch-target checks.

Mock-only success is insufficient.

### 16.3 Existing smoke failure

Before route migration, diagnose the deterministic pasted-transcript save failure using the debugging ledger:

1. Reproduce the existing 3/3 smoke failure.
2. Trace the save mutation and navigation path.
3. Enumerate runtime settings, auth headers, origin, backend mutation response, and router reachability.
4. Rank hypotheses and run the cleanest disproof first.
5. Add a failing regression test only after the failure path is known.
6. Fix and verify against all breadcrumbs.

Do not mask this failure by changing the route expectation before establishing the actual cause.

## 17. Implementation phases and gates

### Phase 0: Baseline freeze

- preserve the dirty worktree;
- save external backup patch;
- record routes, API contracts, screenshots, bundle sizes, test failures, workflow behavior, and visual defects;
- complete `docs/frontend/UX_UI_BASELINE_AUDIT.md`.

### Phase 1: Remote-state and capability foundation

- add contract decoding;
- add capability and data-mode models;
- add product/demo adapters;
- remove sample imports from product routes.

### Phase 2: Behavior-preserving decomposition

- extract Session orchestration;
- extract Cases list/detail and mutations;
- extract Settings therapist/admin services;
- extract Transcript editor state/actions;
- extract shared Report implementation.

### Phase 3: Route and authorization consolidation

- auth-aware root redirect;
- canonical navigation;
- Session view validation;
- legacy identifier-aware redirects;
- server/backend Settings gates;
- demo environment gating.

### Phase 4: Design-system consolidation

- authoritative tokens and typography;
- shell breakpoints;
- standardized components/states;
- safe-area, popover, drawer, forced-colors primitives;
- remove stale visual documentation and misleading names.

### Phase 5: Screen modernization

Implement in order:

1. Today
2. Cases
3. Case Detail
4. Session Intake
5. Transcript Workspace
6. Findings
7. Report
8. Reports Library
9. Settings/Admin

### Phase 6: State and backend hardening

- loading, empty, error, unavailable, stale, retry;
- local draft and explicit sample mode;
- experimental/disabled capabilities;
- backend unreachable and recovery;
- race/cancellation behavior;
- signed immutability and version provenance.

### Phase 7: Accessibility, performance, and polish

- keyboard and screen-reader audit;
- contrast and forced-colors audit;
- 200% zoom and safe-area audit;
- exact responsive screenshots;
- transcript benchmark suite;
- route bundle evidence;
- core end-to-end workflow;
- approved-concept comparison.

### Gate after every phase

Before moving forward:

- characterization and affected tests pass;
- typecheck and lint pass for changed scope;
- no clinical safety or authorization regression exists;
- responsive screenshots for affected screens are reviewed;
- contract/types are synchronized where applicable;
- documentation is updated;
- intentional deviations and exceptions are recorded and approved.

## 18. Documentation deliverables

Maintain or create:

- `docs/frontend/UX_UI_BASELINE_AUDIT.md`
- this master design specification;
- phase-specific implementation plans;
- canonical frontend architecture documentation;
- role matrix and authorization behavior;
- updated `apps/lingualens-app/DESIGN.md` matching live tokens;
- README updates for structure/setup/user-facing behavior;
- CHANGELOG updates only for real behavior changes;
- `docs/frontend/LINGUALENS_UX_UI_MODERNIZATION_REPORT.md`.

The final report contains the initial audit, approved architecture, screen changes, exact viewport screenshot paths/results, accessibility evidence, performance evidence, exact commands/results, remaining intentional deviations, and explicit unresolved external or clinical-validation limits.

## 19. Completion criteria

The modernization is complete only when all prompt acceptance criteria are verified against current evidence. At minimum:

- Today is the sole default work queue.
- Navigation matches Today, Cases, Session, Reports, Settings.
- Session is canonical for Intake, Transcript, Findings, Report.
- Legacy routes redirect safely.
- Monolith responsibilities are separated coherently.
- Backend/sample/local-draft/unavailable modes are explicit.
- Backend failure never creates fake success or patient-like sample substitution.
- Mobile, tablet, and desktop layouts are intentional.
- iPad transcript review uses the approved collapsible/switchable two-pane design.
- Required viewports have no horizontal overflow or sticky-control overlap.
- Clinical safety and authorization gates remain intact.
- Unit, component, contract, backend, Playwright, typecheck, lint, and build gates pass.
- Exact-viewport implementation screenshots are compared with approved concepts.
- Every intentional deviation is documented.
- No new diagnostic claim appears.
- Documentation reflects the actual canonical architecture.

## 20. Scrutinize verdict

The modernization should exist because the current UI duplicates routes, combines data access with presentation, silently retains sample/fallback state, and lacks intentional tablet behavior.

The simpler safe path is not a visual rebuild. It is the approved incremental strangler: preserve the live token normalization and clinical workflow safeguards, introduce one explicit capability/data-mode layer, consolidate one canonical Session route, and modernize each screen after behavior is characterized.

Verdict: **approved for phased planning, not yet for production implementation**. The written specification and phase plans remain mandatory gates.
