"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Clipboard, Download, Heart, Send, ShieldCheck, Star } from "lucide-react";

import { GlassCard, GradientButton, ProgressSummaryCard, SafetyNote } from "@/components/liquid-ui";
import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import {
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

export function ReportSummaryClient({ caseId, sessionId, transcriptId, reportId }: {
  caseId?: string;
  sessionId?: string;
  transcriptId?: string;
  reportId?: string;
}) {
  const [state, setState] = useState<WorkflowState>(() => createInitialWorkflowState());
  const [busy, setBusy] = useState(false);
  const [reportText, setReportText] = useState("");
  const [therapistNotes, setTherapistNotes] = useState("");
  const [goalsText, setGoalsText] = useState("");
  const [exportedCha, setExportedCha] = useState("");
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const transcriptUnlocked = state.transcriptAttested && state.transcriptReviewStatus === "reviewed";

  useEffect(() => {
    let cancelled = false;
    const stored = loadWorkflowState();
    if (!reportId && !sessionId) {
      setState(stored);
      setReportText(stored.reportMarkdown ?? createDraftText(stored));
      setTherapistNotes(stored.therapistNotes);
      setGoalsText(stored.therapyGoals.join("\n"));
      return;
    }
    setState({
      ...stored,
      reportMarkdown: "",
      reportStatus: "Not started",
      reportSaveStatus: "idle",
      workflowLoading: true,
      statusMessage: "Loading persisted report...",
      error: undefined
    });
    void (async () => {
      try {
        const session = sessionId ? await getBackendSession(sessionId) : undefined;
        const resolvedReportId = reportId ?? session?.report_id;
        if (!resolvedReportId) throw new Error("Report not found.");
        const report = await getBackendReport(resolvedReportId);
        const resolvedTranscriptId = transcriptId ?? session?.transcript_id;
        const transcript = resolvedTranscriptId ? await getBackendTranscript(resolvedTranscriptId) : undefined;
        const resolvedCaseId = caseId ?? report.case_id ?? session?.case_id;
        const childCase = resolvedCaseId ? await getBackendCase(resolvedCaseId) : undefined;
        const finalized = report.status === "Signed Off";
        const hydrated = saveWorkflowState({
          ...stored,
          caseId: resolvedCaseId,
          caseInfo: {
            caseId: resolvedCaseId,
            clientLabel: childCase?.nickname ?? childCase?.child_code ?? stored.caseInfo.clientLabel
          },
          childName: childCase?.nickname ?? childCase?.child_code ?? stored.childName,
          backendSessionId: report.session_id ?? session?.session_id,
          backendTranscriptSessionId: transcript?.session_id ?? report.session_id ?? session?.session_id,
          backendTranscriptId: transcript?.transcript_id,
          transcriptAttested: Boolean(transcript?.therapist_attested),
          transcriptReviewStatus: transcript?.therapist_attested ? "reviewed" : "in_review",
          backendReportId: resolvedReportId,
          reportId: resolvedReportId,
          reportMarkdown: report.markdown ?? "",
          reportStatus: finalized ? "Finalized" : "Draft",
          reportSaveStatus: "saved",
          workflowLoading: false,
          finalizeStatus: finalized ? "Report finalized." : undefined,
          statusMessage: finalized ? "Finalized report loaded." : "Report draft loaded.",
          error: undefined
        });
        if (cancelled) return;
        setState(hydrated);
        setReportText(hydrated.reportMarkdown ?? "");
        setTherapistNotes(hydrated.therapistNotes);
        setGoalsText(hydrated.therapyGoals.join("\n"));
      } catch {
        if (cancelled) return;
        setBackendUnavailable(true);
        setState({ ...stored, workflowLoading: false, statusMessage: "Backend unavailable.", error: "Could not load the persisted report." });
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

  function persist(next: WorkflowState) {
    const saved = saveWorkflowState(next);
    setState(saved);
    return saved;
  }

  async function handleGenerateDraft() {
    if (state.reportStatus === "Finalized" || !transcriptUnlocked) return;
    setBusy(true);
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
      const report = await generateBackendReport(targetSession);
      if (!report.report_id) throw new Error("Report ID missing.");
      const markdown = report.content_markdown ?? report.markdown ?? "";
      setReportText(markdown);
      persist({
        ...reportingState,
        backendReportId: report.report_id,
        reportId: report.report_id,
        reportMarkdown: markdown,
        reportStatus: "Draft",
        reportSaveStatus: "saved",
        statusMessage: "Draft report preview generated. Therapist edits are required before finalization.",
        error: undefined
      });
    } catch {
      setBackendUnavailable(true);
      persist({ ...reportingState, reportSaveStatus: "failed", statusMessage: "Report generation failed.", error: "Backend unavailable. No report draft was created." });
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveDraft() {
    if (!state.reportId || state.reportStatus === "Finalized") return;
    setBusy(true);
    const saving = persist({ ...state, reportSaveStatus: "saving", statusMessage: "Saving report draft...", error: undefined });
    try {
      const markdown = mergeReportInputs(reportText, therapistNotes, parseGoals(goalsText));
      const report = await updateBackendReport(state.reportId, markdown, therapistNotes);
      setReportText(report.markdown ?? markdown);
      persist({
        ...saving,
        reportMarkdown: report.markdown ?? markdown,
        therapistNotes,
        therapyGoals: parseGoals(goalsText),
        reportStatus: "Reviewed",
        reportSaveStatus: "saved",
        statusMessage: "Report draft saved.",
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
    if (!state.reportId || state.reportStatus !== "Finalized") return;
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

  async function handleCopySecureLink() {
    const localLink = `https://secure.local/reports/${state.reportId ?? state.sessionId ?? "draft"}`;
    await navigator.clipboard?.writeText(localLink);
    persist({
      ...state,
      reportMarkdown: reportText,
      shareStatus: "Secure link copied",
      statusMessage: "Local secure-link status recorded. No public sharing endpoint was created."
    });
  }

  function handleMarkSent() {
    persist({ ...state, reportMarkdown: reportText, shareStatus: "Sent to caregiver", statusMessage: "Caregiver delivery status recorded locally." });
  }

  async function handleFinalize() {
    if (state.reportStatus === "Finalized" || !state.reportId || state.reportSaveStatus !== "saved") return;
    setBusy(true);
    try {
      const finalized = await finalizeBackendReport(state.reportId);
      const markdown = finalized.markdown ?? reportText;
      setReportText(markdown);
      persist({
        ...state,
        reportStatus: "Finalized",
        reportMarkdown: markdown,
        reportSaveStatus: "saved",
        finalizeStatus: "Report finalized.",
        statusMessage: "Report finalized.",
        error: undefined
      });
    } catch {
      setBackendUnavailable(true);
      persist({ ...state, statusMessage: "Report finalization failed.", error: "Backend unavailable. The report remains an editable draft." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <div className="grid gap-6 lg:grid-cols-[430px_1fr]">
      <div className="space-y-5">
        <header>
          <h1 className="text-3xl font-bold text-ink">Report Summary</h1>
        </header>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-14 w-14 place-items-center rounded-full bg-gradient-to-br from-orange-100 to-sky-100 text-xl">EL</span>
            <div>
              <h2 className="text-xl font-bold text-ink">{state.childName}</h2>
              <p className="text-slate-600">{state.reportPeriod}</p>
            </div>
          </div>
          <span className="rounded-full bg-[#efeaff] px-5 py-2 font-bold text-clinical">{state.reportStatus === "Not started" ? "Draft" : state.reportStatus}</span>
        </div>

        <ProgressSummaryCard />

        <GlassCard className="divide-y divide-line/70 p-5">
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
        </GlassCard>

        <GlassCard className="p-5">
          <h2 className="text-lg font-bold text-ink">Report inputs</h2>
          <label className="mt-4 block text-sm font-semibold text-ink" htmlFor="therapist-notes">Therapist notes</label>
          <textarea id="therapist-notes" aria-label="Therapist notes" className="mt-2 min-h-24 w-full rounded-xl border border-line bg-white/70 p-3" value={therapistNotes} readOnly={state.reportStatus === "Finalized"} onChange={(event) => {
            setTherapistNotes(event.target.value);
            persist({ ...state, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
          }} />
          <label className="mt-4 block text-sm font-semibold text-ink" htmlFor="therapy-goals">Therapy goals</label>
          <textarea id="therapy-goals" aria-label="Therapy goals" className="mt-2 min-h-24 w-full rounded-xl border border-line bg-white/70 p-3" value={goalsText} readOnly={state.reportStatus === "Finalized"} onChange={(event) => {
            setGoalsText(event.target.value);
            persist({ ...state, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
          }} />
        </GlassCard>

        <GlassCard className="p-5">
          <h2 className="text-lg font-bold text-ink">Share status</h2>
          <p className="mt-2 font-bold text-clinical">{state.shareStatus}</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-line bg-white/70 px-3 font-semibold" onClick={handleCopySecureLink}>
              <Clipboard size={17} aria-hidden="true" /> Copy secure link
            </button>
            <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-line bg-white/70 px-3 font-semibold" onClick={handleMarkSent}>
              <Send size={17} aria-hidden="true" /> Mark sent to caregiver
            </button>
          </div>
        </GlassCard>

        <GradientButton
          icon={ShieldCheck}
          className="w-full text-xl"
          onClick={handleFinalize}
          disabled={busy || state.reportStatus === "Not started" || state.reportStatus === "Finalized" || state.reportSaveStatus !== "saved" || backendUnavailable}
        >
          {state.reportStatus === "Finalized" ? "Report Finalized" : backendUnavailable ? "Finalize Report (Online only)" : "Finalize Report"}
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
          <button className="rounded-2xl border border-line bg-white/70 px-4 py-2 text-sm font-bold text-clinical disabled:opacity-50" onClick={handleGenerateDraft} disabled={busy || state.reportStatus === "Finalized" || !transcriptUnlocked}>
            {busy ? "Working" : "Generate draft"}
          </button>
        </div>
        {!transcriptUnlocked ? (
          <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900">
            Transcript review and attestation are required before report generation.
          </p>
        ) : null}
        <textarea className="mt-5 min-h-80 w-full rounded-2xl border border-line bg-white/70 p-4 text-sm leading-6 text-ink outline-none focus:ring-2 focus:ring-clinical" value={reportText} readOnly={state.reportStatus === "Finalized"} onChange={(event) => {
          setReportText(event.target.value);
          persist({ ...state, reportMarkdown: event.target.value, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
        }} aria-label={state.reportStatus === "Finalized" ? "Finalized report" : "Editable draft report preview"} />
        <p className="mt-2 text-sm font-semibold text-slate-600" role="status">
          {state.reportSaveStatus === "saving" ? "Saving..." : state.reportSaveStatus === "saved" ? "Saved" : state.reportSaveStatus === "failed" ? "Failed to save" : state.reportSaveStatus === "unsaved" ? "Unsaved changes" : "Not saved"}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button className="inline-flex items-center gap-2 rounded-xl border border-clinical bg-white/70 px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50" onClick={handleSaveDraft} disabled={busy || state.reportStatus === "Finalized" || state.reportSaveStatus === "saved"}>Save draft</button>
          <button className="inline-flex items-center gap-2 rounded-xl border border-line bg-white/70 px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50" disabled={state.reportStatus !== "Finalized"} onClick={() => void handleExport("markdown")}><Download size={18} aria-hidden="true" />Export Markdown</button>
          <button className="inline-flex items-center gap-2 rounded-xl border border-line bg-white/70 px-4 py-3 text-sm font-bold text-clinical disabled:opacity-50" disabled={state.reportStatus !== "Finalized"} onClick={() => void handleExport("html")}><Download size={18} aria-hidden="true" />Export HTML</button>
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
