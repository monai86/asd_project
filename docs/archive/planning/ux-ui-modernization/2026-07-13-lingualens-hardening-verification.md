# LinguaLens Hardening and Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove remote-state correctness, accessibility, performance budgets, real-contract end-to-end behavior, and requirement-by-requirement completion of the UX/UI modernization.

**Architecture:** Add deterministic race and contract tests, reusable Playwright assertions, and a transcript benchmark harness. Treat evidence artifacts and the final report as release gates rather than retrospective documentation.

**Tech Stack:** Vitest, Testing Library, Playwright, axe-compatible accessibility checks where installed, Chrome Performance APIs, Next.js bundle output, FastAPI, pytest

---

## File map

- Create `apps/lingualens-app/src/__tests__/workflow-races.test.tsx`: request identity, cancellation, duplicate submission, stale invalidation.
- Create `apps/lingualens-app/e2e/responsive-workbench.spec.ts`: exact viewport assertions.
- Create `apps/lingualens-app/e2e/demo-isolation.spec.ts`: gated sample behavior.
- Create `apps/lingualens-app/e2e/backend-contract.spec.ts`: contract-faithful workflow and recovery.
- Create `apps/lingualens-app/e2e/accessibility-workbench.spec.ts`: keyboard/focus/semantics.
- Create `apps/lingualens-app/benchmarks/transcript-workspace.bench.spec.ts`: 100/500/1,000-line metrics.
- Create `apps/lingualens-app/scripts/check-bundle-budgets.mjs`: route budget enforcement.
- Create `docs/frontend/LINGUALENS_UX_UI_MODERNIZATION_REPORT.md`: mandatory final evidence.
- Update Playwright config and package scripts.

### Task 1: Cover races, cancellation, duplicate submissions, and stale invalidation

**Files:**
- Create: `apps/lingualens-app/src/__tests__/workflow-races.test.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/hooks/use-session-workspace.ts`
- Modify: `apps/lingualens-app/src/features/sessions/state/session-workflow-reducer.ts`

- [ ] **Step 1: Write failing request-order tests**

```tsx
test("late response from a previous session cannot replace current state", async () => {
  const first = deferred<SessionModel>();
  const second = deferred<SessionModel>();
  service.load.mockImplementation((id) => id.sessionId === "one" ? first.promise : second.promise);
  const { result, rerender } = renderHook(({ sessionId }) => useSessionWorkspace({ sessionId, view: "intake" }), {
    initialProps: { sessionId: "one" },
  });
  rerender({ sessionId: "two" });
  second.resolve(sessionTwo);
  await waitFor(() => expect(result.current.context.sessionId).toBe("two"));
  first.resolve(sessionOne);
  await act(async () => Promise.resolve());
  expect(result.current.context.sessionId).toBe("two");
});
```

- [ ] **Step 2: Add duplicate and navigation-during-save tests**

```tsx
test("prevents duplicate transcript submissions", async () => {
  const user = userEvent.setup();
  render(<SessionTranscriptView model={savingModel} />);
  await user.dblClick(screen.getByRole("button", { name: "Save transcript" }));
  expect(savingModel.onSave).toHaveBeenCalledTimes(0);
  expect(screen.getByRole("button", { name: "Saving transcript" })).toBeDisabled();
});

test("navigation during save leaves the new session authoritative", async () => {
  render(<SessionWorkspace sessionId="one" view="transcript" />);
  await startSave();
  navigateToSession("two");
  resolveSaveForSession("one");
  expect(screen.getByText("Session two")).toBeInTheDocument();
});
```

- [ ] **Step 3: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/workflow-races.test.tsx`
Expected: at least one race assertion fails until identity sequencing and submit locks are complete.

- [ ] **Step 4: Implement request sequencing and mutation identity guards**

Store the current session identity and request sequence in refs. Abort cancellable reads. Before applying any response, require both sequence and session identity match. Disable repeated mutation submission and use backend idempotency keys if the endpoint contract supports them.

- [ ] **Step 5: Add stale downstream tests**

```ts
test("transcript edit invalidates findings and report provenance", () => {
  const next = sessionWorkflowReducer(readyForReport, { type: "transcript-edited", lines: changedLines });
  expect(next.findings.status).toBe("stale");
  expect(next.report.status).toBe("stale");
  expect(next.transcriptAttested).toBe(false);
});
```

- [ ] **Step 6: Run and confirm GREEN**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/workflow-races.test.tsx src/__tests__/session-workflow-reducer.test.ts`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/lingualens-app/src/features/sessions apps/lingualens-app/src/__tests__/workflow-races.test.tsx
git commit -m "test: harden session race behavior" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 2: Add exact viewport Playwright coverage

