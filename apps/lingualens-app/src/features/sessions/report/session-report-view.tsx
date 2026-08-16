"use client";
import { useMemo } from "react";
import Link from "next/link";
import { Clipboard, Download, Send, ShieldCheck } from "lucide-react";
import { PrimaryActionButton, SafetyNote, WorkspacePanel } from "@/components/workbench-ui";
import { BackendAvailabilityBanner } from "@/components/backend-availability-banner";
import { SessionContextHeader } from "@/features/sessions/components/session-context-header";
import { ReportProvenanceItem, reportSectionDefinitions, WorkflowStatus } from "@/features/sessions/report/session-report-components";
import { useSessionReport, type SessionReportViewProps } from "@/features/sessions/report/use-session-report";
import {
  finalizedSafetyLabel,
  finalizedSafetyMetadataString,
  reportGeneratedVersion,
  reportMetadataString,
  reportSaveStateLabel,
  reportSourceLabel,
  reportWorkflowLabel,
  signedSnapshotNumber,
  signedSnapshotProviderString,
  signedSnapshotString,
  versionLabel,
} from "@/features/sessions/report/session-report-model";
import { GENERATE_REPORT_ACTION } from "@/lib/workflow-glossary";
export function SessionReportView(props: SessionReportViewProps) {
  const identityKey = JSON.stringify([
    props.sessionId ?? "",
    props.caseId ?? "",
    props.transcriptId ?? "",
    props.reportId ?? "",
  ]);
  return <ReportSummaryIdentityScope key={identityKey} {...props} />;
}

