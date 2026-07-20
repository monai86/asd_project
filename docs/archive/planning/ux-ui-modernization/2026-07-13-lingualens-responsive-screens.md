# LinguaLens Responsive Screens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved calm clinical workbench, responsive shell, focused Today queue, split Cases, and dominant responsive Session editor without changing clinical behavior.

**Architecture:** Consolidate live tokens first, then implement reusable shell and state primitives. Modernize screens in workflow order, comparing each affected viewport to the approved concept before proceeding.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS, CSS custom properties, Lucide, Vitest, Testing Library, Playwright

---

## File map

- Create `apps/lingualens-app/src/design-system/tokens.css`: authoritative color, spacing, typography, motion, z-index, safe-area tokens.
- Create `apps/lingualens-app/src/design-system/components.css`: shared surfaces and state primitives.
- Create shell components under `src/components/shell/`.
- Create work-queue components under `src/features/work-queue/`.
- Create responsive case components under `src/features/cases/components/`.
- Create Transcript inspector, overflow menu, player, and action bar under `src/features/sessions/transcript/`.
- Update each canonical page to compose feature components.
- Replace stale `apps/lingualens-app/DESIGN.md` with the implemented system.

### Task 1: Consolidate tokens and unified Thai-Latin typography

**Files:**
- Create: `apps/lingualens-app/src/design-system/tokens.css`
- Create: `apps/lingualens-app/src/design-system/components.css`
- Modify: `apps/lingualens-app/src/styles/globals.css`
- Modify: `apps/lingualens-app/src/app/layout.tsx`
- Modify: `apps/lingualens-app/DESIGN.md`
- Modify: `apps/lingualens-app/src/__tests__/design-system.test.tsx`

- [ ] **Step 1: Add token characterization assertions**

```tsx
test("uses the unified Thai-Latin product stack and restrained motion tokens", () => {
  const css = readFileSync(resolve(process.cwd(), "src/design-system/tokens.css"), "utf8");
  expect(css).toContain('--font-product: "Noto Sans Thai", "Noto Sans"');
  expect(css).toContain("--motion-selection: 100ms");
  expect(css).toContain("--motion-popover: 170ms");
  expect(css).toContain("--motion-panel: 220ms");
  expect(css).toContain("--z-popover:");
  expect(css).toContain("--safe-bottom: env(safe-area-inset-bottom, 0px)");
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/design-system.test.tsx`
Expected: FAIL because the authoritative token file does not exist.

- [ ] **Step 3: Move and normalize live tokens**

Start from current `globals.css` values. Add:

```css
:root {
  --font-product: "Noto Sans Thai", "Noto Sans", system-ui, sans-serif;
  --font-accessible-latin: "Atkinson Hyperlegible", var(--font-product);
  --motion-selection: 100ms;
  --motion-popover: 170ms;
  --motion-panel: 220ms;
  --z-dropdown: 20;
  --z-sticky: 30;
  --z-modal-backdrop: 40;
  --z-modal: 50;
  --z-toast: 60;
  --z-tooltip: 70;
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
}
```

Import tokens/components before Tailwind layers. Use `font-family: var(--font-product)` on body. Optional accessibility mode applies `--font-accessible-latin` only to Latin-only content.

- [ ] **Step 4: Add forced-colors and reduced-motion rules**

```css
@media (forced-colors: active) {
  :focus-visible { outline: 2px solid Highlight; }
  [aria-selected="true"] { border: 2px solid Highlight; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

- [ ] **Step 5: Rewrite `DESIGN.md` from implemented tokens**

Document color roles, font modes, fixed type scale, motion tiers, radii, state vocabulary, safe areas, forced colors, and the prohibition on decorative glass/gradient naming.

- [ ] **Step 6: Run tests and typecheck**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/design-system.test.tsx && npm run typecheck`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/lingualens-app/src/design-system apps/lingualens-app/src/styles/globals.css apps/lingualens-app/src/app/layout.tsx apps/lingualens-app/DESIGN.md apps/lingualens-app/src/__tests__/design-system.test.tsx
git commit -m "style: consolidate clinical design tokens" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 2: Implement the responsive application shell