**Files:**
- Create: `apps/lingualens-app/e2e/responsive-workbench.spec.ts`
- Modify: `apps/lingualens-app/playwright.config.ts`
- Modify: `apps/lingualens-app/package.json`

- [ ] **Step 1: Add the viewport matrix and shared assertions**

```ts
const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  { name: "small-desktop", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

async function expectNoHorizontalOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
}
```

- [ ] **Step 2: Add screen assertions for each viewport**

For every viewport, visit Today, Cases, Session Transcript, Reports, and Settings. Assert no overflow, usable navigation, visible primary action, and content clear of sticky controls. At 768 px assert Transcript inspector can switch/collapse; at 1440 px assert editor width is at least 60% of workspace.

- [ ] **Step 3: Add touch-target geometry checks**

```ts
for (const control of await page.locator("[data-touch-target]").all()) {
  const box = await control.boundingBox();
  expect(box && box.width >= 44 && box.height >= 44).toBe(true);
}
```

Mark touch controls explicitly; do not apply this assertion to dense desktop-only controls.

- [ ] **Step 4: Run and confirm failures expose unfinished responsive behavior**

Run: `cd apps/lingualens-app && npx playwright test e2e/responsive-workbench.spec.ts`
Expected: PASS only after all affected responsive contracts are implemented. Fix product code, not the evidence assertions.

- [ ] **Step 5: Add a package script and commit**

Add `"e2e:responsive": "playwright test e2e/responsive-workbench.spec.ts"`.

```bash
git add apps/lingualens-app/e2e/responsive-workbench.spec.ts apps/lingualens-app/playwright.config.ts apps/lingualens-app/package.json apps/lingualens-app/package-lock.json
git commit -m "test: verify responsive workbench viewports" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 3: Add accessibility and focus-flow Playwright coverage

**Files:**
- Create: `apps/lingualens-app/e2e/accessibility-workbench.spec.ts`
- Modify: `apps/lingualens-app/package.json`

- [ ] **Step 1: Test transcript selection and save announcements**

```ts
test("transcript selection, overflow, and save remain keyboard complete", async ({ page }) => {
  await openSeededTranscript(page);
  await page.keyboard.press("Tab");
  const firstLine = page.getByRole("option", { name: /line 1/i });
  await firstLine.focus();
  await page.keyboard.press("Enter");
  await expect(firstLine).toHaveAttribute("aria-selected", "true");
  await page.getByRole("button", { name: "More actions for line 1" }).press("Enter");
  await expect(page.getByRole("menuitem", { name: "Split line" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "More actions for line 1" })).toBeFocused();
});
```

- [ ] **Step 2: Test `aria-live`, errors, and focus restoration**

Trigger save, job processing, and safe error responses. Assert status text changes inside live regions. Open/close inspector drawer and verify focus returns to its trigger. Submit an invalid field and verify `aria-describedby` references visible error text.

- [ ] **Step 3: Test 200% zoom and forced colors**

Use `page.evaluate(() => { document.documentElement.style.zoom = "2"; })` for layout evidence and Chromium forced-colors emulation when supported. Assert controls remain visible, selection remains distinguishable, and no horizontal page overflow appears.

- [ ] **Step 4: Verify shortcuts avoid browser defaults**

Use only documented non-conflicting combinations, such as `Alt+Shift+S` for Save transcript, and ensure editable fields do not intercept browser refresh, find, close-tab, or address-bar shortcuts.

- [ ] **Step 5: Run and commit**

Run: `cd apps/lingualens-app && npx playwright test e2e/accessibility-workbench.spec.ts`
Expected: PASS.

```bash
git add apps/lingualens-app/e2e/accessibility-workbench.spec.ts apps/lingualens-app/package.json apps/lingualens-app/package-lock.json
git commit -m "test: verify workbench accessibility flows" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 4: Cover explicit demo isolation and real backend contract

**Files:**
- Create: `apps/lingualens-app/e2e/demo-isolation.spec.ts`
- Create: `apps/lingualens-app/e2e/backend-contract.spec.ts`
- Modify: `apps/lingualens-app/playwright.config.ts`

- [ ] **Step 1: Add demo gating/isolation tests**

