"use client";

import Link from "next/link";
import type { FormEvent, ReactNode } from "react";
import { Activity, ArrowRight, CalendarDays, CircleDot, Crown, RefreshCw, ShieldCheck, Sparkles, Users } from "lucide-react";
import { Stack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";

import { ActionButton } from "@/components/action-button";
import { DataTable } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { PipelineProgressBar } from "@/components/pipeline-progress-bar";
import { SafetyNotice } from "@/components/safety-notice";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import type { CaseCareTeamViewModel, CaseDetailViewModel } from "@/features/cases/hooks/use-cases-workspace";
import type { BackendCase, BackendGoal, BackendTimelineEvent } from "@/lib/workflow";

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

export function CaseDetail({ model }: { model: CaseDetailViewModel }) {
  const { caseItem, timeline, goals, consent, careTeam } = model;
  const {
    localConsent,
    consentSigner,
    setConsentSigner,
    consentChecked,
    setConsentChecked,
    consentDate,
    setConsentDate,
    consentNotes,
    setConsentNotes,
    consentBusy,
    consentMsg,
  } = consent;
  const isConsentGranted = localConsent.toLowerCase() === "granted";
  const localWorkflowStage = getLocalWorkflowStage(caseItem, localConsent);
  const snapshot = getProgressSnapshot(caseItem, localWorkflowStage);
  const tasks = buildUpcomingTasks(caseItem, timeline, goals, localConsent);

  function handleGrantConsent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void consent.grantConsent();
  }

  function handleWithdrawConsent() {
    if (!confirm("Are you sure you want to withdraw consent? This will redact child details and disable clinical workflows for this case.")) return;
    void consent.withdrawConsent();
  }

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

      <section className="workspace-panel p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="grid h-12 w-12 place-items-center rounded-[var(--radius-card)] bg-[color:var(--color-accent-soft)] text-lg font-semibold text-[color:var(--color-accent-strong)]">
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

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_var(--rail-width)]">
        <div className="space-y-6">
          {!isConsentGranted ? (
            <Stack gap={4}>
              <Stack className="rounded-[var(--radius-shell)] border border-amber-200 bg-amber-50 p-5" gap={3}>
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

              <Stack as="section" className="workspace-panel p-5" gap={4}>
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
                        className="min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
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
                        className="min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
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
                      className="min-h-24 w-full resize-y rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
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
              <Stack as="section" className="rounded-[var(--radius-shell)] border border-emerald-200 bg-emerald-50 p-5" gap={4}>
              <Stack direction="horizontal" justify="between" align="center" className="flex-wrap gap-3">
                <Stack direction="horizontal" gap={3} align="center" className="flex-wrap">
                  <span className="inline-flex min-h-8 items-center gap-2 rounded-[var(--radius-card)] border border-emerald-300 bg-emerald-100 px-3 text-xs font-semibold text-emerald-800">
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

            <CareTeamManagementCard model={careTeam} />

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
                      className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-[color:var(--color-border)] px-4 py-2 font-medium text-[color:var(--color-text-strong)] transition hover:border-[color:var(--color-accent-strong)] hover:bg-[color:var(--color-accent-soft)]"
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
          <section className="workspace-panel p-5">
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
  children: ReactNode;
}) {
  return (
    <section className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5">
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


function CareTeamManagementCard({ model }: { model: CaseCareTeamViewModel }) {
  const {
    activeAssignments,
    primaryAssignment,
    availableMemberships,
    loading,
    busy,
    message,
    selectedUserId,
    setSelectedUserId,
    selectedRole,
    setSelectedRole,
    makePrimary,
    setMakePrimary,
    refreshAssignments,
    assign,
    promotePrimary: handlePromotePrimary,
    deactivateAssignment: handleDeactivateAssignment,
  } = model;

  function handleAssign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void assign();
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
              <span className="inline-flex min-h-8 items-center gap-2 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 px-3 text-xs font-semibold text-amber-900">
                <Crown size={14} aria-hidden="true" />
                Sign-off owner
              </span>
            ) : (
              <span className="inline-flex min-h-8 items-center rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 px-3 text-xs font-semibold text-amber-900">
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
              className="min-h-11 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
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
              className="min-h-11 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
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

