"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  CircleDot,
  ClipboardList,
  Crown,
  Filter,
  FolderOpen,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Users
} from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { SafetyNotice } from "@/components/safety-notice";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { casesAdapter } from "@/features/cases/services/cases-adapter";
import { useMockAccessSession } from "@/lib/use-mock-access-session";
import {
  assignCaseCareTeamMember,
  getBackendCaseTimeline,
  listCaseCareTeamAssignments,
  listBackendCaseGoals,
  listOrganizationMemberships,
  updateBackendCase,
  withdrawBackendCaseConsent,
  type CareTeamAssignment,
  type BackendCase,
  type BackendGoal,
  type BackendTimelineEvent,
  type OrganizationMembership
} from "@/lib/workflow";
import { useRemoteResource } from "@/services/adapters/use-remote-resource";
import type { RemoteState } from "@/services/adapters/remote-state";
import { PipelineProgressBar } from "@/components/pipeline-progress-bar";
import { Stack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";

type CasesWorkspaceClientProps = {
  caseId?: string;
};

function ageLabel(caseItem: BackendCase) {
  if (caseItem.age_months == null) return "Age not recorded";
  return `${Math.floor(caseItem.age_months / 12)}y ${caseItem.age_months % 12}m`;
}

function caseLabel(caseItem: BackendCase) {
  return caseItem.nickname ?? caseItem.child_code ?? caseItem.display_label ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function codeLabel(caseItem: BackendCase) {
  return caseItem.child_code ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function languageLabel(caseItem: BackendCase) {
  return caseItem.language ?? "Language not recorded";
}

function clinicianLabel(userId: string) {
  if (userId === "therapist-demo") return "Demo Therapist";
  return userId
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function primaryClinician(caseItem: BackendCase) {
  if (caseItem.primary_therapist_user_id) return clinicianLabel(caseItem.primary_therapist_user_id);
  const assigned = caseItem.care_team_user_ids ?? [];
  return assigned.length ? clinicianLabel(assigned[0]) : "Not assigned";
}

function clinicianList(caseItem: BackendCase) {
  const assigned = caseItem.care_team_user_ids ?? [];
  return assigned.length ? assigned.map(clinicianLabel).join(", ") : "No clinician assigned";
}

function childInitials(caseItem: BackendCase) {
  const label = caseLabel(caseItem);
  const words = label.split(/\s+/).filter(Boolean);
  return words.slice(0, 2).map((word) => word[0]?.toUpperCase() ?? "").join("") || codeLabel(caseItem).slice(-2);
}

function consentLabel(value?: string) {
  if (!value) return "Unknown";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function workflowStage(caseItem: BackendCase) {
  if (caseItem.consent_status && caseItem.consent_status !== "granted") return "Consent follow-up";
  if (caseItem.latest_session_status === "Needs Review") return "Transcript review";
  if (caseItem.latest_report_status === "Ready") return "Report sign-off";
  if (caseItem.latest_session_status === "Attested") return "Report drafting";
  if (caseItem.latest_session_date) return "Session in progress";
  return "Intake ready";
}

function nextAction(caseItem: BackendCase) {
  if (caseItem.consent_status && caseItem.consent_status !== "granted") {
    return { label: "Review consent", href: `/cases/${caseItem.case_id}` };
  }
  if (caseItem.latest_session_status === "Needs Review") {
    return { label: "Review session", href: `/cases/${caseItem.case_id}` };
  }
  if (caseItem.latest_report_status === "Ready") {
    return { label: "Finalize report", href: `/cases/${caseItem.case_id}` };
  }
  if (caseItem.latest_session_date) {
    return { label: "Continue workflow", href: `/cases/${caseItem.case_id}` };
  }
  return { label: "Start session", href: `/record?case_id=${caseItem.case_id}` };
}

function progressSnapshot(caseItem: BackendCase) {
  return [
    {
      label: "Workflow stage",
      value: workflowStage(caseItem),
      helper: caseItem.latest_session_status ?? "Draft"
    },
    {
      label: "Latest session",
      value: caseItem.latest_session_date ?? "Not started",
      helper: caseItem.latest_session_status ?? "Draft"
    },
    {
      label: "Report status",
      value: caseItem.latest_report_status ?? "Draft",
      helper: "Therapist review and sign-off remain required."
    }
  ];
}

function buildUpcomingTasks(caseItem: BackendCase, timeline: BackendTimelineEvent[], goals: BackendGoal[], consent: string) {
  const tasks: string[] = [];
  if (consent && consent.toLowerCase() !== "granted") {
    tasks.push("Confirm consent status before creating or reopening sessions.");
  }
  if (timeline.some((event) => event.status === "Needs Review")) {
    tasks.push("Review the latest session transcript before downstream workflow steps.");
  }
  if (goals.length === 0) {
    tasks.push("Add communication goals when the care plan is ready.");
  }
  if (!tasks.length) {
    tasks.push("Open the latest session workspace and confirm the next therapist-reviewed step.");
  }
  return tasks;
}

type CasesResource =
  | { kind: "list"; cases: BackendCase[] }
  | {
      kind: "detail";
      caseItem: BackendCase;
      timeline: BackendTimelineEvent[];
      goals: BackendGoal[];
    };

const emptyCases: BackendCase[] = [];

async function loadCasesResource(identity: string, signal: AbortSignal): Promise<CasesResource> {
  if (identity === "cases:list") {
    return { kind: "list", cases: await casesAdapter.list(signal) };
  }

  const caseId = identity.slice("cases:detail:".length);
  const [caseItem, timeline, goals] = await Promise.all([
    casesAdapter.get(caseId, signal),
    getBackendCaseTimeline(caseId, { signal }),
    listBackendCaseGoals(caseId, { signal }),
  ]);
  return { kind: "detail", caseItem, timeline, goals };
}

export function CasesWorkspaceClient({ caseId }: CasesWorkspaceClientProps) {
  const resource = useRemoteResource(
    caseId ? `cases:detail:${caseId}` : "cases:list",
    loadCasesResource,
  );
  const casesState: RemoteState<CasesResource> =
    resource.status === "error" && !caseId
      ? { status: "unavailable", mode: "unavailable", reason: "Cases service request failed" }
      : resource.status === "success"
          && resource.data.kind === "list"
          && resource.data.cases.length === 0
        ? { status: "empty", mode: "backend" }
        : resource;
  const data = resource.status === "success" || resource.status === "stale"
    ? resource.data
    : undefined;
  const cases = data?.kind === "list" ? data.cases : emptyCases;
  const currentCase = data?.kind === "detail" ? data.caseItem : null;
  const timeline = data?.kind === "detail" ? data.timeline : [];
  const goals = data?.kind === "detail" ? data.goals : [];
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [clinicianFilter, setClinicianFilter] = useState("all");

  const stageOptions = useMemo(() => {
    const statuses = Array.from(new Set(cases.map((item) => item.latest_session_status ?? "Draft")));
    return ["all", ...statuses];
  }, [cases]);

  const clinicianOptions = useMemo(() => {
    return Array.from(new Set(cases.flatMap((item) => item.care_team_user_ids ?? [])));
  }, [cases]);

  const filteredCases = useMemo(() => {
    return cases.filter((caseItem) => {
      const matchesSearch = !query || [
        caseLabel(caseItem),
        codeLabel(caseItem),
        languageLabel(caseItem),
        clinicianList(caseItem)
      ].join(" ").toLowerCase().includes(query.toLowerCase());
      const matchesStatus = statusFilter === "all" || (caseItem.latest_session_status ?? "Draft") === statusFilter;
      const matchesClinician = clinicianFilter === "all" || (caseItem.care_team_user_ids ?? []).includes(clinicianFilter);
      return matchesSearch && matchesStatus && matchesClinician;
    });
  }, [cases, clinicianFilter, query, statusFilter]);

  const caseStats = useMemo(() => {
    const pendingConsent = cases.filter((item) => item.consent_status && item.consent_status !== "granted").length;
    const reviewQueue = cases.filter((item) => item.latest_session_status === "Needs Review").length;
    const readyReports = cases.filter((item) => item.latest_report_status === "Ready").length;
    return {
      total: cases.length,
      pendingConsent,
      reviewQueue,
      readyReports
    };
  }, [cases]);

  const recentActivity = useMemo(() => {
    return [...cases]
      .filter((item) => item.latest_session_date)
      .sort((a, b) => (b.latest_session_date ?? "").localeCompare(a.latest_session_date ?? ""))
      .slice(0, 4);
  }, [cases]);

  if (casesState.status === "loading" || casesState.status === "idle") {
    return <CaseListSkeleton />;
  }

  if (casesState.status === "unavailable") {
    return (
      <section className="workspace-panel p-5" role="alert">
        <h1 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Cases are unavailable</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          The backend cases service could not be reached. Try again when the service is available.
        </p>
      </section>
    );
  }

  if (casesState.status === "error") {
    return (
      <section className="workspace-panel p-5" role="alert">
        <h1 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Case could not be loaded</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          The requested backend case was not returned. Check the case link or try again.
        </p>
      </section>
    );
  }

  if (caseId && currentCase) {
    return (
      <CaseDetailContent key={currentCase.case_id} caseItem={currentCase} timeline={timeline} goals={goals} />
    );
  }

  return (
    <>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_var(--rail-width)]">
        <div className="space-y-6">
          <PageHeader
            title="Cases"
            description="Track case workflow progress, consent state, and the next therapist-reviewed action without leaving the current workspace."
            meta={[
              "Backend-backed cases",
              "Decision-support only"
            ]}
          />

          <section className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="flex-1">
                <label htmlFor="case-search" className="mb-2 block text-sm font-medium text-[color:var(--color-text-strong)]">
                  Search cases
                </label>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[color:var(--color-text-subtle)]" size={18} aria-hidden="true" />
                  <input
                    id="case-search"
                    type="search"
                    role="searchbox"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search by child label, case code, language, or clinician"
                    className="min-h-11 w-full rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-white pl-10 pr-4 text-sm text-[color:var(--color-text-strong)] outline-none transition focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
                  />
                </div>
              </div>

              {clinicianOptions.length ? (
                <div className="w-full lg:max-w-[16rem]">
                  <label htmlFor="clinician-filter" className="mb-2 block text-sm font-medium text-[color:var(--color-text-strong)]">
                    Clinician filter
                  </label>
                  <select
                    id="clinician-filter"
                    aria-label="Clinician filter"
                    value={clinicianFilter}
                    onChange={(event) => setClinicianFilter(event.target.value)}
                    className="min-h-11 w-full rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-white px-4 text-sm text-[color:var(--color-text-strong)] outline-none transition focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
                  >
                    <option value="all">All clinicians</option>
                    {clinicianOptions.map((userId) => (
                      <option key={userId} value={userId}>
                        {clinicianLabel(userId)}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}
            </div>

            <div className="mt-4 flex flex-wrap gap-2" aria-label="Status filters">
              {stageOptions.map((option) => {
                const active = statusFilter === option;
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setStatusFilter(option)}
                    className={`inline-flex min-h-11 items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] ${
                      active
                        ? "border-[color:var(--color-accent-strong)] bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]"
                        : "border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]"
                    }`}
                    aria-pressed={active}
                  >
                    <Filter size={16} aria-hidden="true" />
                    {option === "all" ? "All statuses" : option}
                  </button>
                );
              })}
            </div>
          </section>

          {filteredCases.length ? (
            <>
              <div className="hidden lg:block">
                <DataTable
                  caption="Cases workspace"
                  columns={[
                    { key: "case", header: "Case" },
                    { key: "workflow", header: "Workflow stage" },
                    { key: "status", header: "Status badge" },
                    { key: "clinician", header: "Clinician" },
                    { key: "nextAction", header: "Next action" }
                  ]}
                  rows={filteredCases.map((caseItem) => {
                    const action = nextAction(caseItem);
                    return {
                      id: caseItem.case_id,
                      case: (
                        <div className="space-y-1">
                          <Link href={`/cases/${caseItem.case_id}`} className="font-semibold text-[color:var(--color-text-strong)] hover:text-[color:var(--color-accent-strong)]">
                            {caseLabel(caseItem)}
                          </Link>
                          <p className="text-xs text-[color:var(--color-text-muted)]">
                            {codeLabel(caseItem)} · {ageLabel(caseItem)} · {languageLabel(caseItem)}
                          </p>
                        </div>
                      ),
                      workflow: (
                        <div className="space-y-1">
                          <p className="font-medium">{workflowStage(caseItem)}</p>
                          <p className="text-xs text-[color:var(--color-text-muted)]">
                            {caseItem.latest_session_date ?? "No session date yet"}
                          </p>
                        </div>
                      ),
                      status: <StatusBadge status={caseItem.latest_session_status ?? "Draft"} />,
                      clinician: (
                        <div className="space-y-1">
                          <p className="font-medium">{primaryClinician(caseItem)}</p>
                          <p className="text-xs text-[color:var(--color-text-muted)]">{consentLabel(caseItem.consent_status)} consent</p>
                        </div>
                      ),
                      nextAction: (
                        <Link
                          href={action.href}
                          className="inline-flex min-h-11 items-center gap-2 rounded-full border border-[color:var(--color-border)] px-4 py-2 font-medium text-[color:var(--color-text-strong)] transition hover:border-[color:var(--color-accent-strong)] hover:bg-[color:var(--color-accent-soft)]"
                        >
                          {action.label}
                          <ArrowRight size={16} aria-hidden="true" />
                        </Link>
                      )
                    };
                  })}
                />
              </div>

              <div className="space-y-3 lg:hidden">
                {filteredCases.map((caseItem) => {
                  const action = nextAction(caseItem);
                  return (
                    <section key={caseItem.case_id} className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft">
                      <div className="flex items-start gap-3">
                        <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[color:var(--color-accent-soft)] font-semibold text-[color:var(--color-accent-strong)]">
                          {childInitials(caseItem)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <Link href={`/cases/${caseItem.case_id}`} className="font-semibold text-[color:var(--color-text-strong)]">
                            {caseLabel(caseItem)}
                          </Link>
                          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
                            {workflowStage(caseItem)} · {primaryClinician(caseItem)}
                          </p>
                        </div>
                        <StatusBadge status={caseItem.latest_session_status ?? "Draft"} />
                      </div>
                      <div className="mt-4">
                        <ActionButton href={action.href} tone="secondary" className="w-full">
                          {action.label}
                        </ActionButton>
                      </div>
                    </section>
                  );
                })}
              </div>
            </>
          ) : (
            <EmptyState
              title="No cases yet"
              description="Create or open a case from the backend workspace to view session progress here."
              action={<ActionButton href="/record">Open session workspace</ActionButton>}
            />
          )}

          <footer className="flex items-center justify-between rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-3 text-sm text-[color:var(--color-text-muted)] shadow-soft">
            <p>
              Showing {filteredCases.length ? `1-${filteredCases.length}` : "0-0"} of {cases.length} cases
            </p>
            <p>Filter results update in place and keep backend workflow state unchanged.</p>
          </footer>

          <SafetyNotice>
            Decision-support only. Use this workspace to organize therapist-reviewed workflow, not to infer diagnosis or secure-sharing status.
          </SafetyNotice>
        </div>

        <aside className="space-y-4">
          <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
            <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">Case overview stats</h2>
            <div className="mt-4 grid gap-3">
              <StatCard label="Open cases" value={String(caseStats.total)} icon={FolderOpen} />
              <StatCard label="Needs review" value={String(caseStats.reviewQueue)} icon={ClipboardList} tone="warning" />
              <StatCard label="Consent follow-up" value={String(caseStats.pendingConsent)} icon={ShieldCheck} />
              <StatCard label="Reports ready" value={String(caseStats.readyReports)} icon={CheckCircle2} tone="success" />
            </div>
          </section>

          <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
            <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">Workflow at a glance</h2>
            <div className="mt-4 space-y-3">
              {stageOptions.slice(1, 5).map((stage) => (
                <div key={stage} className="flex items-center justify-between rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-3">
                  <span className="text-sm font-medium text-[color:var(--color-text-strong)]">{stage}</span>
                  <span className="text-sm text-[color:var(--color-text-muted)]">
                    {cases.filter((item) => workflowStage(item) === stage).length} case(s)
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
            <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">Recent activity</h2>
            <div className="mt-4 space-y-3">
              {recentActivity.length ? recentActivity.map((item) => (
                <div key={item.case_id} className="rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] px-4 py-3">
                  <p className="font-medium text-[color:var(--color-text-strong)]">{caseLabel(item)}</p>
                  <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
                    {item.latest_session_date} · {workflowStage(item)}
                  </p>
                </div>
              )) : (
                <p className="text-sm leading-6 text-[color:var(--color-text-muted)]">No recent case activity yet.</p>
              )}
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}

function CaseListSkeleton() {
  return (
    <section className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft">
      <div className="space-y-3 animate-pulse motion-reduce:animate-none">
        <div className="h-12 rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)]" />
        <div className="h-12 rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)]" />
        <div className="h-12 rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)]" />
      </div>
    </section>
  );
}

function getLocalWorkflowStage(caseItem: BackendCase, consent: string) {
  if (consent && consent.toLowerCase() !== "granted") return "Consent follow-up";
  if (caseItem.latest_session_status === "Needs Review") return "Transcript review";
  if (caseItem.latest_report_status === "Ready") return "Report sign-off";
  if (caseItem.latest_session_status === "Attested") return "Report drafting";
  if (caseItem.latest_session_date) return "Session in progress";
  return "Intake ready";
}

function getProgressSnapshot(caseItem: BackendCase, localWorkflowStage: string) {
  return [
    {
      label: "Workflow stage",
      value: localWorkflowStage,
      helper: caseItem.latest_session_status ?? "Draft"
    },
    {
      label: "Latest session",
      value: caseItem.latest_session_date ?? "Not started",
      helper: caseItem.latest_session_status ?? "Draft"
    },
    {
      label: "Report status",
      value: caseItem.latest_report_status ?? "Draft",
      helper: "Therapist review and sign-off remain required."
    }
  ];
}

function CaseDetailContent({
  caseItem,
  timeline,
  goals
}: {
  caseItem: BackendCase;
  timeline: BackendTimelineEvent[];
  goals: BackendGoal[];
}) {
  const [localConsent, setLocalConsent] = useState(caseItem.consent_status ?? "pending");
  const [consentSigner, setConsentSigner] = useState("Parent");
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentDate, setConsentDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [consentNotes, setConsentNotes] = useState("");
  const [consentBusy, setConsentBusy] = useState(false);
  const [consentMsg, setConsentMsg] = useState("");

  useEffect(() => {
    setLocalConsent(caseItem.consent_status ?? "pending");
  }, [caseItem.consent_status]);

  const isConsentGranted = localConsent.toLowerCase() === "granted";

  async function handleGrantConsent(e: React.FormEvent) {
    e.preventDefault();
    if (!consentChecked) return;
    setConsentBusy(true);
    setConsentMsg("");
    try {
      await updateBackendCase(caseItem.case_id, {
        consent_status: "granted",
        notes: `${caseItem.notes || ""}\nConsent verified on ${consentDate} by ${consentSigner}. Notes: ${consentNotes}`.trim()
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

  const localWorkflowStage = getLocalWorkflowStage(caseItem, localConsent);
  const snapshot = getProgressSnapshot(caseItem, localWorkflowStage);
  const tasks = buildUpcomingTasks(caseItem, timeline, goals, localConsent);

  return (
    <div className="space-y-6">
      <PageHeader
        title={caseLabel(caseItem)}
        description="Use the persisted case record to review workflow progress, referral context, and therapist-owned next steps."
        meta={[
          `Case ${codeLabel(caseItem)}`,
          `${ageLabel(caseItem)}`,
          `${localWorkflowStage}`,
          `${primaryClinician(caseItem)}`
        ]}
        actions={
          <ActionButton
            href={isConsentGranted ? `/record?case_id=${caseItem.case_id}` : "#"}
            disabled={!isConsentGranted}
            className={!isConsentGranted ? "opacity-50 cursor-not-allowed" : ""}
          >
            Create new session
          </ActionButton>
        }
      />

      <PipelineProgressBar currentStatus={localConsent === "granted" ? "ready_for_audio" : "awaiting_consent"} />

      <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="grid h-16 w-16 place-items-center rounded-[1.5rem] bg-[color:var(--color-accent-soft)] text-xl font-semibold text-[color:var(--color-accent-strong)]">
              {childInitials(caseItem)}
            </div>
            <div>
              <h2 className="text-xl font-semibold text-[color:var(--color-text-strong)]">Case profile</h2>
              <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
                {codeLabel(caseItem)} · {languageLabel(caseItem)}
              </p>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <HeaderMeta label="Case status" value={localWorkflowStage} icon={Activity} />
            <HeaderMeta label="Primary therapist" value={primaryClinician(caseItem)} icon={Users} />
            <HeaderMeta label="Consent status" value={consentLabel(localConsent)} icon={ShieldCheck} />
            <HeaderMeta label="Latest session" value={caseItem.latest_session_date ?? "Not started"} icon={CalendarDays} />
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {!isConsentGranted ? (
            <Stack gap={4}>
              <Stack className="rounded-[var(--radius-shell)] border border-amber-200 bg-amber-50 p-5 shadow-soft" gap={3}>
                <Stack direction="horizontal" gap={3} align="start">
                  <CircleDot className="mt-1 h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
                  <Stack gap={1}>
                    <Text as="h3" weight="semibold" className="text-amber-900">
                      Caregiver Consent Verification Required
                    </Text>
                    <Text type="supporting" className="text-amber-800 leading-6">
                      This case requires verified caregiver consent. Session recording, audio processing, and clinical observation workflows are locked until consent is obtained and verified.
                    </Text>
                  </Stack>
                </Stack>
              </Stack>

              <Stack as="section" className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5 shadow-soft" gap={4}>
                <Stack gap={1}>
                  <Text as="h2" weight="semibold" className="text-lg text-[color:var(--color-text-strong)]">
                    Consent Verification Form
                  </Text>
                  <Text type="supporting" className="text-sm text-[color:var(--color-text-muted)]">
                    Please verify consent credentials below to unlock the clinical intake and session workflows.
                  </Text>
                </Stack>

                <form onSubmit={handleGrantConsent} className="space-y-4">
                  <label className="flex items-start gap-3 text-sm text-[color:var(--color-text-strong)] font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 rounded border-[color:var(--color-border)] accent-[color:var(--color-accent-strong)]"
                      checked={consentChecked}
                      onChange={(e) => setConsentChecked(e.target.checked)}
                      disabled={consentBusy}
                      required
                    />
                    <span>I verify that written or verbal caregiver consent has been obtained.</span>
                  </label>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="grid gap-1 text-sm font-medium text-[color:var(--color-text-strong)]">
                      Signer relationship
                      <input
                        type="text"
                        className="min-h-11 w-full rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-white px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
                        value={consentSigner}
                        onChange={(e) => setConsentSigner(e.target.value)}
                        disabled={consentBusy}
                        placeholder="e.g. Parent, Guardian"
                        required
                      />
                    </label>

                    <label className="grid gap-1 text-sm font-medium text-[color:var(--color-text-strong)]">
                      Consent date
                      <input
                        type="date"
                        className="min-h-11 w-full rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-white px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
                        value={consentDate}
                        onChange={(e) => setConsentDate(e.target.value)}
                        disabled={consentBusy}
                        required
                      />
                    </label>
                  </div>

                  <label className="grid gap-1 text-sm font-medium text-[color:var(--color-text-strong)]">
                    Verification notes
                    <textarea
                      className="min-h-24 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-white p-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] resize-y"
                      value={consentNotes}
                      onChange={(e) => setConsentNotes(e.target.value)}
                      disabled={consentBusy}
                      placeholder="Add any verification comments, reference document numbers, or meeting details here."
                    />
                  </label>

                  <div className="flex flex-wrap gap-3">
                    <ActionButton type="submit" disabled={consentBusy || !consentChecked}>
                      {consentBusy ? "Verifying..." : "Verify and Grant Consent"}
                    </ActionButton>
                  </div>
                </form>
              </Stack>
            </Stack>
          ) : (
            <Stack as="section" className="rounded-[var(--radius-shell)] border border-emerald-200 bg-emerald-50 p-5 shadow-soft" gap={4}>
              <Stack direction="horizontal" justify="between" align="center" className="flex-wrap gap-3">
                <Stack direction="horizontal" gap={3} align="center" className="flex-wrap">
                  <span className="inline-flex min-h-8 items-center gap-2 rounded-full border border-emerald-300 bg-emerald-100 px-3 text-xs font-semibold text-emerald-800">
                    <ShieldCheck size={14} aria-hidden="true" />
                    Consent Active
                  </span>
                  <Text weight="medium" className="text-emerald-900">
                    Caregiver consent has been verified and clinical workflows are unlocked.
                  </Text>
                </Stack>
                <ActionButton
                  type="button"
                  tone="secondary"
                  onClick={handleWithdrawConsent}
                  disabled={consentBusy}
                  className="border-emerald-300 hover:border-rose-400 hover:bg-rose-50 hover:text-rose-700"
                >
                  Withdraw Consent
                </ActionButton>
              </Stack>
            </Stack>
          )}

          {consentMsg && (
            <p className={`rounded-[var(--radius-card)] border px-4 py-3 text-sm font-medium ${
              consentMsg.includes("Failed") || consentMsg.includes("Could not")
                ? "border-rose-100 bg-rose-50 text-rose-950"
                : "border-cyan-100 bg-cyan-50 text-cyan-950"
            }`}>
              {consentMsg}
            </p>
          )}

          <section className="grid gap-6 lg:grid-cols-2">
            <InfoCard title="Case summary">
              <DetailRow label="Child label" value={caseLabel(caseItem)} />
              <DetailRow label="Age" value={ageLabel(caseItem)} />
              <DetailRow label="Language" value={languageLabel(caseItem)} />
              <DetailRow label="Referral/context" value={caseItem.notes?.trim() || "Referral or intake context has not been added yet."} />
            </InfoCard>

            <CareTeamManagementCard caseItem={caseItem} />

            <InfoCard title="Communication goals">
              {goals.length ? (
                <div className="space-y-3">
                  {goals.map((goal) => (
                    <div key={goal.goal_id} className="rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4">
                      <p className="font-medium text-[color:var(--color-text-strong)]">{goal.title}</p>
                      <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
                        {goal.target?.trim() || "Target not yet documented."}
                      </p>
                      {goal.notes?.trim() ? (
                        <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">{goal.notes}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm leading-6 text-[color:var(--color-text-muted)]">No communication goals recorded yet.</p>
              )}
            </InfoCard>
          </section>

          <InfoCard title="Session history">
            {timeline.length ? (
              <DataTable
                caption="Case session history"
                columns={[
                  { key: "session", header: "Session" },
                  { key: "date", header: "Date" },
                  { key: "status", header: "Status" },
                  { key: "nextAction", header: "Next action" }
                ]}
                rows={timeline.map((event) => ({
                  id: event.event_id,
                  session: <span className="font-medium">{event.label}</span>,
                  date: new Date(event.occurred_at).toLocaleString(),
                  status: <StatusBadge status={event.status} />,
                  nextAction: (
                    <Link
                      href={`/record?case_id=${caseItem.case_id}&session_id=${event.target_id}`}
                      className="inline-flex min-h-11 items-center gap-2 rounded-full border border-[color:var(--color-border)] px-4 py-2 font-medium text-[color:var(--color-text-strong)] transition hover:border-[color:var(--color-accent-strong)] hover:bg-[color:var(--color-accent-soft)]"
                    >
                      Open session workspace
                      <ArrowRight size={16} aria-hidden="true" />
                    </Link>
                  )
                }))}
              />
            ) : (
              <p className="text-sm leading-6 text-[color:var(--color-text-muted)]">No sessions recorded yet for this case.</p>
            )}
          </InfoCard>

          <section className="grid gap-6 lg:grid-cols-2">
            <InfoCard title="Upcoming tasks">
              <ul className="space-y-3 text-sm leading-6 text-[color:var(--color-text-muted)]">
                {tasks.map((task) => (
                  <li key={task} className="flex gap-3">
                    <CircleDot size={18} className="mt-1 shrink-0 text-[color:var(--color-accent-strong)]" aria-hidden="true" />
                    <span>{task}</span>
                  </li>
                ))}
              </ul>
            </InfoCard>

            <InfoCard title="Recent notes">
              <p className="text-sm leading-6 text-[color:var(--color-text-muted)]">
                {caseItem.notes?.trim() || "No recent therapist notes recorded yet."}
              </p>
            </InfoCard>
          </section>

          <SafetyNotice>
            Decision-support only. Case detail is a workflow summary and referral/context record. It does not display diagnostic conclusions.
          </SafetyNotice>
        </div>

        <aside className="space-y-4">
          <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-glass)] p-5 shadow-soft backdrop-blur-xl">
            <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">Progress snapshot</h2>
            <div className="mt-4 grid gap-3">
              {snapshot.map((item) => (
                <StatCard key={item.label} label={item.label} value={item.value} helper={item.helper} icon={Sparkles} />
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function HeaderMeta({
  label,
  value,
  icon: Icon
}: {
  label: string;
  value: string;
  icon: typeof Activity;
}) {
  return (
    <div className="rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3">
      <div className="flex items-center gap-2 text-xs uppercase tracking-[0.1em] text-[color:var(--color-text-subtle)]">
        <Icon size={14} aria-hidden="true" />
        <span>{label}</span>
      </div>
      <p className="mt-2 text-sm font-medium text-[color:var(--color-text-strong)]">{value}</p>
    </div>
  );
}

function InfoCard({
  title,
  children
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5 shadow-soft">
      <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-[color:var(--color-border)] py-3 last:border-b-0">
      <p className="text-xs uppercase tracking-[0.1em] text-[color:var(--color-text-subtle)]">{label}</p>
      <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-strong)]">{value}</p>
    </div>
  );
}

function CareTeamManagementCard({ caseItem }: { caseItem: BackendCase }) {
  const session = useMockAccessSession();
  const [memberships, setMemberships] = useState<OrganizationMembership[]>([]);
  const [assignments, setAssignments] = useState<CareTeamAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [selectedUserId, setSelectedUserId] = useState("");
  const [selectedRole, setSelectedRole] = useState("therapist");
  const [makePrimary, setMakePrimary] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void (async () => {
      try {
        const [loadedAssignments, loadedMemberships] = await Promise.all([
          listCaseCareTeamAssignments(caseItem.case_id),
          listOrganizationMemberships(),
        ]);
        if (cancelled) return;
        setAssignments(loadedAssignments);
        const activeMemberships = loadedMemberships.filter((member) => member.active);
        setMemberships(activeMemberships);
        const firstAssignable = activeMemberships.find((member) => member.user_id !== caseItem.primary_therapist_user_id);
        setSelectedUserId(firstAssignable?.user_id ?? activeMemberships[0]?.user_id ?? "");
      } catch {
        if (cancelled) return;
        setMessage("Care-team management requires the local backend admin flow.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [caseItem.case_id, caseItem.primary_therapist_user_id, session?.organizationId]);

  const activeAssignments = assignments.filter((item) => item.active);
  const primaryAssignment = activeAssignments.find((item) => item.is_primary);
  const availableMemberships = memberships.filter((member) => !activeAssignments.some((item) => item.user_id === member.user_id));

  async function refreshAssignments() {
    const loadedAssignments = await listCaseCareTeamAssignments(caseItem.case_id);
    setAssignments(loadedAssignments);
  }

  async function handleAssign(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedUserId) return;
    setBusy(true);
    setMessage("");
    try {
      await assignCaseCareTeamMember(caseItem.case_id, {
        user_id: selectedUserId,
        role: selectedRole,
        active: true,
        is_primary: makePrimary,
      });
      await refreshAssignments();
      const promotedLabel = memberships.find((member) => member.user_id === selectedUserId)?.display_name ?? clinicianLabel(selectedUserId);
      setMessage(makePrimary ? `Primary therapist reassigned to ${promotedLabel}.` : `Care-team assignment updated for ${promotedLabel}.`);
      setMakePrimary(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update the care team.");
    } finally {
      setBusy(false);
    }
  }

  async function handlePromotePrimary(userId: string) {
    const existing = activeAssignments.find((item) => item.user_id === userId);
    if (!existing) return;
    setBusy(true);
    setMessage("");
    try {
      await assignCaseCareTeamMember(caseItem.case_id, {
        user_id: existing.user_id,
        role: existing.role,
        active: true,
        is_primary: true,
      });
      await refreshAssignments();
      setMessage(`Primary therapist reassigned to ${clinicianLabel(userId)}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not reassign the primary therapist.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeactivateAssignment(assignment: CareTeamAssignment) {
    setBusy(true);
    setMessage("");
    try {
      await assignCaseCareTeamMember(caseItem.case_id, {
        user_id: assignment.user_id,
        role: assignment.role,
        active: false,
        is_primary: false,
      });
      await refreshAssignments();
      setMessage(
        assignment.is_primary
          ? `Primary therapist assignment removed for ${clinicianLabel(assignment.user_id)}. Report sign-off stays blocked until reassigned.`
          : `Care-team assignment removed for ${clinicianLabel(assignment.user_id)}.`,
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not deactivate the care-team assignment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <InfoCard title="Care team & sign-off ownership">
      <div className="space-y-4">
        <div className="rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4">
          <p className="text-xs uppercase tracking-[0.1em] text-[color:var(--color-text-subtle)]">Primary assigned therapist</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <p className="text-sm font-semibold text-[color:var(--color-text-strong)]">
              {primaryAssignment ? clinicianLabel(primaryAssignment.user_id) : "Not assigned"}
            </p>
            {primaryAssignment ? (
              <span className="inline-flex min-h-8 items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 text-xs font-semibold text-amber-900">
                <Crown size={14} aria-hidden="true" />
                Sign-off owner
              </span>
            ) : (
              <span className="inline-flex min-h-8 items-center rounded-full border border-amber-200 bg-amber-50 px-3 text-xs font-semibold text-amber-900">
                Reassignment required before report sign-off
              </span>
            )}
          </div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
            Report finalization is restricted to the primary assigned therapist. If the primary therapist is revoked or removed, sign-off remains blocked until reassigned.
          </p>
        </div>

        <div className="space-y-3">
          {loading ? (
            <p className="text-sm text-[color:var(--color-text-muted)]">Loading care-team assignments...</p>
          ) : activeAssignments.length ? (
            activeAssignments.map((assignment) => (
              <div key={assignment.assignment_id} className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-[color:var(--color-text-strong)]">{clinicianLabel(assignment.user_id)}</p>
                  <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
                    {assignment.role} {assignment.is_primary ? "· primary therapist" : "· care-team member"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {!assignment.is_primary ? (
                    <ActionButton type="button" tone="secondary" disabled={busy} onClick={() => void handlePromotePrimary(assignment.user_id)}>
                      Make primary therapist
                    </ActionButton>
                  ) : null}
                  <ActionButton type="button" tone="ghost" disabled={busy} onClick={() => void handleDeactivateAssignment(assignment)}>
                    Remove assignment
                  </ActionButton>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm leading-6 text-[color:var(--color-text-muted)]">No backend care-team assignments returned yet.</p>
          )}
        </div>

        <form className="grid gap-3 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4" onSubmit={handleAssign}>
          <div>
            <p className="text-sm font-semibold text-[color:var(--color-text-strong)]">Assign or reassign therapist</p>
            <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
              This pilot admin flow reuses organization memberships that are already active in the current organization.
            </p>
          </div>
          <label className="grid gap-1 text-sm font-medium text-[color:var(--color-text-strong)]">
            Organization member
            <select
              className="min-h-11 rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-white px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
              value={selectedUserId}
              onChange={(event) => setSelectedUserId(event.target.value)}
              disabled={busy || !availableMemberships.length}
            >
              {availableMemberships.length ? availableMemberships.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {member.display_name} · {member.role}
                </option>
              )) : (
                <option value="">No additional active memberships</option>
              )}
            </select>
          </label>
          <label className="grid gap-1 text-sm font-medium text-[color:var(--color-text-strong)]">
            Care-team role
            <select
              className="min-h-11 rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-white px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
              value={selectedRole}
              onChange={(event) => setSelectedRole(event.target.value)}
              disabled={busy}
            >
              <option value="therapist">Therapist</option>
              <option value="clinical_supervisor">Clinical supervisor</option>
              <option value="org_admin">Org admin</option>
            </select>
          </label>
          <label className="flex items-start gap-3 text-sm text-[color:var(--color-text-muted)]">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 rounded border-[color:var(--color-border)]"
              checked={makePrimary}
              onChange={(event) => setMakePrimary(event.target.checked)}
              disabled={busy}
            />
            <span>Set this assignment as the primary therapist and transfer sign-off ownership.</span>
          </label>
          <div className="flex flex-wrap gap-3">
            <ActionButton type="submit" disabled={busy || !selectedUserId}>
              Assign to care team
            </ActionButton>
            <ActionButton type="button" tone="ghost" disabled={busy || loading} onClick={() => void refreshAssignments()}>
              <RefreshCw size={16} aria-hidden="true" />
              Refresh
            </ActionButton>
          </div>
        </form>

        {message ? (
          <p className="rounded-[var(--radius-card)] border border-cyan-100 bg-cyan-50 px-4 py-3 text-sm font-medium text-cyan-950">
            {message}
          </p>
        ) : null}
      </div>
    </InfoCard>
  );
}
