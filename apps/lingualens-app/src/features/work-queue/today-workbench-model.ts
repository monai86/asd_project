import { resolveSessionHref } from "@/features/sessions/state/session-view";
import type { BackendCase, BackendReport } from "@/lib/workflow";

export type TodayQueueGroupKey =
  | "needs_action"
  | "processing"
  | "ready_for_review"
  | "ready_for_signoff"
  | "recently_completed";

export type TodayQueueItem = {
  id: string;
  caseId: string;
  caseLabel: string;
  sessionDate?: string;
  taskType: string;
  workflowStatus: string;
  reviewPriority: string;
  reason: string;
  group: TodayQueueGroupKey;
  actionLabel: string;
  href: string;
};

export type TodayRecentCase = {
  caseId: string;
  caseLabel: string;
  latestActivity?: string;
  workflowStatus: string;
};

export type TodayWorkbenchModel = {
  items: TodayQueueItem[];
  recentCases: TodayRecentCase[];
  summary: {
    needsAction: number;
    readyForReview: number;
    readyForSignoff: number;
  };
};

export const todayQueueGroups: Array<{
  key: TodayQueueGroupKey;
  label: string;
  description: string;
}> = [
  { key: "needs_action", label: "Needs action", description: "Blocked, stale, failed, or incomplete work requiring a therapist decision." },
  { key: "processing", label: "Processing", description: "Backend work is still running. No completion is assumed." },
  { key: "ready_for_review", label: "Ready for review", description: "Persisted transcript or report material is ready for therapist review." },
  { key: "ready_for_signoff", label: "Ready for sign-off", description: "Reviewed report drafts awaiting the therapist’s final decision." },
  { key: "recently_completed", label: "Recently completed", description: "Recently signed work available as an immutable record." },
];

const groupRank = new Map(todayQueueGroups.map((group, index) => [group.key, index]));

export function buildTodayWorkbench(
  cases: BackendCase[],
  reports: BackendReport[],
): TodayWorkbenchModel {
  const latestReportByCase = latestReportsByCase(reports);
  const items = cases
    .map((caseItem) => buildCaseQueueItem(caseItem, latestReportByCase.get(caseItem.case_id)))
    .sort((left, right) => {
      const groupDifference = (groupRank.get(left.group) ?? 0) - (groupRank.get(right.group) ?? 0);
      if (groupDifference !== 0) return groupDifference;
      return timestamp(right.sessionDate) - timestamp(left.sessionDate);
    });

  const recentCases = [...cases]
    .sort((left, right) => timestamp(right.updated_at ?? right.latest_session_date) - timestamp(left.updated_at ?? left.latest_session_date))
    .slice(0, 4)
    .map((caseItem) => ({
      caseId: caseItem.case_id,
      caseLabel: caseLabel(caseItem),
      latestActivity: caseItem.updated_at ?? caseItem.latest_session_date,
      workflowStatus: normalizedDisplayStatus(caseItem.latest_session_status),
    }));

  return {
    items,
    recentCases,
    summary: {
      needsAction: items.filter((item) => item.group === "needs_action").length,
      readyForReview: items.filter((item) => item.group === "ready_for_review").length,
      readyForSignoff: items.filter((item) => item.group === "ready_for_signoff").length,
    },
  };
}