```ts
test("demo mode is unavailable when disabled", async ({ page }) => {
  const response = await page.goto("/demo/dashboard");
  expect(response?.status()).toBe(404);
});

test("enabled demo stays labeled and isolated", async ({ page }) => {
  await page.goto("/demo/dashboard");
  await expect(page.getByText("Sample Data")).toBeVisible();
  expect(await page.evaluate(() => Object.keys(sessionStorage).every((key) => key.startsWith("lingualens.demo.")))).toBe(true);
});
```

Run these in separate projects/configurations with demo mode false and true.

- [ ] **Step 2: Add contract-faithful backend workflow test**

Use the real FastAPI memory repository via Playwright `webServer`. Create a case/session/transcript through authenticated API calls, then drive review, QA, attestation, findings, report generation, sign-off, and immutable signed view in the browser.

- [ ] **Step 3: Add backend recovery test**

Route one request to a controlled 503, assert visible error/retry with no sample data, restore the route to the real backend, click Retry, and assert backend-confirmed content appears.

- [ ] **Step 4: Run both environments**

Run: `cd apps/lingualens-app && npx playwright test e2e/demo-isolation.spec.ts e2e/backend-contract.spec.ts`
Expected: PASS in explicit demo and real-contract projects. Mock-only fixtures do not satisfy the backend-contract test.

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/e2e apps/lingualens-app/playwright.config.ts
git commit -m "test: cover demo isolation and backend contract" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 5: Add transcript performance benchmarks

**Files:**
- Create: `apps/lingualens-app/benchmarks/transcript-workspace.bench.spec.ts`
- Create: `apps/lingualens-app/benchmarks/fixtures/transcript-lines.ts`
- Modify: `apps/lingualens-app/package.json`

- [ ] **Step 1: Create deterministic line fixtures**

```ts
export function makeTranscriptLines(count: number): TranscriptLine[] {
  return Array.from({ length: count }, (_, index) => ({
    lineId: `line-${index}`,
    speaker: index % 2 === 0 ? "CHI" : "THER",
    text: `Non-identifying benchmark utterance ${index}`,
    startMs: index * 1200,
    endMs: index * 1200 + 900,
  }));
}
```

- [ ] **Step 2: Measure render, keystroke, selection, filter, scroll, and memory**

For 100, 500, and 1,000 lines, record navigation-to-ready time, `performance.now()` around one keystroke and selection update, filter completion, scroll frame samples, and heap size where Chromium exposes it. Repeat at least five times and report median plus p95.

- [ ] **Step 3: Encode budgets**

Fail when keystroke p95 exceeds 50 ms at 500 lines or 100 ms at 1,000 lines, or scroll falls below 50 fps at 500 lines or 45 fps at 1,000 lines. Record reference machine/browser and warm/cold conditions.

- [ ] **Step 4: Run baseline and decide dynamic loading/virtualization from evidence**

Run: `cd apps/lingualens-app && npx playwright test benchmarks/transcript-workspace.bench.spec.ts`
Expected: PASS within budgets, or produce a documented failure requiring remediation. Add virtualization only if the non-virtualized editor fails and the chosen implementation preserves selection, focus, ARIA, audio synchronization, and direct editing.

- [ ] **Step 5: Add script and commit**

Add `"bench:transcript": "playwright test benchmarks/transcript-workspace.bench.spec.ts"`.