**Files:**
- Create: `apps/lingualens-app/src/components/shell/workbench-shell.tsx`
- Create: `apps/lingualens-app/src/components/shell/primary-navigation.tsx`
- Create: `apps/lingualens-app/src/components/shell/mobile-bottom-navigation.tsx`
- Create: `apps/lingualens-app/src/components/shell/tablet-navigation.tsx`
- Modify: `apps/lingualens-app/src/components/app-shell.tsx`
- Modify: `apps/lingualens-app/src/__tests__/design-system.test.tsx`

- [ ] **Step 1: Add failing shell semantics tests**

```tsx
test("renders one canonical navigation appropriate to the viewport", () => {
  render(<WorkbenchShell active="Today"><main>content</main></WorkbenchShell>);
  expect(screen.getAllByRole("navigation", { name: "Primary navigation" })).toHaveLength(1);
  expect(screen.getByRole("link", { name: "Today" })).toHaveAttribute("aria-current", "page");
});

test("keeps mobile content clear of bottom navigation", () => {
  render(<WorkbenchShell active="Cases"><main data-testid="content">content</main></WorkbenchShell>);
  expect(screen.getByTestId("content").parentElement).toHaveClass("workbench-content");
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/design-system.test.tsx`
Expected: FAIL until the new shell exists.

- [ ] **Step 3: Implement shared navigation source and structural breakpoints**

Use CSS media queries to display bottom nav below 768 px, tablet rail at 768–1023 px, compact sidebar at 1024–1279 px, and expanded sidebar at 1280 px. Do not render duplicate navigations and hide them with CSS; render the appropriate client variant after a stable media-query hook or use CSS with duplicate links removed from the accessibility tree via display.

- [ ] **Step 4: Implement safe-area content spacing**

```css
.workbench-content {
  min-width: 0;
  padding-bottom: calc(var(--mobile-nav-height, 0px) + var(--safe-bottom));
}
@media (min-width: 768px) { .workbench-content { padding-bottom: 2rem; } }
```

- [ ] **Step 5: Run shell tests and exact viewport smoke captures**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/design-system.test.tsx src/__tests__/app-shell-auth-gate.test.tsx`
Expected: PASS.

Capture `/today` at all five required viewports and verify exactly one visible/accessible navigation, no overlap, and no horizontal overflow.

- [ ] **Step 6: Commit**

```bash
git add apps/lingualens-app/src/components/shell apps/lingualens-app/src/components/app-shell.tsx apps/lingualens-app/src/design-system apps/lingualens-app/src/__tests__
git commit -m "feat: add responsive workbench shell" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 3: Build the focused Today work queue

**Files:**
- Create: `apps/lingualens-app/src/features/work-queue/types.ts`
- Create: `apps/lingualens-app/src/features/work-queue/services/work-queue-service.ts`
- Create: `apps/lingualens-app/src/features/work-queue/components/work-queue.tsx`
- Create: `apps/lingualens-app/src/features/work-queue/components/work-queue-row.tsx`
- Create: `apps/lingualens-app/src/features/work-queue/components/today-context-rail.tsx`
- Modify: `apps/lingualens-app/src/components/work-queue-dashboard.tsx`
- Create: `apps/lingualens-app/src/__tests__/work-queue.test.tsx`

- [ ] **Step 1: Write failing hierarchy tests**

```tsx
test("renders one prioritized queue and one Start session action", () => {
  render(<WorkQueue state={confirmed(queueFixture)} />);
  expect(screen.getAllByRole("link", { name: "Start session" })).toHaveLength(1);
  expect(screen.getByRole("heading", { name: "Needs action" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Ready for sign-off" })).toBeInTheDocument();
});

test("each queue row exposes one next action", () => {
  render(<WorkQueue state={confirmed(queueFixture)} />);
  for (const row of screen.getAllByTestId("work-queue-row")) {
    expect(within(row).getAllByRole("link")).toHaveLength(1);
  }
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/work-queue.test.tsx`
Expected: FAIL because the focused queue does not exist.