function buildCaseQueueItem(caseItem: BackendCase, report?: BackendReport): TodayQueueItem {
  const reportStatus = normalizeStatus(report?.status ?? caseItem.latest_report_status);
  const sessionStatus = normalizeStatus(caseItem.latest_session_status);
  const base = {
    id: report?.report_id ? `report:${report.report_id}` : `case:${caseItem.case_id}`,
    caseId: caseItem.case_id,
    caseLabel: caseLabel(caseItem),
    sessionDate: caseItem.latest_session_date,
    reviewPriority: normalizedDisplayStatus(caseItem.review_priority || "low"),
  };

  if (reportStatus === "stale") {
    return {
      ...base,
      taskType: "Report regeneration",
      workflowStatus: "Stale",
      reason: "A newer transcript invalidated the existing report draft.",
      group: "needs_action",
      actionLabel: "Regenerate report",
      href: reportHref(report, caseItem.case_id),
    };
  }
  if (isFailed(reportStatus)) {
    return {
      ...base,
      taskType: "Report safety review",
      workflowStatus: normalizedDisplayStatus(reportStatus),
      reason: "The persisted report is blocked or failed and requires therapist review.",
      group: "needs_action",
      actionLabel: "Review report",
      href: reportHref(report, caseItem.case_id),
    };
  }
  if (isSigned(reportStatus)) {
    return {
      ...base,
      taskType: "Signed report",
      workflowStatus: normalizedDisplayStatus(reportStatus),
      reason: "The signed snapshot is complete and remains immutable.",
      group: "recently_completed",
      actionLabel: "View signed report",
      href: reportHref(report, caseItem.case_id),
    };
  }
  if (report && isReadyForSignoff(reportStatus, report.therapist_signoff_status)) {
    return {
      ...base,
      taskType: "Report sign-off",
      workflowStatus: normalizedDisplayStatus(reportStatus),
      reason: "A reviewed report draft is ready for the therapist’s sign-off decision.",
      group: "ready_for_signoff",
      actionLabel: "Review for sign-off",
      href: reportHref(report, caseItem.case_id),
    };
  }
  if (report && ["draft", "needs review", "needs_review"].includes(reportStatus)) {
    return {
      ...base,
      taskType: "Report review",
      workflowStatus: normalizedDisplayStatus(reportStatus),
      reason: "A persisted report draft is ready for therapist review.",
      group: "ready_for_review",
      actionLabel: "Review report",
      href: reportHref(report, caseItem.case_id),
    };
  }
  if (sessionStatus === "processing") {
    return {
      ...base,
      taskType: "Session processing",
      workflowStatus: "Processing",
      reason: "Backend processing is still in progress.",
      group: "processing",
      actionLabel: "View case",
      href: caseHref(caseItem.case_id),
    };
  }
  if (["needs review", "needs_review", "attested", "ready"].includes(sessionStatus)) {
    return {
      ...base,
      taskType: "Transcript review",
      workflowStatus: normalizedDisplayStatus(sessionStatus),
      reason: sessionStatus === "attested"
        ? "The reviewed transcript is ready for the next backend-permitted workflow step."
        : "The persisted session is ready for therapist transcript review.",
      group: "ready_for_review",
      actionLabel: "Open case",
      href: caseHref(caseItem.case_id),
    };
  }
  if (isFailed(sessionStatus)) {
    return {
      ...base,
      taskType: "Session follow-up",
      workflowStatus: normalizedDisplayStatus(sessionStatus),
      reason: "The persisted session is blocked or failed and requires therapist action.",
      group: "needs_action",
      actionLabel: "Review case",
      href: caseHref(caseItem.case_id),
    };
  }
  return {
    ...base,
    taskType: caseItem.latest_session_date ? "Session intake" : "Start session",
    workflowStatus: normalizedDisplayStatus(caseItem.latest_session_status || "Not started"),
    reason: caseItem.latest_session_date
      ? "The persisted session is incomplete and needs the therapist’s next input."
      : "No persisted session is available for this case yet.",
    group: "needs_action",
    actionLabel: caseItem.latest_session_date ? "Continue case" : "Start session",
    href: caseItem.latest_session_date ? caseHref(caseItem.case_id) : `/cases?intent=start-session&case_id=${encodeURIComponent(caseItem.case_id)}`,
  };
}

function latestReportsByCase(reports: BackendReport[]) {
  const result = new Map<string, BackendReport>();
  for (const report of reports) {
    if (!report.case_id) continue;
    const existing = result.get(report.case_id);
    if (!existing || timestamp(report.updated_at ?? report.created_at) >= timestamp(existing.updated_at ?? existing.created_at)) {
      result.set(report.case_id, report);
    }
  }
  return result;
}

function reportHref(report: BackendReport | undefined, caseId: string) {
  return resolveSessionHref("report", report?.session_id?.trim(), {
    caseId,
    reportId: report?.report_id,
  });
}

function caseHref(caseId: string) {
  return `/cases/${encodeURIComponent(caseId)}`;
}

function caseLabel(caseItem: BackendCase) {
  return caseItem.anonymized_child_code
    || caseItem.child_code
    || caseItem.display_label
    || `Case ${caseItem.case_id.slice(-6)}`;
}

function normalizeStatus(value?: string) {
  return `${value ?? ""}`.trim().toLowerCase();
}

function normalizedDisplayStatus(value?: string) {
  const normalized = `${value ?? ""}`.trim().replaceAll("_", " ");
  if (!normalized) return "Not started";
  return normalized.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function isFailed(status: string) {
  return status.includes("failed") || status.includes("blocked") || status === "withdrawn";
}

function isSigned(status: string) {
  return status.includes("signed") || status.includes("finalized");
}

function isReadyForSignoff(status: string, signoffStatus?: string) {
  const signoff = normalizeStatus(signoffStatus);
  return status === "ready" || status === "reviewed" || signoff.includes("ready");
}

function timestamp(value?: string) {
  if (!value) return 0;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}
