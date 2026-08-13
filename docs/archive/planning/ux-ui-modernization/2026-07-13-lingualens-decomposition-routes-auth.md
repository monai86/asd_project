# LinguaLens Decomposition, Routes, and Authorization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Diagnose the existing save failure, split workflow orchestration into focused feature units, consolidate canonical routes, and enforce Settings authorization at backend and server data boundaries.

**Architecture:** Characterize current safe behavior before extraction. Move transport calls into feature services and workflow transitions into reducers/hooks, then make routes thin server compositions. Keep backend authorization authoritative and prevent unauthorized admin data requests.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Vitest, Testing Library, Playwright, FastAPI, pytest

---

## File map

- Create `apps/lingualens-app/src/features/sessions/state/session-view.ts`: canonical view validation and legacy mapping.
- Create `apps/lingualens-app/src/features/sessions/state/session-workflow-reducer.ts`: UI workflow transitions and invalidation.
- Create `apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts`: backend orchestration.
- Create `apps/lingualens-app/src/features/sessions/components/session-workspace.tsx`: feature container.
- Create focused Intake, Transcript, Findings, and Report view components under `features/sessions/`.
- Create `apps/lingualens-app/src/features/settings/services/settings-access.ts`: role matrix and section authorization.
- Create `apps/lingualens-app/src/features/settings/components/settings-workspace.tsx`: role-safe settings composition.
- Modify canonical and legacy route files under `src/app/`.
- Modify backend security/admin routes only where required for role-safe data responses.

### Task 1: Diagnose and fix the pasted-transcript smoke failure

**Files:**
- Modify: `apps/lingualens-app/e2e/therapist-workflow.smoke.spec.ts`
- Modify: `apps/lingualens-app/src/components/session-workspace-client.tsx`
- Modify: `apps/lingualens-app/src/lib/api.ts`
- Test: `apps/api/tests/test_workflow.py`
- Create: `docs/frontend/debug-ledgers/pasted-transcript-save-2026-07-13.md`

- [ ] **Step 1: Reproduce the unchanged failure**

Run: `cd apps/lingualens-app && npm run e2e:smoke`
Expected baseline: 3 failures at the `/record?mode=paste` to `/review-transcript?...` transition. If behavior differs, record the fresh output and trace that behavior instead.

- [ ] **Step 2: Add a response breadcrumb to the Playwright test**

```ts
const mutationResponses: Array<{ url: string; status: number }> = [];
page.on("response", (response) => {
  if (/\/api\/v1\/(sessions|transcripts)/.test(response.url())) {
    mutationResponses.push({ url: response.url(), status: response.status() });
  }
});
```

On transition timeout, attach `JSON.stringify(mutationResponses, null, 2)` to the test output. Do not log request bodies or transcript text.

- [ ] **Step 3: Run the disproof for the leading hypothesis**

Run: `cd apps/lingualens-app && npm run e2e:smoke`
Expected: determine whether session/transcript mutation returns a non-2xx response. Record the response status and whether `router.push` is reached in the debug ledger.

- [ ] **Step 4: Write the failing regression test at the proven boundary**

If the backend rejects the mutation, add a backend test that reproduces the exact authorized request and expected success status. If the backend succeeds but navigation is skipped, add this frontend test:

```tsx
test("navigates after the backend confirms a pasted transcript save", async () => {
  const user = userEvent.setup();
  render(<SessionWorkspaceClient view="record" mode="paste" />);
  await user.clear(screen.getByTestId("transcript-input"));
  await user.type(screen.getByTestId("transcript-input"), "CHI: sample utterance");
  await user.click(screen.getByTestId("save-transcript-button"));
  await waitFor(() => expect(routerPush).toHaveBeenCalledWith(expect.stringContaining("/review-transcript?")));
});
```

- [ ] **Step 5: Implement the minimal proven fix**

Keep backend confirmation mandatory. Replace broad catch handling with `ApiError` narrowing so the UI exposes a generic retryable error while tests can assert status. Do not navigate on failed persistence.

- [ ] **Step 6: Verify the regression and smoke paths**

Run the new focused test, then `cd apps/lingualens-app && npm run e2e:smoke`.
Expected: focused regression PASS and 3/3 smoke tests PASS before route expectations are migrated.

- [ ] **Step 7: Commit**

