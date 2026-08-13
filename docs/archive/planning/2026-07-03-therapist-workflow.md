# Integrated Therapist Workflow Implementation Plan

Status: Historical
Not a source of truth
Superseded by: `docs/PROJECT_SOURCE_OF_TRUTH.md`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cohesive, role-aware therapist-facing web app workflow that enforces consent gates, displays a visual session pipeline progress bar, and handles ML-pending results with an escape hatch.

**Architecture:** We will modify the client components `CasesWorkspaceClient` and `SessionWorkspaceClient` to enforce consent restrictions and display real-time status. We will add a reusable `PipelineProgressBar` component and update the mock/API backend connectors in `workflow.ts` to support these interactions.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS, Lucide icons, Astryx design system tokens.

---

### Task 1: API helper functions in `workflow.ts` for Case Consent Management

**Files:**
- Modify: `/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/workflow.ts`

- [ ] **Step 1: Write the case consent helpers**

Add these function definitions to `/Users/porschecaa/lingualens/apps/lingualens-app/src/lib/workflow.ts`:

```typescript
export async function createBackendCase(payload: Partial<BackendCase>): Promise<BackendCase> {
  return apiRequest<BackendCase>("/cases", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateBackendCase(caseId: string, payload: Partial<BackendCase>): Promise<BackendCase> {
  return apiRequest<BackendCase>(`/cases/${caseId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function withdrawBackendCaseConsent(
  caseId: string,
  reason: string,
  redactNotes: boolean
): Promise<{ status: string; message: string }> {
  return apiRequest<any>(`/cases/${caseId}/withdraw-consent`, {
    method: "POST",
    body: JSON.stringify({ reason, redact_notes: redactNotes })
  });
}
```

- [ ] **Step 2: Export helper functions**
Ensure the new functions are exported from `workflow.ts` so they can be consumed by client components.

- [ ] **Step 3: Verify build**
Run: `npm run typecheck` inside `apps/lingualens-app/` to ensure no syntax errors.

---

### Task 2: Map and style pipeline statuses in `status-badge.tsx`

**Files:**
- Modify: `/Users/porschecaa/lingualens/apps/lingualens-app/src/components/status-badge.tsx`

- [ ] **Step 1: Add new status mappings**

Modify `src/components/status-badge.tsx` to handle the new pipeline statuses:

```typescript
export type WorkflowStatus =
  | "Draft"
  | "Needs Review"
  | "Attested"
  | "Processing"
  | "Failed"
  | "Ready"
  | "Signed Off"
  | "Withdrawn"
  | "Awaiting Consent"
  | "Ready for Audio"
  | "Recording"
  | "Uploading"
  | "Transcribing"
  | "CHA Generating"
  | "ML Pending"
  | "Review Required"
  | "Report Ready";

const styles: Record<WorkflowStatus, string> = {
  Draft: "border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-muted)]",
  "Needs Review": "border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]",
  Attested: "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
  Processing: "border-[color:var(--color-info-border)] bg-[color:var(--color-info-bg)] text-[color:var(--color-info-text)]",
  Failed: "border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)]",
  Ready: "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
  "Signed Off": "border-[color:var(--color-accent-strong)] bg-[color:var(--color-accent-strong)] text-white",
  Withdrawn: "border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]",
  "Awaiting Consent": "border-orange-200 bg-orange-50 text-orange-800",
  "Ready for Audio": "border-blue-200 bg-blue-50 text-blue-800",
  Recording: "border-red-200 bg-red-50 text-red-800 animate-pulse",
  Uploading: "border-blue-200 bg-blue-50 text-blue-800 animate-pulse",
  Transcribing: "border-indigo-200 bg-indigo-50 text-indigo-800",
  "CHA Generating": "border-purple-200 bg-purple-50 text-purple-800",
  "ML Pending": "border-amber-200 bg-amber-50 text-amber-800",
  "Review Required": "border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]",
  "Report Ready": "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]"
};

export function StatusBadge({ status }: { status: string }) {
  // Normalize key mapping for pipeline status strings to WorkflowStatus keys
  let lookupStatus: WorkflowStatus = "Draft";
  const normalized = status.toLowerCase().replace(/_/g, " ");

  if (normalized === "awaiting consent" || status === "awaiting_consent") lookupStatus = "Awaiting Consent";
  else if (normalized === "ready for audio" || status === "ready_for_audio") lookupStatus = "Ready for Audio";
  else if (normalized === "recording" || status === "recording") lookupStatus = "Recording";
  else if (normalized === "uploading" || status === "uploading") lookupStatus = "Uploading";
  else if (normalized === "transcribing" || status === "transcribing") lookupStatus = "Transcribing";
  else if (normalized === "cha generating" || status === "cha_generating") lookupStatus = "CHA Generating";
  else if (normalized === "ml pending" || status === "ml_pending") lookupStatus = "ML Pending";
  else if (normalized === "review required" || status === "review_required" || status === "Needs Review") lookupStatus = "Review Required";
  else if (normalized === "report ready" || status === "report_ready" || status === "Ready") lookupStatus = "Report Ready";
  else if (normalized === "signed off" || status === "Signed Off") lookupStatus = "Signed Off";
  else if (normalized === "withdrawn" || status === "Withdrawn") lookupStatus = "Withdrawn";
  else if (normalized === "failed" || status === "Failed") lookupStatus = "Failed";
  else if ((Object.keys(styles) as string[]).includes(status)) lookupStatus = status as WorkflowStatus;

  return (
    <span
      className={`inline-flex min-h-8 min-w-24 items-center justify-center rounded-full border px-3 py-1 text-xs font-semibold ${styles[lookupStatus]}`}
    >
      {lookupStatus}
    </span>
  );
}
```

- [ ] **Step 2: Verify typecheck**
Run: `npm run typecheck` to verify the code compiles without error.

---

### Task 3: Create visual pipeline progress bar component

**Files:**
- Create: `/Users/porschecaa/lingualens/apps/lingualens-app/src/components/pipeline-progress-bar.tsx`

- [ ] **Step 1: Write `PipelineProgressBar`**

Define the component in `src/components/pipeline-progress-bar.tsx` using Astryx components:

```typescript
"use client";

import { Check } from "lucide-react";
import { Stack } from "@astryxdesign/core/Stack";

export type PipelineState =
  | "awaiting_consent"
  | "ready_for_audio"
  | "uploading"
  | "transcribing"
  | "cha_generating"
  | "review_required"
  | "ml_pending"
  | "report_ready";

const pipelineStages: Array<{ id: PipelineState; label: string }> = [
  { id: "awaiting_consent", label: "Consent" },
  { id: "ready_for_audio", label: "Ready" },
  { id: "uploading", label: "Upload" },
  { id: "transcribing", label: "ASR" },
  { id: "cha_generating", label: "CHA" },
  { id: "review_required", label: "Review" },
  { id: "ml_pending", label: "ML Suggestions" },
  { id: "report_ready", label: "Report" }
];

type PipelineProgressBarProps = {
  currentStatus: string;
};

export function PipelineProgressBar({ currentStatus }: PipelineProgressBarProps) {
  // Map various session statuses to pipeline stages
  let activeIndex = 0;
  const statusLower = currentStatus.toLowerCase().replace(/_/g, " ");

  if (statusLower.includes("awaiting consent") || currentStatus === "awaiting_consent") activeIndex = 0;
  else if (statusLower.includes("ready for audio") || currentStatus === "ready_for_audio") activeIndex = 1;
  else if (statusLower.includes("recording") || statusLower.includes("uploading") || currentStatus === "uploading") activeIndex = 2;
  else if (statusLower.includes("transcribing") || currentStatus === "transcribing") activeIndex = 3;
  else if (statusLower.includes("cha generating") || currentStatus === "cha_generating") activeIndex = 4;
  else if (statusLower.includes("needs review") || statusLower.includes("review required") || currentStatus === "review_required" || currentStatus === "in_review") activeIndex = 5;
  else if (statusLower.includes("ml pending") || currentStatus === "ml_pending" || currentStatus === "attested") activeIndex = 6;
  else if (statusLower.includes("report ready") || currentStatus === "report_ready" || statusLower.includes("ready") || statusLower.includes("signed off")) activeIndex = 7;

  return (
    <Stack gap={4} className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-[0.1em] text-[color:var(--color-text-subtle)]">Pipeline Status</h3>
        <span className="text-xs font-medium text-[color:var(--color-accent-strong)]">
          Stage {activeIndex + 1} of {pipelineStages.length}: {pipelineStages[activeIndex].label}
        </span>
      </div>
      <div className="relative flex items-center justify-between" role="img" aria-label={`Pipeline Progress: ${pipelineStages[activeIndex].label}`}>
        {/* Progress bar line background */}
        <div className="absolute left-0 top-1/2 h-0.5 w-full -translate-y-1/2 bg-[color:var(--color-border)]" />
        {/* Active progress bar line */}
        <div
          className="absolute left-0 top-1/2 h-0.5 -translate-y-1/2 bg-[color:var(--color-accent-strong)] transition-all duration-500"
          style={{ width: `${(activeIndex / (pipelineStages.length - 1)) * 100}%` }}
        />

        {pipelineStages.map((stage, idx) => {
          const isCompleted = idx < activeIndex;
          const isActive = idx === activeIndex;

          return (
            <div key={stage.id} className="relative flex flex-col items-center z-10">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold transition-all duration-300 ${
                  isCompleted
                    ? "border-[color:var(--color-accent-strong)] bg-[color:var(--color-accent-strong)] text-white"
                    : isActive
                    ? "border-[color:var(--color-accent-strong)] bg-white text-[color:var(--color-accent-strong)] ring-4 ring-[color:var(--color-accent-soft)]"
                    : "border-[color:var(--color-border)] bg-white text-[color:var(--color-text-muted)]"
                }`}
              >
                {isCompleted ? <Check size={14} /> : idx + 1}
              </div>
              <span
                className={`mt-2 text-2xs font-semibold tracking-wide uppercase ${
                  isActive
                    ? "text-[color:var(--color-text-strong)]"
                    : "text-[color:var(--color-text-muted)]"
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </Stack>
  );
}
```

- [ ] **Step 2: Verify typecheck**
Run: `npm run typecheck` to verify no import/syntax errors.

---

### Task 4: Consent & Intake Gate in Case Details View

**Files:**
- Modify: `/Users/porschecaa/lingualens/apps/lingualens-app/src/components/cases-workspace-client.tsx`

- [ ] **Step 1: Update Imports and add helper structures**

Import Case update helpers at the top of the file:
```typescript
import {
  updateBackendCase,
  withdrawBackendCaseConsent
} from "@/lib/workflow";
import { PipelineProgressBar } from "@/components/pipeline-progress-bar";
```

- [ ] **Step 2: Add inline Consent Verification Panel inside `CaseDetailContent`**

Modify `CaseDetailContent` to display the consent management panel. Replace the current return block where it renders safety notices and other cards, and block the session creation action.

Specifically:
- Check `caseItem.consent_status` (normalize comparison using `.toLowerCase()`).
- Add states inside `CaseDetailContent` to handle loading, inline form inputs (`consentSigner`, `consentChecked`, `consentNotes`), and messages.
- If consent is not `granted`:
  - Show a banner and disable the "Create new session" button.
  - Render an inline Consent Gate panel.
- If consent is `granted`:
  - Show a "Withdraw Consent" button.

Implementation details:
```typescript
  const [localConsent, setLocalConsent] = useState(caseItem.consent_status ?? "pending");
  const [consentSigner, setConsentSigner] = useState("Parent");
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentNotes, setConsentNotes] = useState("");
  const [consentBusy, setConsentBusy] = useState(false);
  const [consentMsg, setConsentMsg] = useState("");

  const isConsentGranted = localConsent.toLowerCase() === "granted";

  async function handleGrantConsent(e: React.FormEvent) {
    e.preventDefault();
    if (!consentChecked) return;
    setConsentBusy(true);
    setConsentMsg("");
    try {
      await updateBackendCase(caseItem.case_id, {
        consent_status: "granted",
        notes: `${caseItem.notes}\nConsent verified on ${new Date().toISOString().slice(0, 10)} by ${consentSigner}. Notes: ${consentNotes}`.trim()
      });
      setLocalConsent("granted");
      setConsentMsg("Caregiver consent has been successfully verified and saved.");
    } catch (err) {
      setConsentMsg("Failed to verify consent on the backend. Please retry.");
    } finally {
      setConsentBusy(false);
    }
  }

  async function handleWithdrawConsent() {
    if (!confirm("Are you sure you want to withdraw consent? This will redact child details and disable clinical workflows for this case.")) return;
    setConsentBusy(true);
    setConsentMsg("");
    try {
      await withdrawBackendCaseConsent(caseItem.case_id, "Therapist request", true);
      setLocalConsent("withdrawn");
      setConsentMsg("Consent has been successfully withdrawn. Case details redacted.");
    } catch (err) {
      setConsentMsg("Failed to withdraw consent. Please try again.");
    } finally {
      setConsentBusy(false);
    }
  }
```

Render `PipelineProgressBar` inside `CaseDetailContent` right above the profile card.

- [ ] **Step 3: Modify PageHeader "Create new session" Action Button**

Make button conditional or disabled:
```typescript
        actions={
          <ActionButton
            href={isConsentGranted ? `/record?case_id=${caseItem.case_id}` : "#"}
            disabled={!isConsentGranted}
            className={!isConsentGranted ? "opacity-50 cursor-not-allowed" : ""}
          >
            Create new session
          </ActionButton>
        }
```

- [ ] **Step 4: Commit changes**
Run tests to make sure things build.

---

### Task 5: Consent Intake Gate and Pipeline Stepper in Session Intake Wizard

**Files:**
- Modify: `/Users/porschecaa/lingualens/apps/lingualens-app/src/components/session-workspace-client.tsx`

- [ ] **Step 1: Import new helpers and component**

Add imports to the top of `/Users/porschecaa/lingualens/apps/lingualens-app/src/components/session-workspace-client.tsx`:
```typescript
import { PipelineProgressBar } from "@/components/pipeline-progress-bar";
import { updateBackendCase } from "@/lib/workflow";
```

- [ ] **Step 2: Add inline Consent Verification Gate in Step 1 (Details)**

Inside `SessionWorkspaceClient` state, track `localConsent` for the case:
```typescript
  const [caseConsent, setCaseConsent] = useState<string>("granted");
  const [consentSigner, setConsentSigner] = useState("Parent");
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentNotes, setConsentNotes] = useState("");
```

Update the initial case fetch `useEffect` to capture the case consent:
```typescript
        const childCase = resolvedCaseId ? await getBackendCase(resolvedCaseId) : undefined;
        if (childCase) {
          setCaseConsent(childCase.consent_status ?? "pending");
        }
```

Inside Step 1 (`intakeStep === "details"`):
Check `caseConsent`. If it is not `"granted"`, render a blocking Consent Gate Card:
```typescript
          {intakeStep === "details" && caseConsent !== "granted" ? (
            <GlassCard className="space-y-5 p-5 sm:p-6" role="region" aria-label="Consent Intake Gate">
              <div>
                <h2 className="text-xl font-semibold text-ink">Consent Verification Required</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Audio processing, recording, and clinical observation suggested reviews are locked until parental/caregiver consent is verified.
                </p>
              </div>
              <form onSubmit={async (e) => {
                e.preventDefault();
                if (!consentChecked || !caseId) return;
                setBusy(true);
                try {
                  await updateBackendCase(caseId, { consent_status: "granted" });
                  setCaseConsent("granted");
                  setIntakeError("");
                } catch {
                  setIntakeError("Could not update case consent on the backend.");
                } finally {
                  setBusy(false);
                }
              }} className="space-y-4">
                <label className="flex items-start gap-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={consentChecked}
                    onChange={(event) => setConsentChecked(event.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-line"
                  />
                  <span>ข้าพเจ้ายืนยันว่าได้รับการลงนามยินยอมจากผู้ปกครองเพื่อรวบรวมตัวอย่างเสียงเรียบร้อยแล้ว</span>
                </label>
                <Field>
                  <label htmlFor="consent-signer" className="text-sm font-semibold text-ink">Signer Relation</label>
                  <select
                    id="consent-signer"
                    value={consentSigner}
                    onChange={(event) => setConsentSigner(event.target.value)}
                    className="min-h-11 rounded-2xl border border-line bg-white/80 px-4 py-3 text-sm"
                  >
                    <option value="Parent">Parent</option>
                    <option value="Guardian">Guardian</option>
                    <option value="Self">Self</option>
                  </select>
                </Field>
                <div className="flex justify-end gap-3">
                  <ActionButton type="submit" disabled={!consentChecked || busy}>
                    {busy ? "Verifying..." : "Verify & Grant Consent"}
                  </ActionButton>
                </div>
              </form>
            </GlassCard>
          ) : intakeStep === "details" ? (
             // Render the regular session details form here...
```

- [ ] **Step 3: Integrate `PipelineProgressBar`**

Render `<PipelineProgressBar currentStatus={pipelineStatusValue} />` right below `<PageHeader ... />` in `SessionWorkspaceClient`. Map the `pipelineStatusValue` dynamically from `state.transcriptAttested`, `state.featuresExtracted`, `uploadStep`, and `caseConsent`.

---

### Task 6: ML-Pending Observer Review with escape hatch in Results View

**Files:**
- Modify: `/Users/porschecaa/lingualens/apps/lingualens-app/src/components/session-workspace-client.tsx`

- [ ] **Step 1: Implement ML-Pending Loading Panel in `SessionResultsView`**

Inside `SessionResultsView`, check if the analysis status is processing or if ML suggestions are pending:
- If `state.analysisStatus === "processing"` or `!state.mlDecisionSupport`:
  - Render an animated loading state panel.
  - Display the safety disclosure: *"Linguistic observation analysis in progress. These suggestions support therapist decision-making and are not automated diagnoses."*
  - Include a button **"Skip to Manual Report"** that calls `onGenerateReport()`.

Implementation:
```typescript
  if (state.featuresExtracted && !state.mlDecisionSupport) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <GlassCard className="p-8 text-center space-y-5">
          <Loader2 className="mx-auto text-clinical animate-spin" size={38} aria-hidden="true" />
          <h1 className="text-2xl font-bold text-ink">Analyzing linguistic observations...</h1>
          <p className="text-sm leading-6 text-slate-600">
            ระบบสนับสนุนการตัดสินใจทางคลินิก (ML) กำลังประมวลผลคำแนะนำสนับสนุนการวิเคราะห์ข้อสังเกต โดยอ้างอิงสัญญาณทางภาษาที่สกัดได้
          </p>
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-xs text-blue-900 leading-5">
            ⚠️ <strong>ข้อควรระวังทางคลินิก:</strong> ข้อมูลวิเคราะห์จาก AI/ML เป็นเพียงข้อมูลเพื่อสนับสนุนการตัดสินใจและสนับสนุนทางคลินิกเท่านั้น (Decision-Support Only) ไม่ใช่ผลการวินิจฉัยโรคอัตโนมัติหรือแทนที่การประเมินโดยนักบำบัด
          </div>
          <div className="flex justify-center gap-3">
            <GradientButton
              onClick={onGenerateReport}
              disabled={busy}
              icon={ShieldCheck}
            >
              Skip to Draft Report
            </GradientButton>
          </div>
        </GlassCard>
      </div>
    );
  }
```

*(Note: Import `Loader2` from `lucide-react` if not already imported).*

- [ ] **Step 2: Verify typecheck**
Run: `npm run typecheck` to verify the code compiles correctly.

---

### Task 7: Update and run automated tests

**Files:**
- Modify: `/Users/porschecaa/lingualens/apps/lingualens-app/src/__tests__/cases-workspace-client.test.tsx`
- Modify: `/Users/porschecaa/lingualens/apps/lingualens-app/src/__tests__/session-intake-flow.test.tsx`
- Modify: `/Users/porschecaa/lingualens/apps/lingualens-app/src/__tests__/pages.test.tsx`

- [ ] **Step 1: Update `cases-workspace-client.test.tsx`**

Add tests checking that:
- Case details screen shows a warning banner and disables creation when `consent_status: "pending"`.
- Clicking "Verify and Grant Consent" triggers a PATCH request to `/cases/{caseId}` and enables session creation.
- Clicking "Withdraw Consent" sends a POST request to `/cases/{caseId}/withdraw-consent` and sets the status to `"withdrawn"`.

Write the test code details:
```typescript
  it("enforces consent status checks and blocks session creation", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases/case_demo_consent")) {
        return jsonResponse({
          case_id: "case_demo_consent",
          child_code: "C-CONSENT",
          nickname: "Consent Child",
          age_months: 50,
          language: "English",
          consent_status: "pending",
          notes: "Need signature.",
          care_team_user_ids: ["therapist-demo"]
        });
      }
      if (url.endsWith("/cases/case_demo_consent/timeline") || url.endsWith("/cases/case_demo_consent/goals")) {
        return jsonResponse([]);
      }
      return jsonResponse({});
    }));

    await renderAsyncPage(CaseDetailPage, { params: { caseId: "case_demo_consent" } });

    // Assert that the create session button is disabled and caution banner is shown
    const createBtn = screen.getByRole("link", { name: "Create new session" });
    expect(createBtn).toHaveClass("opacity-50 cursor-not-allowed");
    expect(screen.getByText("Case requires caregiver consent validation before starting clinical workflows.")).toBeInTheDocument();
  });
```

- [ ] **Step 2: Update `session-intake-flow.test.tsx`**

Add a test checking that:
- Recording or intake details is blocked when the case does not have caregiver consent.
- Submitting the consent verification form inline unlocks the wizard details.

- [ ] **Step 3: Update `pages.test.tsx`**

Add a test verifying that the results view shows the ML-pending loading screen, and that clicking the "Skip to Draft Report" button successfully sends a POST request to generate the draft report and routes to the report summary page.

- [ ] **Step 4: Run typecheck and tests**
Run:
```bash
cd apps/lingualens-app
npm run typecheck
npm test -- src/__tests__/pages.test.tsx src/__tests__/cases-workspace-client.test.tsx src/__tests__/session-intake-flow.test.tsx
npm run build
```
Verify: Ensure all tests compile and pass.

- [ ] **Step 5: Git commit**
Commit the final code updates with appropriate AI Co-Authored-By attribution:
```bash
git add src/lib/workflow.ts src/components/cases-workspace-client.tsx src/components/session-workspace-client.tsx src/components/status-badge.tsx src/components/pipeline-progress-bar.tsx src/__tests__/cases-workspace-client.test.tsx src/__tests__/session-intake-flow.test.tsx src/__tests__/pages.test.tsx
git commit -m "feat: integrate therapist workflow: consent gate, session pipeline bar, and ML pending skip actions"
```