- [ ] **Step 3: Implement typed queue groups**

```ts
export type WorkQueueGroup = "needs-action" | "processing" | "ready-review" | "ready-signoff" | "recent";
export type WorkQueueItem = {
  id: string;
  group: WorkQueueGroup;
  caseLabel: string;
  sessionDate: string;
  task: string;
  status: string;
  reason: string;
  action: { label: string; href: string };
};
```

Render groups in the approved priority order. Context rail contains today's sessions and exceptional backend status only. Delete repeated quick actions, safety reminders, session lists, and results from lower Today content.

- [ ] **Step 4: Add remote-state branches**

Skeleton on loading, one instructive empty state, inline retry on error, and unavailable state without sample data.

- [ ] **Step 5: Verify tests and approved visual direction**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/work-queue.test.tsx src/__tests__/pages.test.tsx`
Expected: PASS.

Compare exact viewport screenshots with Focused workbench direction A. Record intentional differences.

- [ ] **Step 6: Commit**

```bash
git add apps/lingualens-app/src/features/work-queue apps/lingualens-app/src/components/work-queue-dashboard.tsx apps/lingualens-app/src/__tests__
git commit -m "feat: focus Today on prioritized work" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 4: Implement responsive Cases and deliberate session selection

**Files:**
- Modify: `apps/lingualens-app/src/features/cases/components/case-list.tsx`
- Modify: `apps/lingualens-app/src/features/cases/components/case-detail.tsx`
- Create: `apps/lingualens-app/src/features/cases/components/start-session-selector.tsx`
- Create: `apps/lingualens-app/src/__tests__/cases-responsive.test.tsx`

- [ ] **Step 1: Write behavior and intent tests**

```tsx
test("start-session intent requires deliberate case selection", () => {
  render(<CasesWorkspace intent="start-session" state={confirmed(caseFixture)} />);
  expect(screen.getByRole("heading", { name: "Choose a case to start a session" })).toBeInTheDocument();
  expect(screen.queryByText(/session created/i)).not.toBeInTheDocument();
});

test("mobile case list uses rows rather than the desktop table", () => {
  render(<CaseList cases={caseFixture} layout="mobile" />);
  expect(screen.getByRole("list", { name: "Cases" })).toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/cases-responsive.test.tsx`
Expected: FAIL until the responsive interfaces exist.

- [ ] **Step 3: Implement list/detail transformations**

Mobile uses a semantic list of compact rows. Tablet/desktop use split view when both panes preserve minimum widths. Case detail sections are Overview, Sessions, Goals, Progress, Reports, and authorized Care team.

- [ ] **Step 4: Implement deliberate selector**

Selection enables “Start session for {case code}”; submitting calls the backend and routes only after the backend returns the created session ID.

- [ ] **Step 5: Verify tests and screenshots**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/cases-responsive.test.tsx src/__tests__/cases-workspace-client.test.tsx`
Expected: PASS.

Capture Cases/list/detail/selector at 390x844, 768x1024, and 1440x900. Verify clinician filters appear only when authorized.

- [ ] **Step 6: Commit**

```bash
git add apps/lingualens-app/src/features/cases apps/lingualens-app/src/__tests__
git commit -m "feat: add responsive case workspace" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 5: Implement persistent Session context and Intake

**Files:**
- Modify: `apps/lingualens-app/src/features/sessions/components/session-context-header.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/intake/session-intake-view.tsx`
- Create: `apps/lingualens-app/src/__tests__/session-context-header.test.tsx`

- [ ] **Step 1: Write failing context tests**

```tsx
test("shows clinical context and explicit data mode across Session views", () => {
  render(<SessionContextHeader context={contextFixture} />);
  expect(screen.getByText("C-1024")).toBeInTheDocument();
  expect(screen.getByText("Consent granted")).toBeInTheDocument();
  expect(screen.getByText("Backend mode")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Transcript" })).toHaveAttribute("href", "/sessions/session-1?view=transcript");
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/session-context-header.test.tsx`
Expected: FAIL until the context header is implemented.

- [ ] **Step 3: Implement the header and validated links**