```bash
git add apps/lingualens-app/e2e apps/lingualens-app/src apps/api/tests docs/frontend/debug-ledgers
git commit -m "fix: restore transcript save transition" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 2: Add canonical Session view validation and redirects

**Files:**
- Create: `apps/lingualens-app/src/features/sessions/state/session-view.ts`
- Create: `apps/lingualens-app/src/__tests__/session-view.test.ts`
- Modify: `apps/lingualens-app/src/app/sessions/[sessionId]/page.tsx`
- Modify: `apps/lingualens-app/src/app/record/page.tsx`
- Modify: `apps/lingualens-app/src/app/review-transcript/page.tsx`
- Modify: `apps/lingualens-app/src/app/transcript/page.tsx`
- Modify: `apps/lingualens-app/src/app/results/page.tsx`
- Modify: `apps/lingualens-app/src/app/report-summary/page.tsx`

- [ ] **Step 1: Write failing validator tests**

```ts
import { resolveSessionView, resolveLegacySessionHref } from "@/features/sessions/state/session-view";

test.each(["intake", "transcript", "findings", "report"])("accepts %s", (view) => {
  expect(resolveSessionView(view)).toBe(view);
});

test.each([undefined, "", "results", "unknown"])("defaults %s to intake", (view) => {
  expect(resolveSessionView(view)).toBe("intake");
});

test("sends identifier-less legacy traffic to deliberate selection", () => {
  expect(resolveLegacySessionHref("transcript", undefined)).toBe("/cases?intent=start-session");
});

