"use client";

import { AlertTriangle, CheckCircle2, Gauge, ShieldCheck } from "lucide-react";

import { PrimaryActionButton } from "@/components/workbench-ui";
import { SafetyNotice } from "@/components/safety-notice";
import { TranscriptEditorPanel } from "@/components/transcript-editor-panel";
import { SessionContextHeader, type SessionContext } from "@/features/sessions/components/session-context-header";
import { SessionGuide } from "@/features/sessions/components/session-guide";
import { resolveSessionHref } from "@/features/sessions/state/session-view";
import { EXTRACT_FEATURES_ACTION, GENERATE_REPORT_ACTION } from "@/lib/workflow-glossary";
import type { TranscriptLine, WorkflowState } from "@/lib/workflow";

export type SessionTranscriptViewProps = {
  sessionContext: SessionContext;
  state: WorkflowState;
  lines: TranscriptLine[];
  busy: boolean;
  onLinesChange: (lines: TranscriptLine[]) => void;
  onSaveDraft: () => void;
  onRunQa: () => void;
  onAttest: () => void;
  onExtractFeatures: () => void;
  onGenerateReport: () => void;
  onExport: () => void;
  backendUnavailable?: boolean;
  audioUrl?: string;
};

export function SessionTranscriptView({
  sessionContext,
  state,
  lines,
  busy,
  onLinesChange,
  onSaveDraft,
  onRunQa,
  onAttest,
  onExtractFeatures,
  onGenerateReport,
  onExport,
  backendUnavailable,
  audioUrl,
}: SessionTranscriptViewProps) {
  const reviewChecklist = [
    { label: "Draft saved", complete: state.transcriptSaveStatus === "saved" },
    { label: "QA completed", complete: state.qaStatus !== "not_run" && state.qaStatus !== "fail" },
    { label: "Therapist attested", complete: state.transcriptAttested },
    { label: "Features extracted", complete: state.featuresExtracted },
  ];
  const reportBlockedReason = getReviewReportBlockedReason(state);
  const canRetryAttestation = Boolean(
    state.backendTranscriptId
      && state.transcriptSaveStatus === "saved"
      && state.qaStatus !== "not_run"
      && state.qaStatus !== "fail"
      && !state.transcriptAttested,
  );
  const canExtractFeatures = Boolean(
    isTranscriptUnlocked(state) && !state.featuresExtracted && state.backendTranscriptId,
  );

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <SessionContextHeader
        density="compact"
        title="Review Transcript"
        description="Confirm speaker labels and transcript quality before report generation."
        context={sessionContext}
      />
      <SessionGuide
        testId="transcript-guide"
        prompt={
          state.transcriptAttested
            ? "The transcript is reviewed and attested. Next, we'll extract the language-sample features."
            : "Read through the transcript lines below and check the speaker labels and wording, then attest it."
        }
        quickReplies={[
          { label: "Go to findings", href: resolveSessionHref("findings", sessionContext.sessionId) },
          { label: "Go to report", href: resolveSessionHref("report", sessionContext.sessionId) },
        ]}
      />
      <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
      {state.transcriptDraftLabel ? (
        <div className="rounded-[var(--radius-panel)] border border-amber-200 bg-amber-50 p-4 text-amber-950">
          <p className="font-bold">{state.transcriptDraftLabel}</p>
          <p className="mt-1 text-sm">Experimental ASR can be inaccurate. Verify wording, timestamps, and speaker labels before attestation.</p>
        </div>
      ) : null}
      {state.chatWarnings && state.chatWarnings.length > 0 ? (
        <div className="rounded-[var(--radius-panel)] border border-amber-200 bg-amber-50 p-4 text-amber-950" role="status">
          <p className="font-bold">Import Warnings</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
            {state.chatWarnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}
      <div className="space-y-5">
        <section className="min-w-0">
            <TranscriptEditorPanel
              lines={lines}
              qaStatus={state.qaStatus}
              qaIssues={state.qaIssues}
              attested={state.transcriptAttested}
              busy={busy}
              saveStatus={state.transcriptSaveStatus}
              onChange={onLinesChange}
              onSaveDraft={onSaveDraft}
              backendUnavailable={backendUnavailable}
              onRunQa={onRunQa}
              onAttest={onAttest}
              onExport={onExport}
              audioUrl={audioUrl}
            />
        </section>
        <details className="responsive-details rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)]" data-testid="mobile-transcript-report-readiness">
          <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-ink">
            <span>Report readiness</span>
            <span className={reportBlockedReason ? "text-amber-800" : "text-emerald-700"}>{reportBlockedReason ? "Locked" : "Ready"}</span>
          </summary>
          <section className={`border-t p-4 md:border-t-0 ${
          reportBlockedReason
            ? "border-amber-200 bg-amber-50 text-amber-950"
            : "border-emerald-200 bg-emerald-50 text-emerald-950"
        }`} aria-label="Report generation readiness">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                {reportBlockedReason ? <AlertTriangle size={18} aria-hidden="true" /> : <CheckCircle2 size={18} aria-hidden="true" />}
                <h3 className="font-semibold">{reportBlockedReason ? "Report generation is locked" : "Ready to generate report"}</h3>
              </div>
              <p id="generate-report-blocked-reason" className="mt-2 text-sm font-medium" role={reportBlockedReason ? "status" : undefined}>
                {reportBlockedReason ?? "Transcript review is complete. Generate the therapist-editable draft report."}
              </p>
            </div>
            {canRetryAttestation ? (
              <button
                type="button"
                onClick={onAttest}
                disabled={busy}
                className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-[var(--radius-card)] bg-[color:var(--color-text-strong)] px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600 motion-reduce:transition-none"
              >
                <ShieldCheck size={17} aria-hidden="true" />
                {busy ? "Recording attestation..." : "Record attestation"}
              </button>
            ) : null}
            {canExtractFeatures ? (
              <button
                type="button"
                onClick={onExtractFeatures}
                disabled={busy}
                className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-[var(--radius-card)] bg-[color:var(--color-text-strong)] px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600 motion-reduce:transition-none"
              >
                <Gauge size={17} aria-hidden="true" />
                {busy ? "Extracting..." : EXTRACT_FEATURES_ACTION}
              </button>
            ) : null}
          </div>
          <ul className="mt-4 grid gap-2 text-sm sm:grid-cols-2 xl:grid-cols-4">
            {reviewChecklist.map((item) => (
              <li key={item.label} className="flex items-center gap-2 rounded-[var(--radius-card)] border border-black/5 bg-[color:var(--color-surface-reading)] px-3 py-2 font-medium">
                <span className={`grid h-5 w-5 place-items-center rounded-full text-xs font-bold ${item.complete ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"}`}>
                  {item.complete ? "✓" : "•"}
                </span>
                <span>{item.label}</span>
              </li>
            ))}
          </ul>
            <PrimaryActionButton
              icon={ShieldCheck}
              className="mt-4 w-full"
              onClick={onGenerateReport}
              disabled={busy || Boolean(reportBlockedReason)}
              aria-describedby={reportBlockedReason ? "generate-report-blocked-reason" : undefined}
              title={reportBlockedReason}
            >
              {GENERATE_REPORT_ACTION}
            </PrimaryActionButton>
          </section>
        </details>
        <details className="responsive-details rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)]" data-testid="mobile-transcript-review-requirements">
          <summary className="flex min-h-11 cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-ink">
            <span>Review requirements</span>
            <span aria-hidden="true">›</span>
          </summary>
          <div className="border-t border-line md:border-t-0">
            <SafetyNotice>
              Report generation requires a saved draft, completed QA, therapist attestation, and extracted language-sample features. Editing after attestation resets these gates.
            </SafetyNotice>
          </div>
        </details>
      </div>
    </div>
  );
}

function isTranscriptUnlocked(state: WorkflowState) {
  return state.transcriptAttested && state.transcriptReviewStatus === "reviewed";
}

function getReviewReportBlockedReason(state: WorkflowState) {
  if (state.transcriptSaveStatus !== "saved") return "Save the transcript draft before generating a report.";
  if (state.qaStatus === "not_run") return "Run transcript QA before generating a report.";
  if (state.qaStatus === "fail") return "Resolve transcript QA issues before generating a report.";
  if (state.error && state.statusMessage === "Attestation failed.") {
    return "Attestation did not finish. Try Attest transcript again before generating a report.";
  }
  if (!state.transcriptAttested || state.transcriptReviewStatus !== "reviewed") {
    return "Click Attest transcript before generating a report.";
  }
  if (!state.featuresExtracted) return "Extract language-sample features before generating a report.";
  return undefined;
}

function WorkflowStatus({ state, backendUnavailable }: { state: WorkflowState; backendUnavailable?: boolean }) {
  if (!state.statusMessage && !state.error) return null;
  const isError = Boolean(state.error);
  const routineSaveAnnouncement = !isError && (
    state.statusMessage === "Unsaved transcript edits."
    || state.statusMessage === "Transcript draft saved."
  );
  if (routineSaveAnnouncement) return null;
  if (state.statusMessage && !isError && backendUnavailable) return null;
  const className = isError
    ? "rounded-[var(--radius-panel)] border border-red-200 bg-red-50 p-4 text-sm text-red-950 animate-fade-in"
    : "rounded-[var(--radius-panel)] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 animate-fade-in";
  return (
    <div className={className} role={isError ? "alert" : "status"} aria-live="polite">
      {state.statusMessage ? <p className="font-semibold">{state.statusMessage}</p> : null}
      {state.error ? <p className="mt-1 font-semibold">{state.error}</p> : null}
    </div>
  );
}