Use a compact definition list for case/session/source/consent/status/mode and canonical Session links. Unknown context is “Unavailable”, never a fabricated label.

- [ ] **Step 4: Modernize Intake without changing gates**

Use existing source paths, explicit source selection, consent, upload/processing states, quality warnings, experimental labeling, and one next action. Keep raw audio memory-only.

- [ ] **Step 5: Run Intake suites and screenshots**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/session-context-header.test.tsx src/__tests__/session-intake-flow.test.tsx src/__tests__/browser-audio-recorder.test.tsx`
Expected: PASS.

Capture Intake at every required viewport and verify context stays visible without covering content.

- [ ] **Step 6: Commit**

```bash
git add apps/lingualens-app/src/features/sessions apps/lingualens-app/src/__tests__
git commit -m "feat: modernize session intake context" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 6: Implement the approved Transcript Workspace

**Files:**
- Create: `apps/lingualens-app/src/features/sessions/transcript/transcript-workspace.tsx`
- Create: `apps/lingualens-app/src/features/sessions/transcript/transcript-inspector.tsx`
- Create: `apps/lingualens-app/src/features/sessions/transcript/transcript-line-menu.tsx`
- Create: `apps/lingualens-app/src/features/sessions/transcript/sticky-audio-player.tsx`
- Create: `apps/lingualens-app/src/features/sessions/transcript/sticky-review-bar.tsx`
- Modify: `apps/lingualens-app/src/components/transcript-editor-panel.tsx`
- Modify: `apps/lingualens-app/src/__tests__/transcript-editor-panel.test.tsx`

- [ ] **Step 1: Add failing interaction tests**

```tsx
test("selected editable line exposes aria-selected and overflow actions", async () => {
  const user = userEvent.setup();
  render(<TranscriptWorkspace model={transcriptFixture} />);
  const line = screen.getByRole("option", { name: /line 1/i });
  await user.click(within(line).getByLabelText("Utterance text 1"));
  expect(line).toHaveAttribute("aria-selected", "true");
  await user.click(within(line).getByRole("button", { name: "More actions for line 1" }));
  expect(screen.getByRole("menuitem", { name: "Split line" })).toBeVisible();
});

test("save status is announced", async () => {
  render(<TranscriptWorkspace model={{ ...transcriptFixture, saveStatus: "saving" }} />);
  expect(screen.getByRole("status")).toHaveTextContent("Saving transcript");
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/transcript-editor-panel.test.tsx`
Expected: FAIL for missing semantics and overflow behavior.

- [ ] **Step 3: Implement dominant desktop layout**

Use `grid-template-columns: minmax(0, 3fr) minmax(16rem, 1fr)` with the editor never below 60%. Inspector collapse removes its column; resizing clamps between 16 rem and 32% of workspace width and uses immediate updates.

- [ ] **Step 4: Implement iPad and mobile transformations**

At 768–1023 px, keep transcript minimum width and offer Audio/QA segmented inspector with Hide inspector. Below 768 px, use one column, sticky safe-area player/action bar, and matching bottom padding.

- [ ] **Step 5: Implement accessible selected lines and overflow menu**

Use a listbox/option pattern only if line selection behaves as single selection; otherwise use buttons plus `aria-pressed`. The approved contract requires `aria-selected`, so implement `role="listbox"` and `role="option"` while keeping textarea/select inputs directly editable. Use native popover or a portal menu with focus restoration and Escape support.

- [ ] **Step 6: Prevent repeated line lookup scans**

Create `const lineIndexById = useMemo(() => new Map(lines.map((line, index) => [line.lineId, index])), [lines]);` and replace render-time `findIndex` calls.

- [ ] **Step 7: Run tests and exact viewport comparison**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/transcript-editor-panel.test.tsx src/__tests__/session-workspace-audio-auth.test.tsx`
Expected: PASS.

Capture Transcript at all exact viewports. Verify editor dominance, inspector clipping, iPad collapse/switching, direct editing, selected-line focus, safe areas, and overflow actions against the approved v2 concept.

- [ ] **Step 8: Commit**

```bash
git add apps/lingualens-app/src/features/sessions/transcript apps/lingualens-app/src/components/transcript-editor-panel.tsx apps/lingualens-app/src/__tests__
git commit -m "feat: add responsive transcript workspace" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 7: Modernize Findings, Report, Reports, and Settings