function ReportSummaryIdentityScope({ caseId, sessionId, transcriptId, reportId }: SessionReportViewProps) {
  const {
    hasLocator,
    state,
    busy,
    reportText,
    setReportText,
    therapistNotes,
    setTherapistNotes,
    goalsText,
    setGoalsText,
    exportedCha,
    providerId,
    setProviderId,
    allowFallback,
    setAllowFallback,
    backendReport,
    primaryTherapistLabel,
    primaryTherapistAssigned,
    confirmationChecked,
    setConfirmationChecked,
    snapshotIntegrity,
    backendUnavailable,
    isFailedSafety,
    isFinalized,
    isStale,
    isNotStarted,
    isSnapshotIntegrityChecking,
    hasSnapshotIntegrityError,
    signedSnapshotVerified,
    signedActionsBlocked,
    canRenderReportMetadata,
    isEditorLocked,
    transcriptUnlocked,
    identityLoaded,
    persist,
    handleGenerateDraft,
    handleSaveDraft,
    handleExport,
    handleExportCha,
    handleCopyLocalDemoShareLink,
    handleMarkSent,
    handleFinalize,
    handleCreateRevision,
    isFinalizeDisabled,
  } = useSessionReport({ caseId, sessionId, transcriptId, reportId });

  const reportSections = useMemo(() => reportSectionDefinitions.map((section) => {
    if (section.title !== "Strengths" || !state.featureSummary.length) return section;
    return {
      ...section,
      items: state.featureSummary.map((item) => `${item.label}: ${item.value}`),
    };
  }), [state.featureSummary]);

  return (
    <>
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <SessionContextHeader
        title="Report Summary"
        description="Review provenance, edit therapist-owned language, and complete sign-off gates before export."
        context={{
          sessionId: state.backendSessionId ?? state.sessionId ?? sessionId,
          caseId: state.caseId || caseId,
          caseLabel: state.childName || state.caseInfo.clientLabel || state.caseId || caseId,
          consentStatus: undefined,
          sourceLabel: isFinalized
            ? signedSnapshotVerified
              ? reportSourceLabel(backendReport)
              : undefined
            : reportSourceLabel(backendReport),
          workflowStatus: reportWorkflowLabel(state, backendReport),
          dataMode: state.backendSessionId
            ? "backend"
            : backendUnavailable && hasLocator
              ? "unavailable"
              : "local_draft",
          activeView: "report",
        }}
      />
      <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(18rem,26rem)_minmax(0,1fr)]">
      <div className="min-w-0 space-y-5">
        {isStale ? (
          <div className="rounded-[var(--radius-panel)] border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950" role="alert">
            <p className="font-semibold">This report is stale because the transcript changed.</p>
            <p className="mt-1" id="stale-report-explanation">The prior draft is read-only and cannot be saved, signed, exported, or shared as current.</p>
            <Link
              className="mt-3 inline-flex min-h-11 items-center rounded-[var(--radius-card)] bg-amber-900 px-4 font-semibold text-white"
              href={state.backendSessionId ? `/sessions/${state.backendSessionId}?view=findings` : "/cases?intent=start-session"}
            >
              Regenerate findings
            </Link>
          </div>
        ) : null}

        {hasSnapshotIntegrityError ? (
          <div className="rounded-[var(--radius-panel)] border border-red-300 bg-red-50 p-4 text-sm text-red-950" role="alert">
            <p className="font-semibold">Signed snapshot integrity error.</p>
            <p className="mt-1">{snapshotIntegrity.status === "invalid" ? snapshotIntegrity.reason : ""} The mutable report row is hidden, and export, revision, or sharing is blocked until the persisted signed snapshot is repaired and verified.</p>
          </div>
        ) : null}

        {isSnapshotIntegrityChecking ? (
          <div className="rounded-[var(--radius-panel)] border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-950" role="status" aria-live="polite">
            <p className="font-semibold">Verifying signed snapshot integrity…</p>
            <p className="mt-1">Export, revision, and sharing remain blocked until the signed payload hash is verified.</p>
          </div>
        ) : null}

        {identityLoaded && canRenderReportMetadata ? (
          <section
            aria-label="Report provenance"
            className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-5"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-ink">Report provenance</h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">Persisted versions are shown exactly as returned by the workflow API.</p>
              </div>
              {signedSnapshotVerified ? (
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-900">Signed snapshot · immutable</span>
              ) : isSnapshotIntegrityChecking ? (
                <span className="rounded-full bg-cyan-100 px-3 py-1 text-xs font-bold text-cyan-950">Verifying signed snapshot</span>
              ) : hasSnapshotIntegrityError ? (
                <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-900">Snapshot integrity error</span>
              ) : isStale ? (
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-950">Stale · regeneration required</span>
              ) : isFailedSafety ? (
                <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-900">Safety validation failed</span>
              ) : isNotStarted ? (
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">Never generated</span>
              ) : (
                <span className="rounded-full bg-[color:var(--color-accent-soft)] px-3 py-1 text-xs font-bold text-[color:var(--color-accent-strong)]">Editable draft</span>
              )}
            </div>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              <ReportProvenanceItem
                label="Reviewed transcript"
                value={versionLabel(reportGeneratedVersion(backendReport, state, "transcript_version") ?? (isFinalized ? undefined : state.backendTranscriptVersion))}
              />
              <ReportProvenanceItem label="Report version" value={versionLabel(isFinalized ? signedSnapshotNumber(backendReport, "report_version") : backendReport?.version ?? state.backendReportVersion)} />
              <ReportProvenanceItem label="Feature result ID" value={(isFinalized ? signedSnapshotString(backendReport, "feature_result_id") : backendReport?.feature_result_id ?? state.featureSetId) ?? "Unavailable"} />
              <ReportProvenanceItem
                label="Feature schema version"
                value={String(reportGeneratedVersion(backendReport, state, "schema_version") ?? (isFinalized ? undefined : backendReport?.feature_schema_version ?? state.featureSchemaVersion) ?? "Unavailable")}
              />
              <ReportProvenanceItem
                label="Revision"
                value={isFinalized || backendReport?.revision_number == null ? "Unavailable" : `Revision ${backendReport.revision_number}`}
              />
              {isFinalized ? (
                <>
                  <ReportProvenanceItem label="Signed snapshot version" value={versionLabel(signedSnapshotNumber(backendReport, "report_version"))} />
                  <ReportProvenanceItem label="Signed snapshot hash" value={signedSnapshotString(backendReport, "report_hash") ?? "Unavailable"} />
                  <ReportProvenanceItem label="Signed by" value={signedSnapshotString(backendReport, "signed_by") ?? "Unavailable"} />
                  <ReportProvenanceItem label="Signed at" value={signedSnapshotString(backendReport, "signed_at") ?? "Unavailable"} />
                </>
              ) : null}
            </dl>
          </section>
        ) : null}

        {identityLoaded && canRenderReportMetadata ? (
          <section aria-label="Report source and safety" className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-5">
            <h2 className="text-lg font-bold text-ink">Report source and safety</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">Persisted provider and validation metadata. Missing values are shown as unavailable.</p>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              <ReportProvenanceItem label="Requested provider" value={reportMetadataString(backendReport, "requested_provider") ?? "Unavailable"} />
              <ReportProvenanceItem label="Actual provider" value={reportMetadataString(backendReport, "actual_provider") ?? "Unavailable"} />
              <ReportProvenanceItem label="Provider version" value={reportMetadataString(backendReport, "provider_version") ?? "Unavailable"} />
              <ReportProvenanceItem label="Fallback reason" value={(isFinalized ? signedSnapshotProviderString(backendReport, "fallback_reason") : backendReport?.fallback_reason) ?? "Unavailable"} />
              <ReportProvenanceItem label="Validator version" value={(isFinalized ? finalizedSafetyMetadataString(backendReport, "validator_version") : backendReport?.validator_version) ?? "Unavailable"} />
              <ReportProvenanceItem label="Rule-set version" value={(isFinalized ? finalizedSafetyMetadataString(backendReport, "rule_set_version") : backendReport?.rule_set_version) ?? "Unavailable"} />
              <ReportProvenanceItem label="Finalized safety" value={finalizedSafetyLabel(backendReport)} />
              <ReportProvenanceItem label="Input hash" value={(isFinalized ? signedSnapshotString(backendReport, "input_hash") : backendReport?.input_hash) ?? "Unavailable"} />
            </dl>
          </section>
        ) : null}

        {identityLoaded ? (
          <section aria-label="Report workflow states" className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-5">
            <h2 className="text-lg font-bold text-ink">Save, sign-off, and export</h2>
            <dl className="mt-4 grid gap-3 sm:grid-cols-3">
              <ReportProvenanceItem label="Save" value={isSnapshotIntegrityChecking ? "Verifying snapshot" : hasSnapshotIntegrityError ? "Integrity error" : isNotStarted ? "Never generated" : reportSaveStateLabel(state.reportSaveStatus, isFinalized, isStale)} />
              <ReportProvenanceItem label="Sign-off" value={isSnapshotIntegrityChecking ? "Signed record — verifying" : hasSnapshotIntegrityError ? "Signed record — snapshot invalid" : isFinalized ? "Signed" : isStale ? "Blocked — regenerate" : isNotStarted ? "Blocked — generate report" : "Therapist confirmation required"} />
              <ReportProvenanceItem label="Report export" value={isSnapshotIntegrityChecking ? "Blocked — verifying" : hasSnapshotIntegrityError ? "Blocked — integrity error" : isFinalized ? "Eligible" : isStale ? "Blocked — regenerate" : isNotStarted ? "Blocked — generate report" : "Available after sign-off"} />
              <ReportProvenanceItem label="Reviewed-cues acknowledgement" value={state.cuesAcknowledgedAt ? `${state.cuesAcknowledgedBy ?? "Therapist"} — ${new Date(state.cuesAcknowledgedAt).toLocaleDateString()}` : "Not recorded"} />
            </dl>
          </section>
        ) : null}

        {identityLoaded && !isFinalized ? <WorkspacePanel className="divide-y divide-line/70 p-5">
          {reportSections.map((section) => {
            const Icon = section.icon;
            return (
              <div key={section.title} className="flex gap-4 py-4 first:pt-0 last:pb-0">
                <Icon size={22} aria-hidden="true" className="mt-1 shrink-0 text-[color:var(--color-accent)]" />
                <div>
                  <h3 className="text-lg font-bold text-ink">{section.title}</h3>
                  <ul className="mt-2 space-y-1 text-sm text-slate-700">
                    {section.items.map((item) => <li key={item}>• {item}</li>)}
                  </ul>
                </div>
              </div>
            );
          })}
        </WorkspacePanel> : null}

        {!isFinalized ? <>
        <WorkspacePanel className="p-5 space-y-4">
          <h2 className="text-lg font-bold text-ink">Report inputs</h2>
          <div>
            <label className="block text-sm font-semibold text-ink" htmlFor="therapist-notes">Therapist notes</label>
            <textarea id="therapist-notes" aria-label="Therapist notes" className="mt-2 min-h-24 w-full rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-3 outline-none focus:ring-2 focus:ring-clinical text-sm" value={therapistNotes} readOnly={isEditorLocked} onChange={(event) => {
              if (isEditorLocked) return;
              setTherapistNotes(event.target.value);
              persist({ ...state, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
            }} />
          </div>
          <div>
            <label className="mt-2 block text-sm font-semibold text-ink" htmlFor="therapy-goals">Therapy goals</label>
            <textarea id="therapy-goals" aria-label="Therapy goals" className="mt-2 min-h-24 w-full rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-3 outline-none focus:ring-2 focus:ring-clinical text-sm" value={goalsText} readOnly={isEditorLocked} onChange={(event) => {
              if (isEditorLocked) return;
              setGoalsText(event.target.value);
              persist({ ...state, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
            }} />
          </div>
        </WorkspacePanel>

        <WorkspacePanel className="p-5 space-y-4">
          <h2 className="text-lg font-bold text-ink">Report Assistant Settings</h2>
          <div>
            <label className="block text-sm font-semibold text-ink" htmlFor="provider-selector">Drafting Provider</label>
            <select
              id="provider-selector"
              className="mt-2 w-full rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-3 text-sm font-medium focus:ring-2 focus:ring-clinical outline-none"
              value={providerId}
              disabled={isEditorLocked}
              onChange={(e) => setProviderId(e.target.value)}
            >
              <option value="template">Deterministic Template Provider</option>
              <option value="local_llm">Local LLM Provider (Llama 3)</option>
            </select>
          </div>
          {providerId === "local_llm" && (
            <label className="flex min-h-11 cursor-pointer select-none items-center gap-3 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-line text-clinical focus:ring-clinical focus:ring-offset-0"
                checked={allowFallback}
                disabled={isEditorLocked}
                onChange={(e) => setAllowFallback(e.target.checked)}
              />
              <span className="text-slate-700 font-medium">
                Allow safe template fallback if LLM fails
              </span>
            </label>
          )}
        </WorkspacePanel>
        </> : null}

        {!isFinalized && !isFailedSafety && !isStale && (
          <WorkspacePanel className="p-5 space-y-4 animate-fade-in border border-[color:var(--color-border)]">
            <h2 className="text-lg font-bold text-ink">Sign-off Confirmation</h2>
            <div className="rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-4">
              <p className="text-sm font-semibold text-ink">Primary assigned therapist</p>
              <p className="mt-2 text-sm text-slate-700">{primaryTherapistLabel}</p>
              <p className="mt-2 text-xs leading-5 text-slate-600">
                Report sign-off uses the authenticated therapist identity from the active session. The client does not choose or override the signer.
              </p>
            </div>
            {!primaryTherapistAssigned ? (
              <p className="rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900">
                Assign a primary therapist before finalizing this report.
              </p>
            ) : null}
            <label className="flex min-h-11 cursor-pointer select-none items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 shrink-0 rounded border-line text-clinical focus:ring-clinical focus:ring-offset-0"
                checked={confirmationChecked}
                onChange={(e) => setConfirmationChecked(e.target.checked)}
              />
              <span className="text-slate-700 font-medium">
                I check and confirm that this report does not contain diagnostic assertions, and is for clinical decision-support only.
              </span>
            </label>
          </WorkspacePanel>
        )}

        <WorkspacePanel className="p-5">
          <h2 className="text-lg font-bold text-ink">Share with caregiver</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Local/demo status only. This does not send a message, create a production delivery channel, or claim secure caregiver sharing.
          </p>
          <p className="mt-2 font-bold text-clinical">{state.shareStatus}</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-3 font-semibold" disabled={!identityLoaded || isStale || signedActionsBlocked} onClick={handleCopyLocalDemoShareLink}>
              <Clipboard size={17} aria-hidden="true" /> Copy local demo share link
            </button>
            <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-3 font-semibold" disabled={!identityLoaded || isStale || signedActionsBlocked} onClick={handleMarkSent}>
              <Send size={17} aria-hidden="true" /> Mark caregiver share recorded
            </button>
          </div>
        </WorkspacePanel>

        <PrimaryActionButton
          icon={ShieldCheck}
          className="w-full text-xl"
          onClick={handleFinalize}
          disabled={isFinalizeDisabled}
          data-testid="finalize-report-button"
        >
          {isFinalized ? "Report Finalized" : backendUnavailable ? "Finalize Report (Online only)" : "Finalize Report"}
        </PrimaryActionButton>
        {isFinalized ? (
          <button
            type="button"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-card)] border border-clinical bg-[color:var(--color-surface-reading)] px-4 text-sm font-bold text-clinical disabled:opacity-50"
            onClick={() => void handleCreateRevision()}
            disabled={busy || backendUnavailable || signedActionsBlocked || !(backendReport?.report_id ?? state.reportId)}
          >
            {busy ? "Creating revision..." : "Create report revision"}
          </button>
        ) : null}
        {state.finalizeStatus ? <p className="demo-note rounded-[var(--radius-panel)] p-3 text-sm">{state.finalizeStatus}</p> : null}
        <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
        <SafetyNote>Decision-support only. Not diagnostic. Final report text must be reviewed by the therapist.</SafetyNote>
      </div>

      <WorkspacePanel className="min-w-0 p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-ink">
              {isSnapshotIntegrityChecking ? "Verifying signed report" : hasSnapshotIntegrityError ? "Signed report unavailable" : isFinalized ? "Signed report snapshot" : isStale ? "Stale report draft" : isNotStarted ? "Report not generated" : "Draft report preview"}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {isSnapshotIntegrityChecking
                ? "The signed payload is hidden until its canonical SHA-256 hash is verified."
                : hasSnapshotIntegrityError
                ? "The signed snapshot did not pass integrity checks. Mutable row content is not displayed."
                : isFinalized
                ? "This signed snapshot is read-only and immutable. Create a revision for any further changes."
                : isStale
                  ? "This prior draft is read-only and cannot be used as current report content."
                  : isNotStarted
                    ? "No report has been generated. Generate a draft from the reviewed transcript and current findings to begin."
                    : "This draft is editable and remains decision-support until therapist finalization."}
            </p>
          </div>
          <button
            className="rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-2 text-sm font-bold text-clinical disabled:opacity-50"
            onClick={() => handleGenerateDraft(false)}
            disabled={busy || isFinalized || isStale || !transcriptUnlocked}
            data-testid="generate-report-draft-button"
          >
            {busy ? "Working" : GENERATE_REPORT_ACTION}
          </button>
        </div>
        {!transcriptUnlocked ? (
          <p className="mt-4 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900">
            Transcript review and attestation are required before report generation.
          </p>
        ) : null}

        {/* Failed Safety Warning Banner */}
        {!isFinalized && isFailedSafety && (
          <div className="mt-4 rounded-[var(--radius-panel)] border border-red-200 bg-red-50 p-5 text-red-950 animate-fade-in" data-testid="report-safety-failed">
            <h3 className="text-lg font-bold text-red-900">Safety Validation Failed</h3>
            <p className="mt-1 text-sm text-red-800">
              The drafted report contains prohibited diagnostic wording or fails required safety disclaimers. 
              The draft has been locked from editing and finalization for clinical safety.
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              {backendReport?.safety_validation_result?.issues.map((issue: any) => (
                <li key={issue.issue_id} className="flex items-start gap-2 bg-[color:var(--color-surface-muted)] p-3 rounded-[var(--radius-card)] border border-red-100">
                  <span className="font-bold text-red-700 uppercase tracking-wide text-xs bg-red-100 px-2 py-0.5 rounded shrink-0 mt-0.5">
                    {issue.severity}
                  </span>
                  <div>
                    <p className="font-semibold text-red-900">{issue.message}</p>
                    {issue.detected_text && (
                      <p className="mt-1 text-xs text-slate-700">
                        Detected: <code className="bg-red-100/50 px-1 py-0.5 rounded text-red-800 font-mono">&quot;{issue.detected_text}&quot;</code>
                      </p>
                    )}
                    {issue.suggested_fix && (
                      <p className="mt-1 text-xs text-slate-600 italic">
                        Fix: {issue.suggested_fix}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            <button
              onClick={() => handleGenerateDraft(true)}
              className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-card)] bg-clinical px-5 font-bold text-white hover:bg-[color:var(--color-accent-strong)] active:scale-95 transition-transform"
              data-testid="regenerate-safe-template-button"
            >
              Regenerate using Safe Template
            </button>
          </div>
        )}

        {/* Non-blocking Safety Warnings (Yellow Alert) */}
        {!isFinalized && !isFailedSafety && backendReport?.safety_validation_result?.issues && backendReport.safety_validation_result.issues.length > 0 && (
          <div className="mt-4 rounded-[var(--radius-panel)] border border-amber-200 bg-amber-50 p-5 text-amber-950 animate-fade-in" data-testid="report-safety-warning">
            <h3 className="text-lg font-bold text-amber-900">Clinical Safety Warnings</h3>
            <p className="mt-1 text-sm text-amber-800">
              Please address the following safety rules in your draft. Finalization is blocked until they are resolved.
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              {backendReport.safety_validation_result.issues.map((issue: any) => (
                <li key={issue.issue_id} className="flex items-start gap-2 bg-[color:var(--color-surface-muted)] p-3 rounded-[var(--radius-card)] border border-amber-100">
                  <span className="font-bold text-amber-700 uppercase tracking-wide text-xs bg-amber-100 px-2 py-0.5 rounded shrink-0 mt-0.5">
                    {issue.severity}
                  </span>
                  <div>
                    <p className="font-semibold text-amber-900">{issue.message}</p>
                    {issue.detected_text && (
                      <p className="mt-1 text-xs text-slate-700">
                        Detected: <code className="bg-amber-100/50 px-1 py-0.5 rounded text-amber-800 font-mono">&quot;{issue.detected_text}&quot;</code>
                      </p>
                    )}
                    {issue.suggested_fix && (
                      <p className="mt-1 text-xs text-slate-600 italic">
                        Fix: {issue.suggested_fix}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        <textarea className="mt-5 min-h-80 w-full rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-4 text-sm leading-6 text-ink outline-none focus:ring-2 focus:ring-clinical" value={reportText} readOnly={isEditorLocked || isNotStarted} onChange={(event) => {
          if (isEditorLocked || isNotStarted) return;
          setReportText(event.target.value);
          persist({ ...state, reportMarkdown: event.target.value, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
        }} aria-label={isStale ? "Stale read-only report" : isFinalized ? "Finalized report" : isNotStarted ? "Report not generated" : "Editable draft report preview"} aria-describedby={isStale ? "stale-report-explanation" : undefined} data-testid="report-preview" />
        <p className="mt-2 text-sm font-semibold text-slate-600" role="status">
          {state.reportSaveStatus === "saving" ? "Saving..." : state.reportSaveStatus === "saved" ? "Saved" : state.reportSaveStatus === "failed" ? "Failed to save" : state.reportSaveStatus === "unsaved" ? "Unsaved changes" : "Not saved"}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-[var(--radius-card)] border border-clinical bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50"
            onClick={handleSaveDraft}
            disabled={busy || isEditorLocked || !state.reportId || state.reportSaveStatus === "saved"}
            data-testid="save-report-draft-button"
          >
            Save draft
          </button>
        </div>
        <div className="mt-4 border-t border-line pt-4">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Export</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button className="inline-flex items-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50" disabled={!isFinalized || signedActionsBlocked} onClick={() => void handleExport("markdown")}><Download size={18} aria-hidden="true" />Export Markdown</button>
            <button className="inline-flex items-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50" disabled={!isFinalized || signedActionsBlocked} onClick={() => void handleExport("html")}><Download size={18} aria-hidden="true" />Export HTML</button>
            <button className="inline-flex items-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm font-bold text-slate-500 disabled:opacity-60" disabled>Export PDF later</button>
            <button className="inline-flex items-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50" onClick={handleExportCha} disabled={!state.transcriptAttested || state.transcriptReviewStatus !== "reviewed"}><Download size={18} aria-hidden="true" />Export reviewed .cha</button>
          </div>
        </div>
        {exportedCha ? <textarea className="mt-4 h-40 w-full rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-3 font-mono text-xs" readOnly value={exportedCha} aria-label="Exported reviewed CHA" /> : null}
      </WorkspacePanel>
      </div>
    </>
  );
}

export type { SessionReportViewProps } from "@/features/sessions/report/use-session-report";