test("maps an identified legacy route to canonical Session", () => {
  expect(resolveLegacySessionHref("findings", "session-1")).toBe("/sessions/session-1?view=findings");
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/session-view.test.ts`
Expected: FAIL because the helper does not exist.

- [ ] **Step 3: Implement the helpers**

```ts
export const sessionViews = ["intake", "transcript", "findings", "report"] as const;
export type SessionView = typeof sessionViews[number];

export function resolveSessionView(value?: string): SessionView {
  return sessionViews.includes(value as SessionView) ? value as SessionView : "intake";
}

export function resolveLegacySessionHref(view: SessionView, sessionId?: string): string {
  return sessionId ? `/sessions/${encodeURIComponent(sessionId)}?view=${view}` : "/cases?intent=start-session";
}
```

- [ ] **Step 4: Convert legacy pages to server redirects**

Each legacy route resolves `session_id` and calls Next.js `redirect(resolveLegacySessionHref(view, sessionId))`. Remove component mounting from those pages. `/transcript` uses the same transcript mapping rather than re-exporting a page.

- [ ] **Step 5: Validate the canonical page view**

Call `resolveSessionView(resolvedSearchParams?.view)` before passing the view to the Session container.

- [ ] **Step 6: Run route tests and build**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/session-view.test.ts src/__tests__/pages.test.tsx`
Expected: PASS after replacing old route-flow assertions with redirect assertions.

Run: `cd apps/lingualens-app && npm run build`
Expected: legacy routes remain as compatibility entries and canonical Session builds.

- [ ] **Step 7: Commit**

```bash
git add apps/lingualens-app/src/features/sessions/state apps/lingualens-app/src/app apps/lingualens-app/src/__tests__
git commit -m "refactor: consolidate session routes" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 3: Characterize and extract Session workflow state

**Files:**
- Create: `apps/lingualens-app/src/features/sessions/state/session-workflow-reducer.ts`
- Create: `apps/lingualens-app/src/__tests__/session-workflow-reducer.test.ts`
- Create: `apps/lingualens-app/src/features/sessions/services/session-workflow-service.ts`
- Modify: `apps/lingualens-app/src/components/session-workspace-client.tsx`

- [ ] **Step 1: Write characterization tests for safety transitions**

```ts
test("transcript edits clear QA, attestation, findings, and report readiness", () => {
  const next = sessionWorkflowReducer(reviewedState, {
    type: "transcript-edited",
    lines: [{ lineId: "1", speaker: "CHI", text: "changed" }],
  });
  expect(next).toMatchObject({
    transcriptSaveStatus: "unsaved",
    qaStatus: "not_run",
    transcriptAttested: false,
    analysisStatus: "stale",
    reportStatus: "Stale",
  });
});

test("signed reports cannot transition back to editable", () => {
  expect(() => sessionWorkflowReducer(signedState, { type: "report-edit-requested" })).toThrow("Signed reports are immutable");
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/session-workflow-reducer.test.ts`
Expected: FAIL because the reducer does not exist.

- [ ] **Step 3: Implement only the characterized transitions**

Create a pure reducer with actions for hydration, transcript edit/save/QA/attest, findings start/success/failure/stale, report draft/save/sign/revise, request start/success/failure, and session identity change. Reuse existing `WorkflowState` initially, then move the type after callers are migrated.

- [ ] **Step 4: Extract backend orchestration**

`session-workflow-service.ts` exports focused methods:

```ts
export type SessionIdentifiers = {
  sessionId: string;
  transcriptId?: string;
  reportId?: string;
};

export type SaveTranscriptInput = {
  sessionId: string;
  transcriptId?: string;
  source: "cha-upload" | "paste-transcript";
  originalText: string;
  normalizedText: string;
  sourceFilename?: string;
};

export type GenerateReportInput = {
  sessionId: string;
  providerId: string;
  allowTemplateFallback: boolean;
  therapistNotes?: string;
  sessionGoals?: string[];
};

export const sessionWorkflowService = {
  load: async (ids: SessionIdentifiers) => {
    const [session, transcript, report] = await Promise.all([
      getBackendSession(ids.sessionId),
      ids.transcriptId ? getBackendTranscript(ids.transcriptId) : Promise.resolve(undefined),
      ids.reportId ? getBackendReport(ids.reportId) : Promise.resolve(undefined),
    ]);
    return { session, transcript, report };
  },
  saveTranscript: async (input: SaveTranscriptInput) => input.transcriptId
    ? updateBackendTranscript(input.transcriptId, input.normalizedText, "Therapist saved transcript edits.")
    : createBackendTranscript(
        input.sessionId,
        input.source,
        input.originalText,
        input.normalizedText,
        input.sourceFilename,
      ),
  runQa: async (transcriptId: string) => runBackendQa(transcriptId),
  attest: async (transcriptId: string) => attestBackendTranscript(transcriptId),
  extractFindings: async (sessionId: string, transcriptId?: string) =>
    runBackendAnalysis(sessionId, transcriptId),
  generateReport: async (input: GenerateReportInput) => generateBackendReport(
    input.sessionId,
    input.providerId,
    input.allowTemplateFallback,
    input.therapistNotes,
    input.sessionGoals,
  ),
};
```

Keep the backend response's existing transcript/report version and provenance fields intact when mapping service results. No browser mock fallback is allowed.

- [ ] **Step 5: Migrate one transition at a time**

Move hydration first, then transcript save/QA/attest, then findings, then report. After each move run the relevant existing tests before deleting the old handler.

- [ ] **Step 6: Verify Session suites**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/session-workflow-reducer.test.ts src/__tests__/session-intake-flow.test.tsx src/__tests__/session-workspace-audio-auth.test.tsx src/__tests__/transcript-editor-panel.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/lingualens-app/src/features/sessions apps/lingualens-app/src/components/session-workspace-client.tsx apps/lingualens-app/src/__tests__
git commit -m "refactor: extract session workflow state" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 4: Split Session views and shared Report implementation

**Files:**
- Create: `apps/lingualens-app/src/features/sessions/components/session-workspace.tsx`
- Create: `apps/lingualens-app/src/features/sessions/components/session-context-header.tsx`
- Create: `apps/lingualens-app/src/features/sessions/intake/session-intake-view.tsx`
- Create: `apps/lingualens-app/src/features/sessions/transcript/session-transcript-view.tsx`
- Create: `apps/lingualens-app/src/features/sessions/findings/session-findings-view.tsx`
- Create: `apps/lingualens-app/src/features/sessions/report/session-report-view.tsx`
- Create: `apps/lingualens-app/src/__tests__/reports-workspace-client.test.tsx`
- Modify: `apps/lingualens-app/src/components/session-workspace-client.tsx`
- Modify: `apps/lingualens-app/src/components/report-summary-client.tsx`
- Modify: `apps/lingualens-app/src/components/reports-workspace-client.tsx`

- [ ] **Step 1: Add a characterization test for shared report routing**

```tsx
test("opens report editing in canonical Session view", async () => {
  render(<ReportsWorkspaceClient reports={[reportFixture]} />);
  expect(screen.getByRole("link", { name: /open report/i })).toHaveAttribute(
    "href", "/sessions/session-1?view=report",
  );
});
```

- [ ] **Step 2: Run and confirm the current test fails**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/reports-workspace-client.test.tsx`
Expected: FAIL because the current library points to `/report-summary`.

- [ ] **Step 3: Create the thin Session container**

```tsx
export function SessionWorkspace(props: SessionWorkspaceProps) {
  const model = useSessionWorkspace(props);
  return (
    <>
      <SessionContextHeader context={model.context} />
      {model.view === "intake" && <SessionIntakeView model={model.intake} />}
      {model.view === "transcript" && <SessionTranscriptView model={model.transcript} />}
      {model.view === "findings" && <SessionFindingsView model={model.findings} />}
      {model.view === "report" && <SessionReportView model={model.report} />}
    </>
  );
}
```

- [ ] **Step 4: Move existing JSX without changing visual behavior**

Move one view at a time, pass typed view models/callbacks, and run its existing tests. `session-report-view.tsx` becomes the only report editor. Convert `report-summary-client.tsx` into a temporary re-export wrapper, then delete it after all callers move.

- [ ] **Step 5: Route Reports library rows to Session Report**

Build hrefs only when `session_id` exists. If missing, use `/cases?intent=start-session` and label the action “Find session”.

- [ ] **Step 6: Run affected tests and typecheck**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/pages.test.tsx src/__tests__/transcript-editor-panel.test.tsx src/__tests__/session-intake-flow.test.tsx src/__tests__/reports-workspace-client.test.tsx`
Expected: PASS.

Run: `cd apps/lingualens-app && npm run typecheck`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/lingualens-app/src/features/sessions apps/lingualens-app/src/components apps/lingualens-app/src/__tests__
git commit -m "refactor: split canonical session workspace" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 5: Split Cases and Settings feature boundaries

**Files:**
- Create: `apps/lingualens-app/src/features/cases/components/case-list.tsx`
- Create: `apps/lingualens-app/src/features/cases/components/case-detail.tsx`
- Create: `apps/lingualens-app/src/features/cases/hooks/use-cases-workspace.ts`
- Create: `apps/lingualens-app/src/features/settings/services/settings-access.ts`
- Create: `apps/lingualens-app/src/features/settings/components/settings-workspace.tsx`
- Modify: `apps/lingualens-app/src/components/cases-workspace-client.tsx`
- Modify: `apps/lingualens-app/src/components/settings-workspace-client.tsx`

- [ ] **Step 1: Write role-matrix tests**

```ts
import { allowedSettingsSections } from "@/features/settings/services/settings-access";

test("therapists receive no admin section", () => {
  expect(allowedSettingsSections("therapist")).toEqual([
    "profile", "organization", "credentials", "accessibility", "privacy",
  ]);
});

test("organization admins receive therapist and admin sections", () => {
  expect(allowedSettingsSections("org_admin")).toContain("team");
  expect(allowedSettingsSections("org_admin")).toContain("audit");
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/settings-access.test.ts`
Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement role-safe sections**

Use readonly section arrays and a `resolveAuthorizedSection(role, requested)` helper that returns `{ authorized: false, section: "profile" }` for unauthorized or unknown deep links.

- [ ] **Step 4: Extract Cases and Settings containers**

Move remote loading/mutations into hooks. `CaseList` and `CaseDetail` receive view models. `SettingsWorkspace` receives the authorized role and section; it does not render or request admin feature data for therapists.

- [ ] **Step 5: Run focused tests**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/settings-access.test.ts src/__tests__/settings-workspace-client.test.tsx src/__tests__/cases-workspace-client.test.tsx`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/lingualens-app/src/features/cases apps/lingualens-app/src/features/settings apps/lingualens-app/src/components apps/lingualens-app/src/__tests__
git commit -m "refactor: split cases and settings features" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 6: Enforce admin authorization and audit boundaries

**Files:**
- Modify: `apps/api/app/core/security.py`
- Modify: `apps/api/app/api/v1/routes/organization_admin.py`
- Modify: `apps/api/tests/test_organization_admin_routes.py`
- Modify: `apps/lingualens-app/src/app/settings/page.tsx`
- Create: `apps/lingualens-app/src/__tests__/settings-route-authorization.test.tsx`

- [ ] **Step 1: Add failing backend therapist denial tests**

```py
def test_therapist_cannot_list_organization_invitations(client, therapist_headers):
    response = client.get("/api/v1/organization-admin/invitations", headers=therapist_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized for organization administration."

def test_denied_admin_action_is_audited(client, therapist_headers, repository):
    client.get("/api/v1/organization-admin/invitations", headers=therapist_headers)
    event = repository.list_audit_events(action="organization.invitation.list_denied")[-1]
    assert event.outcome == "denied"
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest apps/api/tests/test_organization_admin_routes.py -q`
Expected: at least one new assertion fails until denial auditing/shape is implemented.

- [ ] **Step 3: Implement one reusable org-admin guard**

The guard verifies authenticated active membership in the requested organization and role `org_admin`. It returns a generic 403 and emits an audit event containing actor, action, target type/id, outcome, timestamp, and correlation ID without clinical content.

- [ ] **Step 4: Add the frontend direct-link test**

```tsx
test("therapist deep link redirects before admin data is requested", async () => {
  render(await SettingsPage({ searchParams: { section: "team" } }));
  expect(redirectMock).toHaveBeenCalledWith("/settings?section=profile&notice=not-authorized");
  expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("organization-admin"), expect.anything());
});
```

- [ ] **Step 5: Implement server data-boundary resolution**

Resolve the authenticated organization role before composing Settings. Pass only the authorized section and role to the client feature. Never trust a `role` query parameter.

- [ ] **Step 6: Run backend/frontend authorization suites**

Run: `pytest apps/api/tests/test_organization_admin_routes.py apps/api/tests/test_privacy_operations.py -q`
Expected: PASS.

Run: `cd apps/lingualens-app && npm test -- src/__tests__/settings-route-authorization.test.tsx src/__tests__/settings-workspace-client.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app apps/api/tests apps/lingualens-app/src/app/settings apps/lingualens-app/src/features/settings apps/lingualens-app/src/__tests__
git commit -m "feat: enforce settings administration roles" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 7: Consolidate shell navigation and gate demos

**Files:**
- Modify: `apps/lingualens-app/src/app/page.tsx`
- Modify: `apps/lingualens-app/src/components/sidebar.tsx`
- Modify: `apps/lingualens-app/src/components/bottom-nav.tsx`
- Modify: `apps/lingualens-app/src/app/demo/layout.tsx`
- Create: `apps/lingualens-app/src/services/adapters/demo-mode.ts`
- Create: `apps/lingualens-app/src/__tests__/navigation-routes.test.tsx`

- [ ] **Step 1: Write failing navigation and demo tests**

```tsx
test("navigation contains Today, Cases, Session, Reports, Settings without Home", () => {
  render(<Sidebar active="Today" activeSessionId={undefined} />);
  expect(screen.queryByRole("link", { name: "Home" })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute("href", "/cases?intent=start-session");
});

test("disabled demo mode returns not found", () => {
  expect(() => assertDemoEnabled({ NEXT_PUBLIC_DEMO_MODE: "false" })).toThrow("DEMO_NOT_FOUND");
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/navigation-routes.test.tsx`
Expected: FAIL because Home remains and demo has no flag guard.

- [ ] **Step 3: Implement canonical nav and root redirect**

Use one shared nav item source for desktop and mobile. Root page calls `redirect("/today")` after the existing auth gate. Session href uses the active authorized session or `/cases?intent=start-session`.

- [ ] **Step 4: Implement demo guard**

```ts
export function isDemoEnabled(env = process.env): boolean {
  return env.NEXT_PUBLIC_DEMO_MODE === "true";
}
```

The server demo layout calls `notFound()` when disabled and renders a persistent Sample Data banner when enabled.

- [ ] **Step 5: Run tests and build**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/navigation-routes.test.tsx src/__tests__/pages.test.tsx src/__tests__/design-system.test.tsx`
Expected: PASS.

Run: `cd apps/lingualens-app && npm run build`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/lingualens-app/src/app apps/lingualens-app/src/components apps/lingualens-app/src/services apps/lingualens-app/src/__tests__
git commit -m "feat: consolidate workbench navigation" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 8: Run the decomposition/routes/auth phase gate

**Files:**
- Modify: `docs/frontend/LINGUALENS_UX_UI_MODERNIZATION_REPORT.md`
- Modify: `docs/SECURITY.md` if role/deep-link behavior changes documented policy

- [ ] **Step 1: Run all frontend tests**

Run: `cd apps/lingualens-app && npm test`
Expected: PASS with zero failed tests.

- [ ] **Step 2: Run backend affected tests**

Run: `pytest apps/api/tests/test_workflow.py apps/api/tests/test_organization_admin_routes.py apps/api/tests/test_privacy_operations.py -q`
Expected: PASS.

- [ ] **Step 3: Run typecheck, lint, build, and smoke**

Run each: `npm run typecheck`, `npm run lint`, `npm run build`, `npm run e2e:smoke` inside `apps/lingualens-app`.
Expected: exit 0 for each; record lint warnings separately.

- [ ] **Step 4: Capture affected route screenshots**

Capture `/today`, `/cases?intent=start-session`, each Session view, `/reports`, therapist `/settings`, admin `/settings?section=team`, and disabled demo behavior at affected required viewports.

- [ ] **Step 5: Verify safety and authorization explicitly**

Confirm transcript edits invalidate findings/report, signed reports remain read-only, therapist deep links do not fetch admin data, and denied backend requests create safe audit events.

- [ ] **Step 6: Record evidence and commit**

```bash
git add docs/frontend docs/SECURITY.md
git commit -m "docs: record routing and authorization evidence" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```
