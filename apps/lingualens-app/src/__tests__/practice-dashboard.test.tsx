import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/dashboard/page";
import { PracticeDashboardView } from "@/features/dashboard/components/practice-dashboard-view";
import { renderAsyncPage } from "@/__tests__/setup";
import type { DashboardSummary } from "@/lib/workflow";

const { mockRuntimeSettings } = vi.hoisted(() => {
  const settings = {
    mock_mode: true,
    auth_mode: "mock",
    model_version: "v2-mock",
    feature_schema: "lingualens-app.1",
    guideline_mapping: "review-support-only",
    user_roles: ["therapist"],
    access_model: {
      invitation_only: true,
      required_app_aal: "aal2",
      active_organization_session: "explicit_selection_when_ambiguous",
      production_mock_mode: "local_only",
    },
    data_retention: "local test data",
    consent_policy: "visible per case",
    capabilities: {
      cases: "available",
      audio_upload: "experimental",
      transcription: "experimental",
      transcript_qa: "available",
      feature_extraction: "available",
      ai_review: "disabled",
      report_drafting: "disabled",
      pdf_export: "unavailable",
    },
    pipeline_settings: {
      audio_processing: "experimental_async",
      job_queue_mode: "memory",
      repository_mode: "memory",
      storage_mode: "local_private",
    },
  } as const;
  return { mockRuntimeSettings: settings };
});

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({ status: "success", mode: "backend", data: mockRuntimeSettings }),
}));

const summaryFixture: DashboardSummary = {
  organization_id: "pilot_org_001",
  generated_at: "2026-08-16T10:00:00.000Z",
  cases: {
    total: 4,
    consent_counts: { granted: 3, pending: 1 },
    with_latest_reviewed_session: 2,
  },
  sessions: {
    total: 9,
    status_counts: { "Needs Review": 4, Draft: 3, "Signed Off": 2 },
    with_transcript: 8,
    with_features: 6,
    with_ml_review: 5,
    with_report: 4,
  },
  reports: {
    total: 4,
    signoff_counts: { "Signed Off": 2, "Needs Review": 2 },
  },
  recent_sessions: [
    {
      session_id: "session-9",
      case_id: "case-9",
      case_label: "Case Nine",
      session_date: "2026-08-15",
      status: "Needs Review",
      has_transcript: true,
      has_features: true,
      has_ml_review: true,
      has_report: true,
    },
    {
      session_id: "session-8",
      case_id: "case-8",
      case_label: "Case Eight",
      session_date: "2026-08-14",
      status: "Draft",
      has_transcript: true,
      has_features: false,
      has_ml_review: false,
      has_report: false,
    },
  ],
};

const jsonResponse = (body: unknown) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });

function mockSummaryFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/dashboard/summary")) {
      return jsonResponse(summaryFixture);
    }
    return jsonResponse({});
  });
}

beforeEach(() => {
  window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
    role: "therapist",
    organizationId: "pilot_org_001",
    aal: "aal2",
  }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

describe("practice dashboard", () => {
  it("renders the caseload stats, consent breakdown, and pipeline progress from the summary", async () => {
    vi.stubGlobal("fetch", mockSummaryFetch());

    await renderAsyncPage(DashboardPage);

    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    const casesStat = screen.getByText("Active cases").closest("section")!;
    expect(within(casesStat).getByText("4")).toBeInTheDocument();
    const sessionsStat = screen.getByText("Sessions").closest("section")!;
    expect(within(sessionsStat).getByText("9")).toBeInTheDocument();

    const consentSection = screen.getByRole("region", { name: "Consent status" });
    expect(within(consentSection).getByText("Granted")).toBeInTheDocument();
    expect(within(consentSection).getByText("3")).toBeInTheDocument();

    const pipelineSection = screen.getByRole("region", { name: "Pipeline progress" });
    expect(within(pipelineSection).getByText("Features extracted")).toBeInTheDocument();
    expect(within(pipelineSection).getByText("6")).toBeInTheDocument();
  });

  it("lists recent sessions with a stage label and a deep link into the session workspace", async () => {
    vi.stubGlobal("fetch", mockSummaryFetch());

    await renderAsyncPage(DashboardPage);

    const recentSection = screen.getByRole("region", { name: "Recent sessions" });
    expect(within(recentSection).getAllByText("Case Nine").length).toBeGreaterThan(0);
    expect(within(recentSection).getAllByText("Report drafted").length).toBeGreaterThan(0);
    expect(within(recentSection).getAllByText("Transcript ready").length).toBeGreaterThan(0);
    expect(
      within(recentSection).getAllByRole("link", { name: "Case Nine" })[0],
    ).toHaveAttribute("href", "/sessions/session-9?case_id=case-9");
  });

  it("shows a calm empty state when there are no sessions yet", () => {
    const empty = { ...summaryFixture, recent_sessions: [], sessions: { ...summaryFixture.sessions, total: 0 } };
    render(<PracticeDashboardView summary={empty} />);

    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText(/No sessions yet\./)).toBeInTheDocument();
  });

  it("renders the fallback alert when the backend summary is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    await renderAsyncPage(DashboardPage);

    expect(await screen.findByRole("heading", { name: "Practice summary could not be loaded" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to Today" })).toHaveAttribute("href", "/today");
  });
});
