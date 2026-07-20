"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, ClipboardList, Filter, FolderOpen, Search, ShieldCheck } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { SafetyNotice } from "@/components/safety-notice";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import type { CaseListViewModel } from "@/features/cases/hooks/use-cases-workspace";
import type { BackendCase } from "@/lib/workflow";

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

function priorityLabel(value?: string) {
  if (!value) return "Priority not set";
  return `${value.charAt(0).toUpperCase()}${value.slice(1)} priority`;
}

function reportLabel(value?: string) {
  return `Report ${value ?? "not started"}`;
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
  return { label: "Start session", href: "/cases?intent=start-session" };
}

export function CaseList({
  model,
  canFilterByClinician = false,
}: {
  model: CaseListViewModel;
  canFilterByClinician?: boolean;
}) {
  const { cases } = model;
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [consentFilter, setConsentFilter] = useState("all");
  const [clinicianFilter, setClinicianFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"latest-activity" | "next-action">("latest-activity");
  const [selectedCaseId, setSelectedCaseId] = useState(cases[0]?.case_id ?? "");

  const stageOptions = useMemo(() => {
    const statuses = Array.from(new Set(cases.map((item) => item.latest_session_status ?? "Draft")));
    return ["all", ...statuses];
  }, [cases]);

  const clinicianOptions = useMemo(() => {
    return Array.from(new Set(cases.flatMap((item) => item.care_team_user_ids ?? [])));
  }, [cases]);

  const workflowStages = useMemo(() => Array.from(new Set(cases.map(workflowStage))), [cases]);

  const filteredCases = useMemo(() => {
    const filtered = cases.filter((caseItem) => {
      const matchesSearch = !query || [
        caseLabel(caseItem),
        codeLabel(caseItem),
        languageLabel(caseItem),
        clinicianList(caseItem)
      ].join(" ").toLowerCase().includes(query.toLowerCase());
      const matchesStatus = statusFilter === "all" || (caseItem.latest_session_status ?? "Draft") === statusFilter;
      const matchesConsent = consentFilter === "all" || (caseItem.consent_status ?? "unknown").toLowerCase() === consentFilter;
      const matchesClinician = clinicianFilter === "all" || (caseItem.care_team_user_ids ?? []).includes(clinicianFilter);
      return matchesSearch && matchesStatus && matchesConsent && matchesClinician;
    });
    return filtered.sort((left, right) => {
      if (sortBy === "next-action") {
        return workflowStage(left).localeCompare(workflowStage(right)) || caseLabel(left).localeCompare(caseLabel(right));
      }
      return (right.latest_session_date ?? "").localeCompare(left.latest_session_date ?? "")
        || caseLabel(left).localeCompare(caseLabel(right));
    });
  }, [cases, clinicianFilter, consentFilter, query, sortBy, statusFilter]);

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
  const selectedCase = filteredCases.find((caseItem) => caseItem.case_id === selectedCaseId) ?? filteredCases[0];

  const recentActivity = useMemo(() => {
    return [...cases]
      .filter((item) => item.latest_session_date)
      .sort((a, b) => (b.latest_session_date ?? "").localeCompare(a.latest_session_date ?? ""))
      .slice(0, 4);
  }, [cases]);

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

          <section className="workspace-panel p-4">
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
                    className="min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] pl-10 pr-4 text-sm text-[color:var(--color-text-strong)] outline-none transition focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
                  />
                </div>
              </div>

              {canFilterByClinician && clinicianOptions.length ? (
                <div className="w-full lg:max-w-[16rem]">
                  <label htmlFor="clinician-filter" className="mb-2 block text-sm font-medium text-[color:var(--color-text-strong)]">
                    Clinician filter
                  </label>
                  <select
                    id="clinician-filter"
                    aria-label="Clinician filter"
                    value={clinicianFilter}
                    onChange={(event) => setClinicianFilter(event.target.value)}
                    className="min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm text-[color:var(--color-text-strong)] outline-none transition focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
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
                    className={`inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] ${
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

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-medium text-[color:var(--color-text-strong)]">
                Consent filter
                <select
                  aria-label="Consent filter"
                  value={consentFilter}
                  onChange={(event) => setConsentFilter(event.target.value)}
                  className="min-h-11 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
                >
                  <option value="all">All consent states</option>
                  <option value="granted">Consent active</option>
                  <option value="pending">Consent pending</option>
                  <option value="withdrawn">Consent withdrawn</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm font-medium text-[color:var(--color-text-strong)]">
                Sort cases
                <select
                  aria-label="Sort cases"
                  value={sortBy}
                  onChange={(event) => setSortBy(event.target.value as "latest-activity" | "next-action")}
                  className="min-h-11 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
                >
                  <option value="latest-activity">Latest activity</option>
                  <option value="next-action">Next action</option>
                </select>
              </label>
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
                          <p className="text-xs text-[color:var(--color-text-muted)]">{priorityLabel(caseItem.review_priority)}</p>
                          <button
                            type="button"
                            onClick={() => setSelectedCaseId(caseItem.case_id)}
                            aria-pressed={selectedCase?.case_id === caseItem.case_id}
                            className="mt-2 inline-flex min-h-8 items-center rounded-[var(--radius-card)] border border-[color:var(--color-border)] px-3 text-xs font-semibold text-[color:var(--color-text-muted)] transition hover:border-[color:var(--color-accent-strong)] hover:text-[color:var(--color-accent-strong)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
                          >
                            Preview {caseLabel(caseItem)}
                          </button>
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
                      status: (
                        <div className="space-y-1">
                          <StatusBadge status={caseItem.latest_session_status ?? "Draft"} />
                          <p className="text-xs text-[color:var(--color-text-muted)]">{reportLabel(caseItem.latest_report_status)}</p>
                        </div>
                      ),
                      clinician: (
                        <div className="space-y-1">
                          <p className="font-medium">{primaryClinician(caseItem)}</p>
                          <p className="text-xs text-[color:var(--color-text-muted)]">{consentLabel(caseItem.consent_status)} consent</p>
                        </div>
                      ),
                      nextAction: (
                        <Link
                          href={action.href}
                          className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-[color:var(--color-border)] px-4 py-2 font-medium text-[color:var(--color-text-strong)] transition hover:border-[color:var(--color-accent-strong)] hover:bg-[color:var(--color-accent-soft)]"
                        >
                          {action.label}
                          <ArrowRight size={16} aria-hidden="true" />
                        </Link>
                      )
                    };
                  })}
                />
              </div>

              <ul className="space-y-3 lg:hidden" aria-label="Cases">
                {filteredCases.map((caseItem) => {
                  const action = nextAction(caseItem);
                  return (
                    <li key={caseItem.case_id} className="reading-surface p-4">
                      <div className="flex items-start gap-3">
                        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-[var(--radius-card)] bg-[color:var(--color-accent-soft)] font-semibold text-[color:var(--color-accent-strong)]">
                          {childInitials(caseItem)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <Link href={`/cases/${caseItem.case_id}`} className="font-semibold text-[color:var(--color-text-strong)]">
                            {caseLabel(caseItem)}
                          </Link>
                          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
                            {workflowStage(caseItem)} · {primaryClinician(caseItem)}
                          </p>
                          <p className="mt-1 text-xs text-[color:var(--color-text-muted)]">
                            {priorityLabel(caseItem.review_priority)} · {reportLabel(caseItem.latest_report_status)}
                          </p>
                        </div>
                        <StatusBadge status={caseItem.latest_session_status ?? "Draft"} />
                      </div>
                      <div className="mt-4">
                        <ActionButton href={action.href} tone="secondary" className="w-full">
                          {action.label}
                        </ActionButton>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <EmptyState
              title="No cases yet"
              description="Create or open a case from the backend workspace to view session progress here."
              action={<ActionButton href="/cases?intent=start-session">Start session</ActionButton>}
            />
          )}

          <footer className="control-strip flex flex-col gap-2 px-4 py-3 text-sm text-[color:var(--color-text-muted)] sm:flex-row sm:items-center sm:justify-between">
            <p>
              Showing {filteredCases.length ? `1-${filteredCases.length}` : "0-0"} of {cases.length} cases
            </p>
            <p>Filter results update in place and keep backend workflow state unchanged.</p>
          </footer>

          <SafetyNotice>
            Decision-support only. Use this workspace to organize therapist-reviewed workflow, not to infer diagnosis or secure-sharing status.
          </SafetyNotice>
        </div>

        <aside className="space-y-4" aria-label="Selected case context">
          <section className="workspace-panel hidden p-5 xl:block">
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[color:var(--color-text-subtle)]">Selected case context</p>
            {selectedCase ? (
              <div className="mt-3 space-y-4">
                <div>
                  <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">{caseLabel(selectedCase)}</h2>
                  <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
                    {codeLabel(selectedCase)} · {ageLabel(selectedCase)} · {languageLabel(selectedCase)}
                  </p>
                </div>
                <dl className="grid gap-3 text-sm">
                  <div className="reading-surface px-4 py-3">
                    <dt className="text-xs uppercase tracking-[0.08em] text-[color:var(--color-text-subtle)]">Next workflow stage</dt>
                    <dd className="mt-1 font-medium text-[color:var(--color-text-strong)]">{workflowStage(selectedCase)}</dd>
                  </div>
                  <div className="reading-surface px-4 py-3">
                    <dt className="text-xs uppercase tracking-[0.08em] text-[color:var(--color-text-subtle)]">Consent and priority</dt>
                    <dd className="mt-1 font-medium text-[color:var(--color-text-strong)]">
                      {consentLabel(selectedCase.consent_status)} consent · {priorityLabel(selectedCase.review_priority)}
                    </dd>
                  </div>
                  <div className="reading-surface px-4 py-3">
                    <dt className="text-xs uppercase tracking-[0.08em] text-[color:var(--color-text-subtle)]">Latest report</dt>
                    <dd className="mt-1 font-medium text-[color:var(--color-text-strong)]">{reportLabel(selectedCase.latest_report_status)}</dd>
                  </div>
                </dl>
                <ActionButton href={`/cases/${encodeURIComponent(selectedCase.case_id)}`} tone="secondary" className="w-full">
                  Open case detail
                </ActionButton>
              </div>
            ) : (
              <p className="mt-3 text-sm leading-6 text-[color:var(--color-text-muted)]">No case matches the current filters.</p>
            )}
          </section>

          <section className="workspace-panel p-5">
            <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">Case overview stats</h2>
            <div className="mt-4 grid gap-3">
              <StatCard label="Open cases" value={String(caseStats.total)} icon={FolderOpen} />
              <StatCard label="Needs review" value={String(caseStats.reviewQueue)} icon={ClipboardList} tone="warning" />
              <StatCard label="Consent follow-up" value={String(caseStats.pendingConsent)} icon={ShieldCheck} />
              <StatCard label="Reports ready" value={String(caseStats.readyReports)} icon={CheckCircle2} tone="success" />
            </div>
          </section>

          <section className="workspace-panel p-5">
            <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">Workflow at a glance</h2>
            <div className="mt-4 space-y-3">
              {workflowStages.slice(0, 5).map((stage) => (
                <div key={stage} className="reading-surface flex items-center justify-between px-4 py-3">
                  <span className="text-sm font-medium text-[color:var(--color-text-strong)]">{stage}</span>
                  <span className="text-sm text-[color:var(--color-text-muted)]">
                    {cases.filter((item) => workflowStage(item) === stage).length} case(s)
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="workspace-panel p-5">
            <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">Recent activity</h2>
            <div className="mt-4 space-y-3">
              {recentActivity.length ? recentActivity.map((item) => (
                <div key={item.case_id} className="reading-surface px-4 py-3">
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
    <section className="workspace-panel p-4">
      <div className="space-y-3 animate-pulse motion-reduce:animate-none">
        <div className="h-12 rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)]" />
        <div className="h-12 rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)]" />
        <div className="h-12 rounded-[var(--radius-card)] bg-[color:var(--color-surface-muted)]" />
      </div>
    </section>
  );
}