**Files:**
- Modify: `apps/lingualens-app/src/features/sessions/findings/session-findings-view.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/report/session-report-view.tsx`
- Create: `apps/lingualens-app/src/features/reports/components/reports-library.tsx`
- Modify: `apps/lingualens-app/src/features/settings/components/settings-workspace.tsx`
- Create: `apps/lingualens-app/src/__tests__/downstream-workspaces.test.tsx`

- [ ] **Step 1: Write safety and ownership tests**

```tsx
test("findings stay locked until reviewed transcript gates are confirmed", () => {
  render(<SessionFindingsView model={{ ...findingsFixture, eligibility: "blocked" }} />);
  expect(screen.getByRole("heading", { name: "Findings unavailable" })).toBeInTheDocument();
  expect(screen.queryByText(/diagnos/i)).not.toBeInTheDocument();
});

test("signed report editor is read-only and offers a revision action", () => {
  render(<SessionReportView model={{ ...reportFixture, signOffState: "signed" }} />);
  expect(screen.getByRole("textbox", { name: "Report draft" })).toHaveAttribute("readonly");
  expect(screen.getByRole("button", { name: "Create report revision" })).toBeEnabled();
});

test("report library has no independent editor", () => {
  render(<ReportsLibrary state={confirmed(reportRows)} />);
  expect(screen.queryByRole("textbox", { name: "Report draft" })).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/downstream-workspaces.test.tsx`
Expected: FAIL until the screen contracts are implemented.

- [ ] **Step 3: Implement Findings and Report**

Findings shows provenance, reviewed version, feature-set version, descriptive cues, missing data, limitations, and AI disposition. Report shows one shared editor, source/safety inspector, save/sign/export states, provenance, and immutable signed snapshot behavior.

- [ ] **Step 4: Implement Reports library and Settings sections**

Reports groups states and provides one canonical next-action link. Settings renders only authorized sections and explicit remote states; ordinary therapists never receive admin controls or requests.

- [ ] **Step 5: Run affected suites and screenshots**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/downstream-workspaces.test.tsx src/__tests__/settings-workspace-client.test.tsx src/__tests__/pages.test.tsx`
Expected: PASS.

Capture affected screens at 390x844, 768x1024, and 1440x900.

- [ ] **Step 6: Commit**

```bash
git add apps/lingualens-app/src/features apps/lingualens-app/src/__tests__
git commit -m "feat: modernize downstream workspaces" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 8: Run the responsive screens phase gate

**Files:**
- Modify: `docs/frontend/LINGUALENS_UX_UI_MODERNIZATION_REPORT.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md` because user-facing behavior changed

- [ ] **Step 1: Run all frontend tests, typecheck, lint, and build**

Run: `cd apps/lingualens-app && npm test && npm run typecheck && npm run lint && npm run build`
Expected: exit 0 for every command; record test counts and lint warnings.

- [ ] **Step 2: Run backend safety/authorization suites**

Run: `pytest apps/api/tests/test_workflow.py apps/api/tests/test_report_service_v1.py apps/api/tests/test_organization_admin_routes.py apps/api/tests/test_privacy_operations.py -q`
Expected: PASS.

- [ ] **Step 3: Capture the exact viewport matrix**

Capture Today, Cases, Case Detail, Intake, Transcript, Findings, Report, Reports, Settings therapist, and Settings admin at 390x844, 768x1024, 1024x1366, 1280x800, and 1440x900.

- [ ] **Step 4: Review visual and accessibility evidence**

Verify approved hierarchy, no horizontal overflow, no safe-area overlap, 44 px touch hit areas, focus visibility, direct transcript editing, inspector access, and no unauthorized admin surface.

- [ ] **Step 5: Update documentation and commit**

```bash
git add docs/frontend README.md CHANGELOG.md
git commit -m "docs: record responsive modernization evidence" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```
