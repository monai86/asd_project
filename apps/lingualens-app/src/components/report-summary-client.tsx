"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Clipboard, Download, Heart, Send, ShieldCheck, Star } from "lucide-react";

import { GlassCard, GradientButton, ProgressSummaryCard, SafetyNote } from "@/components/liquid-ui";
import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import { ApiError } from "@/lib/api";
import {
  classifyWorkflowLoadFailure,
  createIdentityScopedWorkflowState,
  createInitialWorkflowState,
  exportBackendReport,
  exportReviewedCha,
  finalizeBackendReport,
  generateBackendReport,
  getBackendCase,
  getBackendReport,
  getBackendSession,
  getBackendTranscript,
  loadWorkflowState,
  saveWorkflowState,
  updateBackendReport,
  type WorkflowState
} from "@/lib/workflow";

function clinicianLabel(userId: string) {
  if (userId === "therapist-demo") return "Demo Therapist";
  return userId
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

const sections = [
  {
    icon: Star,
    title: "Strengths",
    tone: "bg-emerald-100 text-emerald-700",
    items: ["Reviewed transcript available", "Feature summary prepared for therapist interpretation"]
  },
  {
    icon: Heart,
    title: "Needs Support",
    tone: "bg-orange-100 text-orange-600",
    items: ["Confirm transcript wording", "Review suggested next steps before sharing"]
  },
  {
    icon: ArrowRight,
    title: "Next Steps",
    tone: "bg-[#efeaff] text-clinical",
    items: ["Edit draft report language", "Finalize only after therapist review"]
  }
];

type ReportSummaryClientProps = {
  caseId?: string;
  sessionId?: string;
  transcriptId?: string;
  reportId?: string;
};

export function ReportSummaryClient(props: ReportSummaryClientProps) {
  const identityKey = JSON.stringify([
    props.sessionId ?? "",
    props.caseId ?? "",
    props.transcriptId ?? "",
    props.reportId ?? "",
  ]);
  return <ReportSummaryIdentityScope key={identityKey} {...props} />;
}

function ReportSummaryIdentityScope({ caseId, sessionId, transcriptId, reportId }: ReportSummaryClientProps) {
  const hasLocator = Boolean(reportId || sessionId);
  const [state, setState] = useState<WorkflowState>(() => hasLocator
    ? createIdentityScopedWorkflowState({ workflowLoading: true, statusMessage: "Loading persisted report..." })
    : createInitialWorkflowState());
  const [busy, setBusy] = useState(false);
  const [reportText, setReportText] = useState("");
  const [therapistNotes, setTherapistNotes] = useState("");
  const [goalsText, setGoalsText] = useState("");
  const [exportedCha, setExportedCha] = useState("");
  const [providerId, setProviderId] = useState<string>("template");
  const [allowFallback, setAllowFallback] = useState<boolean>(false);
  const [backendReport, setBackendReport] = useState<any | null>(null);
  const [primaryTherapistLabel, setPrimaryTherapistLabel] = useState<string>(hasLocator ? "" : "Authenticated primary therapist");
  const [primaryTherapistAssigned, setPrimaryTherapistAssigned] = useState<boolean>(!hasLocator);
  const [confirmationChecked, setConfirmationChecked] = useState<boolean>(!hasLocator);
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  
  const isFailedSafety = backendReport?.status === "Failed";
  const isFinalized = state.reportStatus === "finalized" || backendReport?.status === "Signed Off";
  const isStale = state.reportStatus === "stale" || backendReport?.status === "stale";
  const isEditorLocked = isFinalized || isFailedSafety || isStale;
  const transcriptUnlocked = state.transcriptAttested && state.transcriptReviewStatus === "reviewed";

  useEffect(() => {
    let cancelled = false;
    if (!reportId && !sessionId) {
      const stored = loadWorkflowState();
      setState(stored);
      setReportText(stored.reportMarkdown ?? createDraftText(stored));
      setTherapistNotes(stored.therapistNotes);
      setGoalsText(stored.therapyGoals.join("\n"));
      return;
    }

    const loadingState = saveWorkflowState(createIdentityScopedWorkflowState({
      workflowLoading: true,
      statusMessage: "Loading persisted report...",
      error: undefined,
    }));
    setBackendUnavailable(false);
    setState(loadingState);
    setReportText("");
    setTherapistNotes("");
    setGoalsText("");
    setExportedCha("");
    setBackendReport(null);
    setProviderId("template");
    setPrimaryTherapistLabel("");
    setPrimaryTherapistAssigned(false);
    setConfirmationChecked(false);
    void (async () => {
      try {
        const session = sessionId ? await getBackendSession(sessionId) : undefined;
        const resolvedReportId = reportId ?? session?.report_id;
        if (!resolvedReportId) throw new ApiError(404, "Report not found.");
        const report = await getBackendReport(resolvedReportId);
        const resolvedTranscriptId = transcriptId ?? session?.transcript_id;
        const transcript = resolvedTranscriptId ? await getBackendTranscript(resolvedTranscriptId) : undefined;
        const resolvedCaseId = caseId ?? report.case_id ?? session?.case_id;
        const childCase = resolvedCaseId ? await getBackendCase(resolvedCaseId) : undefined;
        const finalized = report.status === "Signed Off";
        
        if (cancelled) return;
        setBackendReport(report);
        setProviderId(report.requested_provider ?? "template");
        setPrimaryTherapistAssigned(Boolean(childCase?.primary_therapist_user_id));
        setPrimaryTherapistLabel(
          childCase?.primary_therapist_user_id
            ? clinicianLabel(childCase.primary_therapist_user_id)
            : "Primary therapist assignment required",
        );
        
        const hydrated = saveWorkflowState({
          ...createIdentityScopedWorkflowState(),
          sessionId: report.session_id ?? session?.session_id,
          caseId: resolvedCaseId,
          caseInfo: {
            caseId: resolvedCaseId,
            clientLabel: childCase?.nickname ?? childCase?.child_code ?? ""
          },
          childName: childCase?.nickname ?? childCase?.child_code ?? "",
          backendSessionId: report.session_id ?? session?.session_id,
          backendTranscriptSessionId: transcript?.session_id ?? report.session_id ?? session?.session_id,
          backendTranscriptId: transcript?.transcript_id,
          backendTranscriptVersion: transcript?.version,
          transcriptAttested: Boolean(transcript?.therapist_attested),
          transcriptReviewStatus: transcript?.therapist_attested ? "reviewed" : "in_review",
          backendReportId: resolvedReportId,
          backendReportVersion: report.version,
          reportId: resolvedReportId,
          reportMarkdown: report.markdown ?? "",
          therapistNotes: report.therapist_notes ?? "",
          therapyGoals: report.session_goals ?? [],
          featureSetId: report.feature_result_id,
          reportGeneratedFromVersions: report.generated_from_versions,
          reportStatus: report.status === "stale" ? "stale" : finalized ? "finalized" : "draft",
          reportSaveStatus: "saved",
          workflowLoading: false,
          finalizeStatus: finalized ? "Report finalized." : undefined,
          statusMessage: report.status === "Failed" ? "Safety check failed." : finalized ? "Finalized report loaded." : "Report draft loaded.",
          error: undefined
        });
        setState(hydrated);
        setReportText(hydrated.reportMarkdown ?? "");
        setTherapistNotes(hydrated.therapistNotes);
        setGoalsText(hydrated.therapyGoals.join("\n"));
      } catch (error) {
        if (cancelled) return;
        const failure = classifyWorkflowLoadFailure(error, "report");
        setBackendUnavailable(failure.backendUnavailable);
        const failedState = saveWorkflowState(createIdentityScopedWorkflowState({
          workflowLoading: false,
          statusMessage: failure.statusMessage,
          error: failure.error,
        }));
        setState(failedState);
        setReportText("");
        setTherapistNotes("");
        setGoalsText("");
        setExportedCha("");
        setBackendReport(null);
        setPrimaryTherapistLabel("");
        setPrimaryTherapistAssigned(false);
        setConfirmationChecked(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [caseId, reportId, sessionId, setBackendUnavailable, transcriptId]);

  useEffect(() => {
    if (state.reportSaveStatus !== "unsaved" && state.reportSaveStatus !== "failed") return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [state.reportSaveStatus]);

  const reportSections = useMemo(() => sections.map((section) => {
    if (section.title !== "Strengths" || !state.featureSummary.length) {
      return section;
    }
    return {
      ...section,
      items: state.featureSummary.map((item) => `${item.label}: ${item.value}`)
    };
  }), [state.featureSummary]);
  const identityLoaded = !hasLocator || Boolean(state.backendReportId && !state.workflowLoading && !state.error);

  function persist(next: WorkflowState) {
    const saved = saveWorkflowState(next);
    setState(saved);
    return saved;
  }

  async function handleGenerateDraft(forceTemplate: boolean = false) {
    if (isFinalized || !transcriptUnlocked) return;
    setBusy(true);
    const selectedProvider = forceTemplate ? "template" : providerId;
    const reportingState = persist({
      ...state,
      therapistNotes,
      therapyGoals: parseGoals(goalsText),
      statusMessage: "Generating report draft...",
      error: undefined
    });
    try {
      const targetSession = reportingState.backendTranscriptSessionId ?? reportingState.backendSessionId;
      if (!targetSession) throw new Error("Persistent session unavailable.");
      const report = await generateBackendReport(targetSession, selectedProvider, allowFallback, therapistNotes, parseGoals(goalsText));
      if (!report.report_id) throw new Error("Report ID missing.");
      setBackendReport(report);
      const markdown = report.content_markdown ?? report.markdown ?? "";
      setReportText(markdown);
      
      persist({
        ...reportingState,
        backendReportId: report.report_id,
        reportId: report.report_id,
        reportMarkdown: markdown,
        reportStatus: "draft",
        reportSaveStatus: "saved",
        statusMessage: report.status === "Failed" 
          ? "Safety check failed. The drafted text contains prohibited phrases or missing disclaimers."
          : "Draft report preview generated successfully. Therapist edits required.",
        error: undefined
      });
    } catch (err: any) {
      persist({ ...reportingState, reportSaveStatus: "failed", statusMessage: "Report generation failed.", error: err?.message ?? "Error drafting report." });
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveDraft() {
    if (!state.reportId || isFinalized || isStale) return;
    setBusy(true);
    const saving = persist({ ...state, reportSaveStatus: "saving", statusMessage: "Saving report draft...", error: undefined });
    try {
      const markdown = mergeReportInputs(reportText, therapistNotes, parseGoals(goalsText));
      const report = await updateBackendReport(state.reportId, markdown, therapistNotes);
      setBackendReport(report);
      setReportText(report.markdown ?? markdown);
      
      persist({
        ...saving,
        reportMarkdown: report.markdown ?? markdown,
        therapistNotes,
        therapyGoals: parseGoals(goalsText),
        reportStatus: "reviewed",
        reportSaveStatus: "saved",
        statusMessage: report.status === "Failed" ? "Saved, but safety validation issues exist." : "Report draft saved.",
        error: undefined
      });
    } catch {
      setBackendUnavailable(true);
      persist({ ...saving, reportSaveStatus: "failed", statusMessage: "Failed to save report.", error: "Backend unavailable. Report edits remain unsaved." });
    } finally {
      setBusy(false);
    }
  }

  async function handleExport(format: "markdown" | "html") {
    if (!state.reportId || !isFinalized) return;
    try {
      const exported = await exportBackendReport(state.reportId, format);
      downloadTextFile(exported.content, exported.filename, exported.content_type);
      persist({ ...state, statusMessage: `${format === "markdown" ? "Markdown" : "HTML"} report exported.`, error: undefined });
    } catch {
      setBackendUnavailable(true);
      persist({ ...state, statusMessage: "Export failed.", error: "Backend report export was unavailable." });
    }
  }

  async function handleExportCha() {
    if (!state.backendTranscriptId || !state.transcriptAttested) return;
    try {
      const exported = await exportReviewedCha(state.backendTranscriptId);
      setExportedCha(exported.cha_text);
      downloadTextFile(exported.cha_text, exported.filename, "text/x-chat");
    } catch {
      setBackendUnavailable(true);
      persist({ ...state, statusMessage: "Export failed.", error: "Backend transcript export was unavailable." });
    }
  }

  async function handleCopyLocalDemoShareLink() {
    if (isStale) return;
    const localLink = `/report-summary?report_id=${state.reportId ?? ""}&session_id=${state.sessionId ?? ""}&case_id=${state.caseId ?? ""}`;
    await navigator.clipboard?.writeText(localLink);
    persist({
      ...state,
      reportMarkdown: reportText,
      shareStatus: "Local demo share link copied",
      statusMessage: "Local demo share-link status recorded. No caregiver delivery endpoint was created."
    });
  }

  function handleMarkSent() {
    if (isStale) return;
    persist({
      ...state,
      reportMarkdown: reportText,
      shareStatus: "Caregiver share recorded locally",
      statusMessage: "Caregiver share status recorded locally. No external delivery was sent."
    });
  }

  async function handleFinalize() {
    if (isFinalized || isStale || !state.reportId || state.reportSaveStatus !== "saved" || !confirmationChecked) return;
    setBusy(true);
    try {
      const finalized = await finalizeBackendReport(state.reportId, confirmationChecked);
      setBackendReport(finalized);
      const markdown = finalized.markdown ?? reportText;
      setReportText(markdown);
      persist({
        ...state,
        reportStatus: "finalized",
        reportMarkdown: markdown,
        reportSaveStatus: "saved",
        finalizeStatus: "Report finalized.",
        statusMessage: "Report finalized.",
        error: undefined
      });
    } catch (err: any) {
      persist({ ...state, statusMessage: "Report finalization failed.", error: err?.message ?? "Safety validation error. Correct prohibited claims and missing disclaimers." });
    } finally {
      setBusy(false);
    }
  }

  const isFinalizeDisabled = busy ||
    state.reportStatus === "not_started" ||
    isStale ||
    isFinalized ||
    state.reportSaveStatus !== "saved" ||
    !confirmationChecked ||
    !primaryTherapistAssigned ||
    isFailedSafety ||
    backendReport?.finalization_blocked === true ||
    backendUnavailable;

  return (
    <>
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <div className="grid gap-6 lg:grid-cols-[430px_1fr]">
      <div className="space-y-5">
        <header>
          <h1 className="text-3xl font-bold text-ink">Report Summary</h1>
        </header>

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

        {identityLoaded ? <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-14 w-14 place-items-center rounded-full bg-gradient-to-br from-orange-100 to-sky-100 text-xl">EL</span>
            <div>
              <h2 className="text-xl font-bold text-ink">{state.childName}</h2>
              <p className="text-slate-600">{state.reportPeriod}</p>
            </div>
          </div>
          <span className={`rounded-full px-5 py-2 font-bold ${
            isFailedSafety ? "bg-red-100 text-red-700" : "bg-[#efeaff] text-clinical"
          }`}>
            {isFailedSafety ? "Safety Failed" : state.reportStatus === "not_started" ? "Draft" : state.reportStatus === "stale" ? "Stale" : state.reportStatus[0].toUpperCase() + state.reportStatus.slice(1)}
          </span>
        </div> : null}

        {identityLoaded ? <ProgressSummaryCard /> : null}

        {identityLoaded ? <GlassCard className="divide-y divide-line/70 p-5">
          {reportSections.map((section) => {
            const Icon = section.icon;
            return (
              <div key={section.title} className="flex gap-4 py-4 first:pt-0 last:pb-0">
                <span className={`grid h-12 w-12 shrink-0 place-items-center rounded-full ${section.tone}`}>
                  <Icon size={23} aria-hidden="true" />
                </span>
                <div>
                  <h3 className="text-lg font-bold text-ink">{section.title}</h3>
                  <ul className="mt-2 space-y-1 text-sm text-slate-700">
                    {section.items.map((item) => <li key={item}>• {item}</li>)}
                  </ul>
                </div>
              </div>
            );
          })}
        </GlassCard> : null}

        <GlassCard className="p-5 space-y-4">
          <h2 className="text-lg font-bold text-ink">Report inputs</h2>
          <div>
            <label className="block text-sm font-semibold text-ink" htmlFor="therapist-notes">Therapist notes</label>
            <textarea id="therapist-notes" aria-label="Therapist notes" className="mt-2 min-h-24 w-full rounded-xl border border-line bg-white/70 p-3 outline-none focus:ring-2 focus:ring-clinical text-sm" value={therapistNotes} readOnly={isEditorLocked} onChange={(event) => {
              if (isEditorLocked) return;
              setTherapistNotes(event.target.value);
              persist({ ...state, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
            }} />
          </div>
          <div>
            <label className="mt-2 block text-sm font-semibold text-ink" htmlFor="therapy-goals">Therapy goals</label>
            <textarea id="therapy-goals" aria-label="Therapy goals" className="mt-2 min-h-24 w-full rounded-xl border border-line bg-white/70 p-3 outline-none focus:ring-2 focus:ring-clinical text-sm" value={goalsText} readOnly={isEditorLocked} onChange={(event) => {
              if (isEditorLocked) return;
              setGoalsText(event.target.value);
              persist({ ...state, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
            }} />
          </div>
        </GlassCard>

        <GlassCard className="p-5 space-y-4">
          <h2 className="text-lg font-bold text-ink">Report Assistant Settings</h2>
          <div>
            <label className="block text-sm font-semibold text-ink" htmlFor="provider-selector">Drafting Provider</label>
            <select
              id="provider-selector"
              className="mt-2 w-full rounded-xl border border-line bg-white/70 p-3 text-sm font-medium focus:ring-2 focus:ring-clinical outline-none"
              value={providerId}
              disabled={isFinalized}
              onChange={(e) => setProviderId(e.target.value)}
            >
              <option value="template">Deterministic Template Provider</option>
              <option value="local_llm">Local LLM Provider (Llama 3)</option>
            </select>
          </div>
          {providerId === "local_llm" && (
            <label className="flex items-center gap-3 text-sm cursor-pointer select-none">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-line text-clinical focus:ring-clinical focus:ring-offset-0"
                checked={allowFallback}
                disabled={isFinalized}
                onChange={(e) => setAllowFallback(e.target.checked)}
              />
              <span className="text-slate-700 font-medium">
                Allow safe template fallback if LLM fails
              </span>
            </label>
          )}
        </GlassCard>

        {!isFinalized && !isFailedSafety && (
          <GlassCard className="p-5 space-y-4 animate-fade-in border border-[#efeaff]">
            <h2 className="text-lg font-bold text-ink">Sign-off Confirmation</h2>
            <div className="rounded-2xl border border-line bg-white/70 p-4">
              <p className="text-sm font-semibold text-ink">Primary assigned therapist</p>
              <p className="mt-2 text-sm text-slate-700">{primaryTherapistLabel}</p>
              <p className="mt-2 text-xs leading-5 text-slate-600">
                Report sign-off uses the authenticated therapist identity from the active session. The client does not choose or override the signer.
              </p>
            </div>
            {!primaryTherapistAssigned ? (
              <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900">
                Assign a primary therapist before finalizing this report.
              </p>
            ) : null}
            <label className="flex items-start gap-3 text-sm cursor-pointer select-none">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-line text-clinical focus:ring-clinical focus:ring-offset-0 shrink-0"
                checked={confirmationChecked}
                onChange={(e) => setConfirmationChecked(e.target.checked)}
              />
              <span className="text-slate-700 font-medium">
                I check and confirm that this report does not contain diagnostic assertions, and is for clinical decision-support only.
              </span>
            </label>
          </GlassCard>
        )}

        <GlassCard className="p-5">
          <h2 className="text-lg font-bold text-ink">Share with caregiver</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Local/demo status only. This does not send a message, create a production delivery channel, or claim secure caregiver sharing.
          </p>
          <p className="mt-2 font-bold text-clinical">{state.shareStatus}</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-line bg-white/70 px-3 font-semibold" disabled={!identityLoaded || isStale} onClick={handleCopyLocalDemoShareLink}>
              <Clipboard size={17} aria-hidden="true" /> Copy local demo share link
            </button>
            <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-line bg-white/70 px-3 font-semibold" disabled={!identityLoaded || isStale} onClick={handleMarkSent}>
              <Send size={17} aria-hidden="true" /> Mark caregiver share recorded
            </button>
          </div>
        </GlassCard>

        <GradientButton
          icon={ShieldCheck}
          className="w-full text-xl"
          onClick={handleFinalize}
          disabled={isFinalizeDisabled}
          data-testid="finalize-report-button"
        >
          {isFinalized ? "Report Finalized" : backendUnavailable ? "Finalize Report (Online only)" : "Finalize Report"}
        </GradientButton>
        {state.finalizeStatus ? <p className="demo-note rounded-2xl p-3 text-sm">{state.finalizeStatus}</p> : null}
        <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
        <SafetyNote>Decision-support only. Not diagnostic. Final report text must be reviewed by the therapist.</SafetyNote>
      </div>

      <GlassCard className="p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-ink">Draft report preview</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              This draft is editable and remains decision-support until therapist finalization.
            </p>
          </div>
          <button
            className="rounded-2xl border border-line bg-white/70 px-4 py-2 text-sm font-bold text-clinical disabled:opacity-50"
            onClick={() => handleGenerateDraft(false)}
            disabled={busy || isFinalized || !transcriptUnlocked}
            data-testid="generate-report-draft-button"
          >
            {busy ? "Working" : "Generate draft"}
          </button>
        </div>
        {!transcriptUnlocked ? (
          <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900">
            Transcript review and attestation are required before report generation.
          </p>
        ) : null}

        {/* Failed Safety Warning Banner */}
        {isFailedSafety && (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-5 text-red-950 animate-fade-in" data-testid="report-safety-failed">
            <h3 className="text-lg font-bold text-red-900">Safety Validation Failed</h3>
            <p className="mt-1 text-sm text-red-800">
              The drafted report contains prohibited diagnostic wording or fails required safety disclaimers. 
              The draft has been locked from editing and finalization for clinical safety.
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              {backendReport?.safety_validation_result?.issues.map((issue: any) => (
                <li key={issue.issue_id} className="flex items-start gap-2 bg-white/50 p-3 rounded-xl border border-red-100">
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
              className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-clinical px-5 font-bold text-white shadow-md hover:bg-clinical/90 active:scale-95 transition-transform"
              data-testid="regenerate-safe-template-button"
            >
              Regenerate using Safe Template
            </button>
          </div>
        )}

        {/* Non-blocking Safety Warnings (Yellow Alert) */}
        {!isFailedSafety && backendReport?.safety_validation_result?.issues && backendReport.safety_validation_result.issues.length > 0 && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-950 animate-fade-in" data-testid="report-safety-warning">
            <h3 className="text-lg font-bold text-amber-900">Clinical Safety Warnings</h3>
            <p className="mt-1 text-sm text-amber-800">
              Please address the following safety rules in your draft. Finalization is blocked until they are resolved.
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              {backendReport.safety_validation_result.issues.map((issue: any) => (
                <li key={issue.issue_id} className="flex items-start gap-2 bg-white/50 p-3 rounded-xl border border-amber-100">
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

        <textarea className="mt-5 min-h-80 w-full rounded-2xl border border-line bg-white/70 p-4 text-sm leading-6 text-ink outline-none focus:ring-2 focus:ring-clinical" value={reportText} readOnly={isEditorLocked} onChange={(event) => {
          if (isEditorLocked) return;
          setReportText(event.target.value);
          persist({ ...state, reportMarkdown: event.target.value, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
        }} aria-label={isStale ? "Stale read-only report" : isFinalized ? "Finalized report" : "Editable draft report preview"} aria-describedby={isStale ? "stale-report-explanation" : undefined} data-testid="report-preview" />
        <p className="mt-2 text-sm font-semibold text-slate-600" role="status">
          {state.reportSaveStatus === "saving" ? "Saving..." : state.reportSaveStatus === "saved" ? "Saved" : state.reportSaveStatus === "failed" ? "Failed to save" : state.reportSaveStatus === "unsaved" ? "Unsaved changes" : "Not saved"}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-xl border border-clinical bg-white/70 px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50"
            onClick={handleSaveDraft}
            disabled={busy || isEditorLocked || !state.reportId || state.reportSaveStatus === "saved"}
            data-testid="save-report-draft-button"
          >
            Save draft
          </button>
          <button className="inline-flex items-center gap-2 rounded-xl border border-line bg-white/70 px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50" disabled={!isFinalized} onClick={() => void handleExport("markdown")}><Download size={18} aria-hidden="true" />Export Markdown</button>
          <button className="inline-flex items-center gap-2 rounded-xl border border-line bg-white/70 px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50" disabled={!isFinalized} onClick={() => void handleExport("html")}><Download size={18} aria-hidden="true" />Export HTML</button>
          <button className="inline-flex items-center gap-2 rounded-xl border border-line bg-white/70 px-4 py-3 text-sm font-bold text-slate-500 disabled:opacity-60" disabled>Export PDF later</button>
          <button className="inline-flex items-center gap-2 rounded-xl border border-line bg-white/70 px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50" onClick={handleExportCha} disabled={!state.transcriptAttested || state.transcriptReviewStatus !== "reviewed"}><Download size={18} aria-hidden="true" />Export reviewed .cha</button>
        </div>
        {exportedCha ? <textarea className="mt-4 h-40 w-full rounded-2xl border border-line bg-white/70 p-3 font-mono text-xs" readOnly value={exportedCha} aria-label="Exported reviewed CHA" /> : null}
      </GlassCard>
      </div>
    </>
  );
}

function downloadTextFile(text: string, filename: string, contentType = "text/plain") {
  if (typeof document === "undefined" || typeof URL.createObjectURL !== "function") return;
  const url = URL.createObjectURL(new Blob([text], { type: `${contentType};charset=utf-8` }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function WorkflowStatus({ state, backendUnavailable }: { state: WorkflowState; backendUnavailable?: boolean }) {
  if (!state.statusMessage && !state.error) {
    return null;
  }
  const isError = Boolean(state.error);
  const isSuccess = Boolean(state.statusMessage && !isError);
  if (isSuccess && backendUnavailable) {
    return null;
  }
  const className = isError
    ? "rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-950 animate-fade-in"
    : isSuccess
      ? "rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 animate-fade-in"
      : "demo-note rounded-2xl p-4 text-sm";
  return (
    <div className={className} role={isError ? "alert" : "status"} aria-live="polite">
      {state.statusMessage ? <p className="font-semibold">{state.statusMessage}</p> : null}
      {state.error ? <p className="mt-1 font-semibold">{state.error}</p> : null}
    </div>
  );
}

function createDraftText(state: WorkflowState) {
  return [
    "# Draft Report Preview",
    "",
    `Child/session: ${state.childName}`,
    `Report period: ${state.reportPeriod}`,
    `Transcript readiness: ${state.transcriptCompleteness || 0}%`,
    `Reviewed transcript status: ${state.transcriptReviewStatus}`,
    `Review-needed count: ${state.reviewNeededCount}`,
    "",
    "## Strengths",
    ...(state.featureSummary.length ? state.featureSummary.map((item) => `- ${item.label}: ${item.value}`) : ["- Feature summary pending therapist review"]),
    "",
    "## Therapist Notes",
    state.therapistNotes || "- No therapist notes recorded.",
    "",
    "## Therapy Goals",
    ...(state.therapyGoals.length ? state.therapyGoals.map((goal) => `- ${goal}`) : ["- No therapy goals recorded."]),
    "",
    "## Needs Support",
    "- Review transcript wording before caregiver sharing",
    "",
    "## Next Steps",
    "- Therapist edits and finalizes this report",
    "",
    "Decision-support only.",
    "Not diagnostic.",
    "Therapist review required."
  ].join("\n");
}

function parseGoals(value: string) {
  return value.split("\n").map((goal) => goal.trim()).filter(Boolean);
}

function mergeReportInputs(markdown: string, therapistNotes: string, therapyGoals: string[]) {
  const withoutInputs = markdown
    .replace(/\n*## Therapist Notes[\s\S]*?(?=\n## |\s*$)/, "")
    .replace(/\n*## Therapy Goals[\s\S]*?(?=\n## |\s*$)/, "")
    .trimEnd();
  return [
    withoutInputs,
    "",
    "## Therapist Notes",
    therapistNotes || "- No therapist notes recorded.",
    "",
    "## Therapy Goals",
    ...(therapyGoals.length ? therapyGoals.map((goal) => `- ${goal}`) : ["- No therapy goals recorded."])
  ].join("\n");
}

function mergeLocalReportInputs(markdown: string, state: WorkflowState) {
  return `${markdown}\n\n## Therapist Notes\n${state.therapistNotes || "- No therapist notes recorded."}\n\n## Therapy Goals\n${state.therapyGoals.length ? state.therapyGoals.map((goal) => `- ${goal}`).join("\n") : "- No therapy goals recorded."}\n\nDecision-support only.\nNot diagnostic.\nTherapist review required.`;
}

function markdownToHtml(markdown: string) {
  const escaped = markdown.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  return escaped.split("\n").map((line) => {
    if (line.startsWith("# ")) return `<h1>${line.slice(2)}</h1>`;
    if (line.startsWith("## ")) return `<h2>${line.slice(3)}</h2>`;
    if (line.startsWith("- ")) return `<p>${line}</p>`;
    return line ? `<p>${line}</p>` : "";
  }).join("\n");
}
