import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
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
  feature_trends: {
    features: [
      { key: "mlu_words", label: "MLU (words)", unit: "words per utterance" },
      { key: "ndw", label: "NDW (different words)", unit: "words" },
      { key: "ttr", label: "Type–Token Ratio", unit: "ratio" },
    ],
    cases: [
      {
        case_id: "case-alpha",
        case_label: "Case Alpha",
        points: [
          {
            session_id: "session-a1",
            session_date: "2026-06-01",
            values: { mlu_words: 2.4, ndw: 28, ttr: 0.52 },
          },
          {
            session_id: "session-a2",
            session_date: "2026-08-01",
            values: { mlu_words: 3.1, ndw: 41, ttr: 0.48 },
          },
        ],
        reference: {
          age_band: "60-71",
          task_type: "toyplay",
          features: {
            mlu_words: { q1: 1.4, median: 2.0, q3: 2.9 },
            ttr: { q1: 0.4, median: 0.55, q3: 0.7 },
          },
        },
      },
      {
        case_id: "case-beta",
        case_label: "Case Beta",
        points: [
          {
            session_id: "session-b1",
            session_date: "2026-07-15",
            values: { mlu_words: 1.9 },
          },
        ],
      },
    ],
  },
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

  it("plots session-level feature trends with case and feature selection", async () => {
    vi.stubGlobal("fetch", mockSummaryFetch());

    await renderAsyncPage(DashboardPage);

    const progressSection = screen.getByRole("region", { name: "Language progress" });
    // Default feature is the first one; values for the case with the most points.
    expect(within(progressSection).getAllByText("MLU (words)").length).toBeGreaterThan(0);
    expect(within(progressSection).getByText("2.4")).toBeInTheDocument();
    expect(within(progressSection).getByText("3.1")).toBeInTheDocument();
    expect(within(progressSection).getByText("Case Alpha")).toBeInTheDocument();

    // Switching the feature re-plots the values for the same case.
    fireEvent.change(within(progressSection).getByLabelText("Feature"), {
      target: { value: "ndw" },
    });
    expect(within(progressSection).getByText("28")).toBeInTheDocument();
    expect(within(progressSection).getByText("41")).toBeInTheDocument();

    // Switching the case shows its series (a single point keeps the hint).
    fireEvent.change(within(progressSection).getByLabelText("Feature"), {
      target: { value: "mlu_words" },
    });
    fireEvent.change(within(progressSection).getByLabelText("Case"), {
      target: { value: "case-beta" },
    });
    expect(within(progressSection).getByText("1.9")).toBeInTheDocument();
    expect(within(progressSection).getByText(/One session with mlu \(words\) data so far/)).toBeInTheDocument();
  });

  it("deep-links chart points and table rows into the session workspace", async () => {
    vi.stubGlobal("fetch", mockSummaryFetch());

    await renderAsyncPage(DashboardPage);

    const progressSection = screen.getByRole("region", { name: "Language progress" });
    // Chart-dot overlay hit areas (44px) carry case context.
    const overlay = within(progressSection).getAllByRole("link", { name: /Open session/ })[0];
    expect(overlay).toHaveAttribute("href", "/sessions/session-a1?case_id=case-alpha");
    // The visible date cells are links to the same session.
    const dateLinks = within(progressSection)
      .getAllByRole("link")
      .filter((link) => link.getAttribute("href") === "/sessions/session-a1?case_id=case-alpha");
    expect(dateLinks.length).toBeGreaterThanOrEqual(2);
  });

  it("renders the typical-development reference band when available", async () => {
    vi.stubGlobal("fetch", mockSummaryFetch());

    await renderAsyncPage(DashboardPage);

    const progressSection = screen.getByRole("region", { name: "Language progress" });
    expect(
      within(progressSection).getByText(/Reference band \(typical development, 60-71 months, toyplay\)/),
    ).toBeInTheDocument();
    expect(within(progressSection).getByText(/median 2 · IQR 1.4–2.9/)).toBeInTheDocument();
  });

  it("deduplicates case options that share a label in the Language progress picker", () => {
    const withDuplicates: DashboardSummary = {
      ...summaryFixture,
      feature_trends: {
        features: summaryFixture.feature_trends.features,
        cases: [
          {
            case_id: "case-a1",
            case_label: "Case Alpha",
            points: [{ session_id: "s1", session_date: "2026-06-01", values: { mlu_words: 2.0 } }],
          },
          {
            case_id: "case-a2",
            case_label: "Case Alpha",
            points: [
              { session_id: "s2", session_date: "2026-06-02", values: { mlu_words: 2.2 } },
              { session_id: "s3", session_date: "2026-06-03", values: { mlu_words: 2.5 } },
            ],
          },
          {
            case_id: "case-b",
            case_label: "Case Beta",
            points: [{ session_id: "s4", session_date: "2026-06-04", values: { mlu_words: 1.5 } }],
          },
        ],
      },
    };
    render(<PracticeDashboardView summary={withDuplicates} />);

    const progressSection = screen.getByRole("region", { name: "Language progress" });
    const caseSelect = within(progressSection).getByLabelText("Case");
    // One option per distinct label, and the entry with the most points wins.
    expect(within(caseSelect).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "Case Alpha",
      "Case Beta",
    ]);
    expect(within(progressSection).getByText("2.5")).toBeInTheDocument();
    expect(within(progressSection).queryByText("2.0")).not.toBeInTheDocument();
  });

  it("shows a calm empty state when no feature data exists yet", () => {
    const empty = {
      ...summaryFixture,
      feature_trends: { features: [], cases: [] },
    };
    render(<PracticeDashboardView summary={empty} />);

    expect(screen.getByText(/No language-progress data yet\./)).toBeInTheDocument();
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
