# Persistence Verification Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden persistence verification, offline local mode behavior, report finalization safeguards, and add comprehensive tests for these scenarios.

**Architecture:** Use repository unit tests on the backend, modify the frontend client views (`SessionWorkspaceClient` and `ReportSummaryClient`) to prevent stale `sessionStorage` leaks and disable/rename clinical-final buttons in offline mode, and write exhaustive Vitest frontend tests.

**Tech Stack:** FastAPI, Pytest, React, Next.js, TypeScript, Vitest, Testing Library.

---

### Task 1: Backend Repository Unit Test

**Files:**
- Modify: [test_workflow.py](file:///Users/porschecaa/Desktop/asd-project/apps/api/tests/test_workflow.py)

- [ ] **Step 1: Write direct repository persistence test**
  Add `test_json_repository_direct_restart_persistence` to `apps/api/tests/test_workflow.py` to assert that creating a case, session, transcript, and report in `JsonFileRepository` and then reinitializing a new instance loading from the same path successfully restores all fields.
  
  ```python
  def test_json_repository_direct_restart_persistence(tmp_path):
      from app.repositories.mock_repository import JsonFileRepository
      from app.schemas.clinical import ChildCase, TherapySession, Transcript, Report, ReviewStatus
      path = tmp_path / "persistence-direct.json"
      
      repo = JsonFileRepository(path)
      # Create entities
      case = ChildCase(case_id="case_t1", child_code="C-T1", age_months=48, language="English", consent_status="granted")
      repo.cases[case.case_id] = case
      
      session = TherapySession(session_id="session_t1", case_id=case.case_id, session_date="2026-06-19", session_type="therapy_session")
      repo.sessions[session.session_id] = session
      
      transcript = Transcript(transcript_id="trans_t1", session_id=session.session_id, case_id=case.case_id, raw_text="@Begin\n*CHI:\thello .\n@End", therapist_attested=True, qa_status="PASS")
      repo.transcripts[transcript.transcript_id] = transcript
      
      report = Report(report_id="rep_t1", session_id=session.session_id, case_id=case.case_id, report_type="Session Review Report", title="Report Title", markdown="# Report", status=ReviewStatus.signed_off)
      repo.reports[report.report_id] = report
      
      repo.add_audit("test.setup", "case_t1", "Created test entities.")
      
      # Reinitialize
      reopened = JsonFileRepository(path)
      assert "case_t1" in reopened.cases
      assert reopened.cases["case_t1"].child_code == "C-T1"
      assert "session_t1" in reopened.sessions
      assert reopened.sessions["session_t1"].case_id == "case_t1"
      assert "trans_t1" in reopened.transcripts
      assert reopened.transcripts["trans_t1"].raw_text == "@Begin\n*CHI:\thello .\n@End"
      assert reopened.transcripts["trans_t1"].therapist_attested is True
      assert "rep_t1" in reopened.reports
      assert reopened.reports["rep_t1"].title == "Report Title"
      assert reopened.reports["rep_t1"].status == ReviewStatus.signed_off
  ```

- [ ] **Step 2: Run the pytest tests to verify they pass**
  Run: `PYTHONPATH=apps/api .venv/bin/pytest -v -k "test_json_repository_direct_restart_persistence"`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add apps/api/tests/test_workflow.py
  git commit -m "test: add direct JSON repository persistence unit test"
  ```

---

### Task 2: Frontend Backend-Source-of-Truth

**Files:**
- Modify: [session-workspace-client.tsx](file:///Users/porschecaa/Desktop/asd-project/apps/therapist-app-v2/src/components/session-workspace-client.tsx)
- Modify: [report-summary-client.tsx](file:///Users/porschecaa/Desktop/asd-project/apps/therapist-app-v2/src/components/report-summary-client.tsx)

- [ ] **Step 1: Clear stale transcript state in SessionWorkspaceClient loader**
  In `apps/therapist-app-v2/src/components/session-workspace-client.tsx`, in `useEffect` when `hasLocator` is true, clear the transcript values in the initial `setState` to prevent stale sessionStorage leaks.
  
  Replace:
  ```typescript
      setState({ ...stored, workflowLoading: true, statusMessage: "Loading persisted workflow...", error: undefined });
  ```
  With:
  ```typescript
      setState({
        ...stored,
        transcriptText: "",
        transcriptLines: [],
        transcriptReady: false,
        transcriptAttested: false,
        transcriptReviewStatus: "not_started",
        qaStatus: "not_run",
        qaIssues: [],
        workflowLoading: true,
        statusMessage: "Loading persisted workflow...",
        error: undefined
      });
  ```

- [ ] **Step 2: Clear stale report state in ReportSummaryClient loader**
  In `apps/therapist-app-v2/src/components/report-summary-client.tsx`, in `useEffect` when a locator is present, clear the report fields in the initial `setState` to prevent stale sessionStorage leaks.
  
  Replace:
  ```typescript
      setState({ ...stored, workflowLoading: true, statusMessage: "Loading persisted report...", error: undefined });
  ```
  With:
  ```typescript
      setState({
        ...stored,
        reportMarkdown: "",
        reportStatus: "Not started",
        reportSaveStatus: "idle",
        workflowLoading: true,
        statusMessage: "Loading persisted report...",
        error: undefined
      });
  ```

- [ ] **Step 3: Commit**
  ```bash
  git add apps/therapist-app-v2/src/components/session-workspace-client.tsx apps/therapist-app-v2/src/components/report-summary-client.tsx
  git commit -m "feat: prevent stale sessionStorage leak during locator loading phase"
  ```

---

### Task 3: Offline Local Mode Enhancements

**Files:**
- Modify: [session-workspace-client.tsx](file:///Users/porschecaa/Desktop/asd-project/apps/therapist-app-v2/src/components/session-workspace-client.tsx)
- Modify: [report-summary-client.tsx](file:///Users/porschecaa/Desktop/asd-project/apps/therapist-app-v2/src/components/report-summary-client.tsx)
- Modify: [transcript-editor-panel.tsx](file:///Users/porschecaa/Desktop/asd-project/apps/therapist-app-v2/src/components/transcript-editor-panel.tsx)

- [ ] **Step 1: Suppress success/saved messages in WorkflowStatus if offline**
  In `session-workspace-client.tsx` and `report-summary-client.tsx`, update `WorkflowStatus` to accept `backendUnavailable: boolean` and suppress success messages if `backendUnavailable` is true.
  
  Modify `WorkflowStatus` in `session-workspace-client.tsx` (around line 1348) and `report-summary-client.tsx` (around line 400):
  ```typescript
  function WorkflowStatus({ state, backendUnavailable }: { state: WorkflowState; backendUnavailable?: boolean }) {
    if (!state.statusMessage && !state.error) {
      return null;
    }
    const isError = Boolean(state.error);
    const isSuccess = Boolean(state.statusMessage && !isError);
    if (isSuccess && backendUnavailable) {
      return null;
    }
    ...
  ```
  Update usages of `<WorkflowStatus state={state} />` in both files to `<WorkflowStatus state={state} backendUnavailable={backendUnavailable} />`.

- [ ] **Step 2: Disable and rename Attest button in TranscriptEditorPanel if offline**
  In `apps/therapist-app-v2/src/components/transcript-editor-panel.tsx`, add `backendUnavailable?: boolean` to props.
  Update the "Attest transcript" button:
  * `disabled={busy || !canAttest || attested || backendUnavailable}`
  * Button text: `{attested ? "Transcript attested" : backendUnavailable ? "Attest transcript (Online only)" : "Attest transcript"}`
  
  In `session-workspace-client.tsx`'s render of `<TranscriptReviewView>`, pass `backendUnavailable={backendUnavailable}` to `<TranscriptEditorPanel>`.

- [ ] **Step 3: Disable and rename Finalize button in ReportSummaryClient if offline**
  In `apps/therapist-app-v2/src/components/report-summary-client.tsx`, update the "Finalize Report" button:
  * `disabled={busy || state.reportStatus === "Not started" || state.reportStatus === "Finalized" || state.reportSaveStatus !== "saved" || backendUnavailable}`
  * Button text: `{state.reportStatus === "Finalized" ? "Report Finalized" : backendUnavailable ? "Finalize Report (Online only)" : "Finalize Report"}`

- [ ] **Step 4: Commit**
  ```bash
  git add apps/therapist-app-v2/src/components/session-workspace-client.tsx apps/therapist-app-v2/src/components/report-summary-client.tsx apps/therapist-app-v2/src/components/transcript-editor-panel.tsx
  git commit -m "feat: disable and rename clinical-final actions, suppress success messages in offline mode"
  ```

---

### Task 4: Report Finalization Validation

**Files:**
- Modify: [report-summary-client.tsx](file:///Users/porschecaa/Desktop/asd-project/apps/therapist-app-v2/src/components/report-summary-client.tsx)

- [ ] **Step 1: Ensure finalized report edit blocking in report-summary-client**
  Verify that inputs (`therapistNotes`, `goalsText`, `reportText` textarea) are read-only when report is finalized.
  Double-check `onChange` handlers for inputs to strictly return if `state.reportStatus === "Finalized"`.
  
  For `therapistNotes` textarea (around line 315):
  ```typescript
  onChange={(event) => {
    if (state.reportStatus === "Finalized") return;
    setTherapistNotes(event.target.value);
    persist({ ...state, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
  }}
  ```
  
  For `goalsText` textarea (around line 320):
  ```typescript
  onChange={(event) => {
    if (state.reportStatus === "Finalized") return;
    setGoalsText(event.target.value);
    persist({ ...state, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
  }}
  ```
  
  For `reportText` preview textarea (around line 369):
  ```typescript
  onChange={(event) => {
    if (state.reportStatus === "Finalized") return;
    setReportText(event.target.value);
    persist({ ...state, reportMarkdown: event.target.value, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
  }}
  ```

- [ ] **Step 2: Commit**
  ```bash
  git add apps/therapist-app-v2/src/components/report-summary-client.tsx
  git commit -m "feat: strictly block edit state changes on finalized reports"
  ```

---

### Task 5: Frontend Vitest Testing Hardening

**Files:**
- Modify: [pages.test.tsx](file:///Users/porschecaa/Desktop/asd-project/apps/therapist-app-v2/src/__tests__/pages.test.tsx)

- [ ] **Step 1: Add frontend tests for source of truth, offline local mode, and report finalization**
  Add these test cases at the end of `apps/therapist-app-v2/src/__tests__/pages.test.tsx`:
  
  ```typescript
  it("strictly overrides stale sessionStorage transcript if transcript_id is in URL", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendSessionId: "STALE-SESSION",
      backendTranscriptId: "STALE-TRANSCRIPT",
      transcriptText: "@Begin\n*CHI:\tStale sessionStorage text.\n@End",
      transcriptLines: [{ lineId: "stale", speaker: "CHI", text: "Stale sessionStorage text." }]
    });
    
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-OK")) {
        return jsonResponse({ session_id: "SESSION-OK", case_id: "CASE-OK", transcript_id: "TRANSCRIPT-OK" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-OK")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-OK",
          session_id: "SESSION-OK",
          case_id: "CASE-OK",
          raw_text: "@Begin\n@Languages:\teng\n*CHI:\tWinner backend text.\n@End",
          utterances: [{ utterance_id: "utt-1", speaker: "CHI", text: "Winner backend text." }],
          qa_status: "PASS",
          therapist_attested: true
        });
      }
      if (url.endsWith("/cases/CASE-OK")) {
        return jsonResponse({ case_id: "CASE-OK", child_code: "C-OK" });
      }
      return jsonResponse({});
    }));

    render(<ReviewTranscriptPage searchParams={{
      case_id: "CASE-OK",
      session_id: "SESSION-OK",
      transcript_id: "TRANSCRIPT-OK"
    }} />);

    // Backend text must win
    expect(await screen.findByRole("textbox", { name: "Utterance text 1" })).toHaveValue("Winner backend text.");
    expect(loadWorkflowState().transcriptText).toContain("Winner backend text.");
  });

  it("enters offline mode, disables clinical-final buttons with Online only label, and hides success messages", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));
    
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendSessionId: "SESSION-OFFLINE",
      backendTranscriptId: "TRANSCRIPT-OFFLINE",
      transcriptText: "@Begin\n*CHI:\thello .\n@End",
      transcriptLines: [{ lineId: "line-1", speaker: "CHI", text: "hello" }],
      transcriptReady: true,
      qaStatus: "pass",
      statusMessage: "Transcript draft saved." // Stale success message
    });

    render(<ReviewTranscriptPage searchParams={{
      case_id: "CASE-OFFLINE",
      session_id: "SESSION-OFFLINE",
      transcript_id: "TRANSCRIPT-OFFLINE"
    }} />);

    // Shows banner
    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    
    // Suppresses the success status message
    expect(screen.queryByText("Transcript draft saved.")).not.toBeInTheDocument();
    
    // Button is disabled and renamed
    const attestBtn = screen.getByRole("button", { name: "Attest transcript (Online only)" });
    expect(attestBtn).toBeDisabled();
  });

  it("strictly disables report finalization inputs and save actions when finalized", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-FIN")) {
        return jsonResponse({ session_id: "SESSION-FIN", case_id: "CASE-FIN", transcript_id: "TRANSCRIPT-FIN", report_id: "REPORT-FIN" });
      }
      if (url.endsWith("/reports/REPORT-FIN")) {
        return jsonResponse({
          report_id: "REPORT-FIN",
          session_id: "SESSION-FIN",
          case_id: "CASE-FIN",
          markdown: "# Finalized report markdown",
          status: "Signed Off"
        });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-FIN")) {
        return jsonResponse({ transcript_id: "TRANSCRIPT-FIN", session_id: "SESSION-FIN", therapist_attested: true });
      }
      if (url.endsWith("/cases/CASE-FIN")) {
        return jsonResponse({ case_id: "CASE-FIN", child_code: "C-FIN" });
      }
      return jsonResponse({});
    }));

    render(<ReportSummaryPage searchParams={{
      case_id: "CASE-FIN",
      session_id: "SESSION-FIN",
      transcript_id: "TRANSCRIPT-FIN",
      report_id: "REPORT-FIN"
    }} />);

    const reportArea = await screen.findByRole("textbox", { name: "Finalized report" });
    expect(reportArea).toBeReadOnly();
    
    const finalizeBtn = screen.getByRole("button", { name: "Report Finalized" });
    expect(finalizeBtn).toBeDisabled();
    
    const saveBtn = screen.getByRole("button", { name: "Save draft" });
    expect(saveBtn).toBeDisabled();
    
    const generateBtn = screen.getByRole("button", { name: "Generate draft" });
    expect(generateBtn).toBeDisabled();
  });
  
  function jsonResponse(data: any) {
    return {
      ok: true,
      status: 200,
      json: async () => data
    } as unknown as Response;
  }
  ```

- [ ] **Step 2: Run all vitest tests to verify success**
  Run: `cd apps/therapist-app-v2 && npm test`
  Expected: All 61 tests pass

- [ ] **Step 3: Commit**
  ```bash
  git add apps/therapist-app-v2/src/__tests__/pages.test.tsx
  git commit -m "test: add vitest tests for truth source, offline mode, and finalization read-only behavior"
  ```

---

### Task 6: Manual QA Checklist Documentation

**Files:**
- Modify: [DEMO_SCRIPT.md](file:///Users/porschecaa/Desktop/asd-project/docs/DEMO_SCRIPT.md)
- Modify: [walkthrough.md](file:///Users/porschecaa/.gemini/antigravity-ide/brain/2ed46f20-4fbc-4539-b086-73a2305978c2/walkthrough.md) (in artifacts directory)

- [ ] **Step 1: Update DEMO_SCRIPT.md with manual QA instructions**
  Open `docs/DEMO_SCRIPT.md` and add a new section `# Manual QA Verification Checklist` at the end containing the requested checklists for backend-on, backend-off, API restart, export .cha, and finalized report reload.
  
  ```markdown
  ## Manual QA Verification Checklist
  
  ### Checklist 1: Test Backend On (Normal Mode)
  - [ ] Start backend API and therapist app frontend.
  - [ ] Navigate to `/login`, choose Therapist, click `Enter workspace`.
  - [ ] Run the workspace demo workflow.
  - [ ] Verify that saving drafts, running QA, attesting transcripts, feature extraction, and report generation complete successfully with success status alerts.
  
  ### Checklist 2: Test Backend Off (Offline Mode)
  - [ ] Terminate the backend API process.
  - [ ] Refresh the workspace or review pages.
  - [ ] Verify banner "Backend unavailable — local workspace mode" is visible.
  - [ ] Verify success status messages (like "Saved" or "Attestation complete") are hidden.
  - [ ] Verify that the clinical-final buttons are disabled and labeled `(Online only)`.
  
  ### Checklist 3: Test API Restart Persistence
  - [ ] Start the backend API with `JsonFileRepository` mode.
  - [ ] Perform a full workflow: create a case/session, review a transcript, extract features, and draft a report.
  - [ ] Shut down the backend API.
  - [ ] Start the backend API again.
  - [ ] Refresh the page on the frontend and verify all edited transcript texts, attestation states, and draft report inputs reload intact.
  
  ### Checklist 4: Test Export .cha
  - [ ] Save and attest a transcript.
  - [ ] Click "Export reviewed .cha" in the transcript review workspace.
  - [ ] Verify that a `.cha` file downloads containing correct CHAT headers (`@Begin`, `@Languages`, `@Participants`, etc.) and matching speaker utterances.
  
  ### Checklist 5: Test Finalized Report Reload
  - [ ] Generate a report, edit notes/goals, and click "Finalize Report".
  - [ ] Verify the report text areas and inputs display as read-only.
  - [ ] Verify the "Save draft", "Generate draft", and "Finalize" buttons are disabled.
  - [ ] Refresh the page and confirm the report loads as "Finalized" and is strictly read-only.
  ```

- [ ] **Step 2: Commit**
  ```bash
  git add docs/DEMO_SCRIPT.md
  git commit -m "docs: add Manual QA Verification Checklist to DEMO_SCRIPT.md"
  ```