```bash
git add apps/lingualens-app/benchmarks apps/lingualens-app/package.json apps/lingualens-app/package-lock.json
git commit -m "test: benchmark long transcript editing" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 6: Enforce route-level JavaScript budgets

**Files:**
- Create: `apps/lingualens-app/scripts/check-bundle-budgets.mjs`
- Create: `apps/lingualens-app/bundle-budgets.json`
- Modify: `apps/lingualens-app/package.json`

- [ ] **Step 1: Record approved budgets**

```json
{
  "sharedFirstLoadKb": 112,
  "routes": {
    "/today": 213,
    "/cases": 242,
    "/reports": 229,
    "/settings": 232,
    "/sessions/[sessionId]": 230
  },
  "maxNewClientChunkKb": 80
}
```

Values follow the approved contract: baseline plus allowed tolerance, with Session capped at its 230 kB baseline and targeted below 210 kB.

- [ ] **Step 2: Implement the build-output parser**

Read Next.js build output from stdin or a saved build log, parse each route's First Load JS value, compare to `bundle-budgets.json`, print every measured route, and exit 1 on exceedance. Also inspect `.next/static/chunks` gzip sizes for new client chunks.

- [ ] **Step 3: Add a verification script**

Add `"verify:bundle": "next build 2>&1 | tee .local/next-build.log && node scripts/check-bundle-budgets.mjs .local/next-build.log"`. Ensure `.local/` remains ignored and never committed.

- [ ] **Step 4: Run and resolve or document exceptions**

Run: `cd apps/lingualens-app && npm run verify:bundle`
Expected: PASS. Any exceedance requires remediation or a user-approved exception recorded in the final report and budget file rationale.

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/scripts/check-bundle-budgets.mjs apps/lingualens-app/bundle-budgets.json apps/lingualens-app/package.json apps/lingualens-app/package-lock.json
git commit -m "build: enforce frontend bundle budgets" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 7: Produce final exact-viewport visual evidence

**Files:**
- Create: `docs/frontend/modernization-screenshots/`
- Create: `docs/frontend/visual-deviations.md`

- [ ] **Step 1: Capture all canonical screens**

Capture Today, Cases, Case Detail, Intake, Transcript, Findings, Report, Reports, therapist Settings, and admin Settings at all five exact viewports. Use stable seeded non-identifying fixtures and backend-confirmed states.

- [ ] **Step 2: Compare against approved concepts and baseline**

For each screenshot, record layout used, overflow result, primary action visibility, transcript/editor usability, inspector access, and comparison with Focused workbench A and responsive Transcript v2.

- [ ] **Step 3: Record every intentional deviation**

`visual-deviations.md` contains screen, viewport, approved concept, implemented difference, reason, accessibility/performance effect, and approval status. An empty file states “No intentional deviations remain” with capture date.

- [ ] **Step 4: Verify safe areas and 200% zoom manually**

Capture at least mobile Today/Transcript and tablet Transcript at 200% zoom. Verify sticky controls do not cover content and focus remains visible.

- [ ] **Step 5: Commit evidence**

```bash
git add docs/frontend/modernization-screenshots docs/frontend/visual-deviations.md
git commit -m "docs: add final responsive visual evidence" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 8: Complete the mandatory final report and completion audit

**Files:**
- Create: `docs/frontend/LINGUALENS_UX_UI_MODERNIZATION_REPORT.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `PROJECT_STATUS.md`

- [ ] **Step 1: Write the report from evidence**

Include initial audit, approved architecture, screen-by-screen changes, responsive evidence table, accessibility evidence, performance/bundle results, exact tests/commands, contract validation, role matrix, race coverage, visual deviations, and unresolved external/clinical limits.

- [ ] **Step 2: Run the full frontend gate**

Run inside `apps/lingualens-app`:

```bash
npm test
npm run typecheck
npm run lint
npm run build
npm run verify:bundle
npm run e2e:smoke
npm run e2e:responsive
npx playwright test e2e/accessibility-workbench.spec.ts e2e/demo-isolation.spec.ts e2e/backend-contract.spec.ts
npm run bench:transcript
```

Expected: every command exits 0. Record exact counts, warnings, bundle values, and benchmark percentiles.

- [ ] **Step 3: Run the backend and project gate**

Run:

```bash
pytest apps/api/tests/test_workflow.py apps/api/tests/test_report_service_v1.py apps/api/tests/test_organization_admin_routes.py apps/api/tests/test_privacy_operations.py -q
bash scripts/check_project.sh
```

Expected: exit 0. Record counts and duration.

- [ ] **Step 4: Audit every acceptance criterion**

Create a table with each numbered acceptance criterion, authoritative file/test/screenshot/command evidence, status, and unresolved item. “Not observed” is not proof; missing evidence remains incomplete.

- [ ] **Step 5: Run final hygiene checks**

Run:

```bash
rtk git status --short
rtk rg -n "diagnos(e|is|tic)|ASD positive|Thai clinical validation" apps/lingualens-app/src
rtk find . -path '*/.next/*' -o -path '*/dist/*' -o -path '*/node_modules/*' -o -name '*.tsbuildinfo'
```

Expected: no generated artifacts staged; any safety-language hit is reviewed and documented as a prohibition/education context rather than a new claim.

- [ ] **Step 6: Scrutinize end to end**

Trace Today action → Cases selection → Session Intake → Transcript save/QA/attest → Findings → Report → sign-off/export through real code and backend calls. Confirm every claim in the final report against the traced path and test evidence.

- [ ] **Step 7: Commit final documentation**

```bash
git add docs/frontend/LINGUALENS_UX_UI_MODERNIZATION_REPORT.md README.md CHANGELOG.md PROJECT_STATUS.md
git commit -m "docs: complete LinguaLens UX modernization report" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```
