import { createHash } from "node:crypto";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CaseDetailPage from "@/app/cases/[caseId]/page";
import CasesPage from "@/app/cases/page";
import ReportsPage from "@/app/reports/page";
import SettingsPage from "@/app/settings/page";
import TodayPage from "@/app/today/page";
import LoginPage from "@/app/login/page";
import { AppShell } from "@/components/app-shell";
import { ReportSummaryClient } from "@/components/report-summary-client";
import { SessionWorkspaceClient } from "@/components/session-workspace-client";
import { renderAsyncPage, routerPush } from "@/__tests__/setup";
import {
  WORKFLOW_STORAGE_KEY,
  createInitialWorkflowState,
  loadWorkflowState,
  saveWorkflowState
} from "@/lib/workflow";

const originalConsoleError = console.error;

function signedSnapshotFixture(payload: Record<string, unknown>) {
  const canonical = JSON.stringify(sortJsonValue(payload));
  const reportHash = createHash("sha256").update(canonical, "utf8").digest("hex");
  return { snapshot: { ...payload, report_hash: reportHash }, reportHash };
}

function sortJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortJsonValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => [key, sortJsonValue(item)]));
  }
  return value;
}

const { runtimeSettingsState, mockRuntimeSettings, supabaseRuntimeSettings } = vi.hoisted(() => {
  const capabilities = {
    cases: "available",
    audio_upload: "experimental",
    transcription: "experimental",
    transcript_qa: "available",
    feature_extraction: "available",
    ai_review: "disabled",
    report_drafting: "disabled",
    pdf_export: "unavailable",
  };
  const pipeline_settings = {
    audio_processing: "experimental_async",
    job_queue_mode: "memory",
    repository_mode: "json",
    storage_mode: "local_private",
  };
  const mock = {
    mock_mode: true,
    auth_mode: "mock",
    model_version: "v2-mock",
    feature_schema: "lingualens-app.1",
    guideline_mapping: "review-support-only",
    user_roles: ["therapist", "clinical_supervisor", "org_admin"],
    access_model: {
      invitation_only: true,
      required_app_aal: "aal2",
      active_organization_session: "explicit_selection_when_ambiguous",
      production_mock_mode: "local_only",
    },
    data_retention: "local test data",
    consent_policy: "visible per case",
    capabilities,
    pipeline_settings,
  };
  const supabase = {
    ...mock,
    mock_mode: false,
    auth_mode: "supabase",
    access_model: {
      ...mock.access_model,
      production_mock_mode: "forbidden",
    },
  };
  return {
    runtimeSettingsState: {
      current: { status: "success", mode: "backend", data: mock },
    } as { current: Record<string, unknown> },
    mockRuntimeSettings: mock,
    supabaseRuntimeSettings: supabase,
  };
});

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => runtimeSettingsState.current,
}));

beforeEach(() => {
  runtimeSettingsState.current = { status: "success", mode: "backend", data: mockRuntimeSettings };
  window.sessionStorage.clear();
  routerPush.mockClear();
  vi.spyOn(console, "error").mockImplementation((...args) => {
    const [firstArg] = args;
    const message = typeof firstArg === "string" ? firstArg : "";
    if (
      message.includes("Not implemented: navigation (except hash changes)")
      || message.includes("not wrapped in act")
    ) {
      return;
    }
    originalConsoleError(...args);
  });
  vi.stubGlobal("fetch", vi.fn(async () => {
    throw new TypeError("Failed to fetch");
  }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const renderCaseDetailPage = (caseId = "case_demo_001") =>
  renderAsyncPage(CaseDetailPage, { params: { caseId } });

const renderSessionWorkspace = (
  view: "record" | "transcript" | "results",
  searchParams?: Record<string, string>,
) => render(
  <AppShell active="Session">
    <SessionWorkspaceClient
      sessionId={searchParams?.session_id}
      caseId={searchParams?.case_id}
      transcriptId={searchParams?.transcript_id}
      reportId={searchParams?.report_id}
      view={view}
      mode={searchParams?.mode}
    />
  </AppShell>,
);

const renderRecordPage = (searchParams?: Record<string, string>) =>
  renderSessionWorkspace("record", searchParams);

const renderResultsPage = (searchParams?: Record<string, string>) =>
  renderSessionWorkspace("results", searchParams);

const renderReviewTranscriptPage = (searchParams?: Record<string, string>) =>
  renderSessionWorkspace("transcript", searchParams);

const renderTranscriptAliasPage = () => renderSessionWorkspace("transcript");

const renderReportSummaryPage = (searchParams?: Record<string, string>) => render(
  <AppShell active="Reports">
    <ReportSummaryClient
      caseId={searchParams?.case_id}
      sessionId={searchParams?.session_id}
      transcriptId={searchParams?.transcript_id}
      reportId={searchParams?.report_id}
    />
  </AppShell>,
);

const renderSettingsPage = (searchParams?: Record<string, string>) =>
  searchParams
    ? renderAsyncPage(SettingsPage, { searchParams })
    : renderAsyncPage(SettingsPage);

describe("lingualens pages", () => {
  it("routes mock login by selected role without browser storage", () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/settings")) {
        return jsonResponse({
          mock_mode: true,
          auth_mode: "mock",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "local_only",
          },
        });
      }
      return jsonResponse({});
    }));

    render(<LoginPage />);
    const enterWorkspace = screen.getByRole("link", { name: "Enter workspace" });
    expect(enterWorkspace).toHaveAttribute("href", "/today?role=therapist");
    expect(screen.getByText("Clinical transcript workbench")).toBeInTheDocument();
    expect(screen.getByText("Production access stays invitation-only and requires AAL2 before app access.")).toBeInTheDocument();
    expect(screen.getByText("This mock role has a single organization membership, so the active organization is preselected.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "clinical_supervisor" } });
    expect(enterWorkspace).toHaveAttribute("href", "/today?role=clinical_supervisor");
    expect(screen.getByText("Clinical supervisor opens the work queue with org-wide oversight.")).toBeInTheDocument();
    expect(screen.getByText("This mock role simulates multiple memberships, so the active organization must be selected explicitly before workspace access.")).toBeInTheDocument();
    expect(screen.getByText("Organization session selection").parentElement).toHaveTextContent(
      "Selecting AAL1 will stop at the MFA gate until the session is promoted to AAL2.",
    );

    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "org_admin" } });

    expect(enterWorkspace).toHaveAttribute("href", "/settings?scope=admin&role=org_admin");
    expect(screen.getByText("Org admin opens assignment-safe runtime controls.")).toBeInTheDocument();
  });

  it("renders the Supabase login scaffold when runtime auth mode is supabase", async () => {
    runtimeSettingsState.current = { status: "success", mode: "backend", data: supabaseRuntimeSettings };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
        });
      }
      if (url.includes("/organizations/current/memberships")) {
        return jsonResponse([]);
      }
      if (url.includes("/organizations/current/invitations")) {
        return jsonResponse([]);
      }
      return jsonResponse({});
    }));

    render(<LoginPage />);

    expect(await screen.findByRole("heading", { name: "Secure sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Enter workspace" })).not.toBeInTheDocument();
    expect(screen.getByText("Public signup is off. Only users with an accepted invitation can continue to account access.")).toBeInTheDocument();
    expect(screen.getByText(/After invitation acceptance, TOTP MFA enrollment is mandatory\./)).toBeInTheDocument();
    expect(screen.getByText(/If multiple memberships are active, the user must explicitly choose one organization before workspace access\./)).toBeInTheDocument();
    expect(screen.getByText(/Password recovery uses the Supabase-managed reset path/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Supabase browser config missing" })).toBeDisabled();
  });

  it("persists the selected active organization session from mock login", () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/settings")) {
        return jsonResponse({
          mock_mode: true,
          auth_mode: "mock",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "local_only",
          },
        });
      }
      return jsonResponse({});
    }));

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "clinical_supervisor" } });
    fireEvent.change(screen.getByLabelText("Active organization session"), { target: { value: "pilot_org_002" } });
    fireEvent.click(screen.getByRole("link", { name: "Enter workspace" }));

    expect(window.sessionStorage.getItem("lingualens.mock-access-session.v1")).toContain("pilot_org_002");
  });

  it("shows the MFA gate instead of workspace content for an aal1 mock session", () => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "clinical_supervisor",
      organizationId: "pilot_org_002",
      aal: "aal1",
    }));

    render(<TodayPage />);

    expect(screen.getByRole("heading", { name: "Additional verification required" })).toBeInTheDocument();
    expect(screen.getByText("Invitation-only onboarding and AAL2 are required before clinical or admin workflow access.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Start session" })).not.toBeInTheDocument();
  });

  it("blocks workspace routes behind the supabase sign-in gate when no session is present", async () => {
    runtimeSettingsState.current = { status: "success", mode: "backend", data: supabaseRuntimeSettings };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
        });
      }
      if (url.includes("/organizations/current/memberships")) {
        return jsonResponse([]);
      }
      if (url.includes("/organizations/current/invitations")) {
        return jsonResponse([]);
      }
      return jsonResponse({});
    }));

    render(<TodayPage />);

    expect(await screen.findByRole("heading", { name: "Workspace access is blocked" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to login" })).toHaveAttribute("href", "/login");
    expect(screen.queryByRole("link", { name: "Start session" })).not.toBeInTheDocument();
  });

  it("blocks workspace routes behind the supabase MFA gate for an aal1 session", async () => {
    runtimeSettingsState.current = { status: "success", mode: "backend", data: supabaseRuntimeSettings };
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      aal: "aal1",
      appMetadata: {
        role: "therapist",
        membership_active: true,
        invitation_status: "accepted",
        organization_id: "clinic_001",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic" },
        ],
      },
    }));

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
        });
      }
      return jsonResponse({});
    }));

    render(<TodayPage />);

    expect(await screen.findByRole("heading", { name: "Additional verification required" })).toBeInTheDocument();
    expect(screen.getByText(/Complete the Supabase TOTP step below to elevate this session to/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start TOTP enrollment" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Start session" })).not.toBeInTheDocument();
  });

  it("requires explicit organization selection before supabase workspace access when memberships are ambiguous", async () => {
    runtimeSettingsState.current = { status: "success", mode: "backend", data: supabaseRuntimeSettings };
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_supervisor_001",
      email: "supervisor@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "clinical_supervisor",
        membership_active: true,
        invitation_status: "accepted",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic" },
          { organizationId: "clinic_002", label: "North Review Clinic" },
        ],
      },
    }));

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
        });
      }
      return jsonResponse({});
    }));

    render(<TodayPage />);

    expect(await screen.findByRole("heading", { name: "Choose an active organization" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Select active organization"), {
      target: { value: "clinic_002" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue with selected organization" }));

    await waitFor(() => {
      expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"stage\":\"authenticated\"");
      expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"organizationId\":\"clinic_002\"");
    });

    cleanup();
    render(<TodayPage />);

    expect(await screen.findByRole("link", { name: "Start session" })).toHaveAttribute("href", "/cases?intent=start-session");
  });

  it("opens the supabase workspace without selection when exactly one membership is active", async () => {
    runtimeSettingsState.current = { status: "success", mode: "backend", data: supabaseRuntimeSettings };
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "therapist",
        membership_active: true,
        invitation_status: "accepted",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic" },
        ],
      },
    }));

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
        });
      }
      return jsonResponse({});
    }));

    render(<TodayPage />);

    expect(await screen.findByRole("link", { name: "Start session" })).toHaveAttribute("href", "/cases?intent=start-session");
    expect(screen.queryByRole("heading", { name: "Choose an active organization" })).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"organizationId\":\"clinic_001\"");
  });

  it("allows the mock MFA gate to promote the session to aal2 and restore workspace access", async () => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "org_admin",
      organizationId: "pilot_org_ops",
      aal: "aal1",
    }));

    await renderSettingsPage({ scope: "admin" });

    fireEvent.click(screen.getByRole("button", { name: "Complete mock MFA" }));

    expect(await screen.findByRole("heading", { name: "Team" })).toBeInTheDocument();
    expect(window.sessionStorage.getItem("lingualens.mock-access-session.v1")).toContain("\"aal\":\"aal2\"");
  });

  it("keeps the org-admin settings route behind the Supabase MFA gate for an aal1 session", async () => {
    runtimeSettingsState.current = { status: "success", mode: "backend", data: supabaseRuntimeSettings };
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_org_admin_001",
      email: "admin@clinic.example",
      aal: "aal1",
      appMetadata: {
        role: "org_admin",
        membership_active: true,
        invitation_status: "accepted",
        organization_id: "clinic_001",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic", role: "org_admin" },
        ],
      },
    }));

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
        });
      }
      return jsonResponse({});
    }));

    await renderSettingsPage({ scope: "admin" });

    expect(await screen.findByRole("heading", { name: "Additional verification required" })).toBeInTheDocument();
    expect(screen.getByText(/Complete the Supabase TOTP step below to elevate this session to/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Team" })).not.toBeInTheDocument();
  });

  it("keeps the org-admin settings route behind explicit organization selection when memberships are ambiguous", async () => {
    runtimeSettingsState.current = { status: "success", mode: "backend", data: supabaseRuntimeSettings };
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_org_admin_001",
      email: "admin@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "org_admin",
        membership_active: true,
        invitation_status: "accepted",
        organizations: [
          { organizationId: "clinic_001", label: "LinguaLens Clinic", role: "org_admin" },
          { organizationId: "clinic_002", label: "North Review Clinic", role: "org_admin" },
        ],
      },
    }));

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
        });
      }
      return jsonResponse({});
    }));

    await renderSettingsPage({ scope: "admin" });

    expect(await screen.findByRole("heading", { name: "Choose an active organization" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Team" })).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Select active organization"), {
      target: { value: "clinic_002" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue with selected organization" }));

    expect(await screen.findByRole("heading", { name: "Team" })).toBeInTheDocument();
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"organizationId\":\"clinic_002\"");
  });

  it("renders the backend-confirmed focused queue without legacy quick actions", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases")) {
        return jsonResponse([
          {
            case_id: "case_demo_001",
            child_code: "C-1024",
            consent_status: "granted",
            language: "Thai / English",
            review_priority: "high",
            latest_session_date: "2026-07-18",
            latest_session_status: "Needs Review",
            latest_report_status: "Draft",
          },
          {
            case_id: "case_demo_002",
            child_code: "C-1031",
            consent_status: "granted",
            language: "Thai",
            review_priority: "moderate",
            latest_session_date: "2026-07-19",
            latest_session_status: "Processing",
            latest_report_status: "Draft",
          },
        ]);
      }
      if (url.endsWith("/reports")) return jsonResponse([]);
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<TodayPage />);

    expect(await screen.findByRole("heading", { name: "Prioritized queue" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ready for review" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Processing" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Today context" }).length).toBeGreaterThan(0);

    expect(screen.getByRole("link", { name: "Start session" })).toHaveAttribute("href", "/cases?intent=start-session");
    expect(screen.queryByRole("heading", { name: "Quick Actions" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Upload audio|Upload \.cha|Paste transcript/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Workflow status is operational and does not imply a clinical conclusion/)).toBeInTheDocument();
  });

  it("keeps an empty focused workbench honest and free of sample queue sections", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases") || url.endsWith("/reports")) return jsonResponse([]);
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<TodayPage />);
    expect(screen.getByRole("link", { name: "Start session" })).toHaveAttribute("href", "/cases?intent=start-session");
    expect(await screen.findByText("No work requires attention right now.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Today's sessions" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Recent results" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Today's Agenda" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Ava M\.|Ethan L\.|Jacob W\./)).not.toBeInTheDocument();
    expect(screen.queryByText(/demo fallback/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Workflow status is operational and does not imply a clinical conclusion/)).toBeInTheDocument();
  });

  it("recovers Today after a backend retry without showing sample success", async () => {
    let caseAttempts = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases")) {
        caseAttempts += 1;
        if (caseAttempts === 1) return jsonResponse({ detail: "temporarily unavailable" }, { status: 503 });
        return jsonResponse([{
          case_id: "case_retry_001",
          child_code: "C-RETRY",
          consent_status: "granted",
          language: "Thai",
          latest_session_date: "2026-07-19",
          latest_session_status: "Needs Review",
          latest_report_status: "Draft",
        }]);
      }
      if (url.endsWith("/reports")) return jsonResponse([]);
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<TodayPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Today’s queue is unavailable");
    expect(screen.getByText("Backend unavailable")).toBeInTheDocument();
    expect(screen.queryByText("C-RETRY")).not.toBeInTheDocument();
    expect(screen.queryByText(/demo fallback/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry work queue" }));

    expect((await screen.findAllByText("C-RETRY")).length).toBeGreaterThan(0);
    expect(screen.getByText("Backend confirmed")).toBeInTheDocument();
    expect(caseAttempts).toBe(2);
  });

  it("renders case cards with consent and session context", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/cases")) {
        return jsonResponse([{
          case_id: "case_demo_001",
          child_code: "C-1024",
          nickname: "Demo child",
          age_months: 62,
          language: "English",
          consent_status: "granted",
          latest_session_date: "2026-06-12",
          latest_session_status: "Needs Review",
          latest_report_status: "Draft",
          care_team_user_ids: ["therapist-demo"],
        }]);
      }
      throw new Error(`Unexpected request: ${String(input)}`);
    }));

    await renderAsyncPage(CasesPage);
    expect(await screen.findByRole("heading", { name: "Cases" })).toBeInTheDocument();
    expect(await screen.findByRole("searchbox", { name: "Search cases" })).toBeInTheDocument();
    expect(await screen.findByRole("columnheader", { name: "Latest activity" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Workflow status" })).toBeInTheDocument();
    expect(screen.getByText(/Granted consent ·/)).toBeInTheDocument();
    expect(screen.getAllByText("Demo child").length).toBeGreaterThan(0);
  });

  it("keeps existing case detail workflow available", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases/case_demo_001")) {
        return jsonResponse({
          case_id: "case_demo_001",
          child_code: "C-1024",
          nickname: "Demo child",
          age_months: 62,
          language: "English",
          consent_status: "granted",
          latest_session_date: "2026-06-12",
          latest_session_status: "Needs Review",
          latest_report_status: "Draft",
          care_team_user_ids: ["therapist-demo"],
          primary_therapist_user_id: "therapist-demo",
        });
      }
      if (url.endsWith("/cases/case_demo_001/timeline") || url.endsWith("/cases/case_demo_001/goals")) {
        return jsonResponse([]);
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    await renderCaseDetailPage();
    expect(await screen.findByRole("heading", { name: "Demo child" })).toBeInTheDocument();
    expect(await screen.findByText("Consent status")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Create new session" })).toHaveAttribute("href", "/cases?intent=start-session");
  });

  it("shows a safe read-only care-team summary on case detail", async () => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "org_admin",
      organizationId: "pilot_org_ops",
      aal: "aal2",
    }));
    let careTeamAssignments = [
      {
        assignment_id: "team_001",
        organization_id: "pilot_org_001",
        case_id: "case_demo_001",
        user_id: "therapist-demo",
        role: "therapist",
        active: true,
        is_primary: true,
      },
      {
        assignment_id: "team_002",
        organization_id: "pilot_org_001",
        case_id: "case_demo_001",
        user_id: "clinician_b",
        role: "therapist",
        active: true,
        is_primary: false,
      }
    ];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases")) {
        return jsonResponse([
          {
            case_id: "case_demo_001",
            child_code: "C-1024",
            nickname: "Demo child",
            age_months: 62,
            language: "English",
            consent_status: "granted",
            latest_session_date: "2026-06-12",
            latest_session_status: "Needs Review",
            latest_report_status: "Draft",
            care_team_user_ids: ["therapist-demo", "clinician_b"],
            primary_therapist_user_id: "therapist-demo",
          }
        ]);
      }
      if (url.endsWith("/cases/case_demo_001")) {
        return jsonResponse({
          case_id: "case_demo_001",
          child_code: "C-1024",
          nickname: "Demo child",
          age_months: 62,
          language: "English",
          consent_status: "granted",
          latest_session_date: "2026-06-12",
          latest_session_status: "Needs Review",
          latest_report_status: "Draft",
          care_team_user_ids: ["therapist-demo", "clinician_b"],
          primary_therapist_user_id: "therapist-demo",
        });
      }
      if (url.endsWith("/cases/case_demo_001/timeline")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/cases/case_demo_001/goals")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/cases/case_demo_001/care-team") && (!init?.method || init.method === "GET")) {
        return jsonResponse(careTeamAssignments);
      }
      if (url.endsWith("/organizations/current/memberships")) {
        const headers = new Headers(init?.headers);
        expect(headers.get("X-Mock-Role")).toBe("org_admin");
        expect(headers.get("X-Organization-Id")).toBe("pilot_org_ops");
        return jsonResponse([
          {
            membership_id: "mbr_001",
            organization_id: "pilot_org_001",
            user_id: "therapist-demo",
            display_name: "Demo Therapist",
            role: "therapist",
            active: true,
          },
          {
            membership_id: "mbr_002",
            organization_id: "pilot_org_001",
            user_id: "clinician_b",
            display_name: "Clinician B",
            role: "therapist",
            active: true,
          },
          {
            membership_id: "mbr_003",
            organization_id: "pilot_org_001",
            user_id: "supervisor_a",
            display_name: "Supervisor A",
            role: "clinical_supervisor",
            active: true,
          }
        ]);
      }
      if (url.endsWith("/cases/case_demo_001/care-team") && init?.method === "POST") {
        const body = JSON.parse(String(init.body ?? "{}"));
        const headers = new Headers(init?.headers);
        expect(headers.get("X-Organization-Id")).toBe("pilot_org_ops");
        const nextActive = body.active ?? true;
        const nextPrimary = body.is_primary ?? false;
        const existingAssignment = careTeamAssignments.find((assignment) => assignment.user_id === body.user_id);
        const updatedAssignment = {
          assignment_id: existingAssignment?.assignment_id ?? `team_${body.user_id}`,
          organization_id: "pilot_org_001",
          case_id: "case_demo_001",
          user_id: body.user_id,
          role: body.role ?? existingAssignment?.role ?? "therapist",
          active: nextActive,
          is_primary: nextPrimary,
        };

        if (nextPrimary) {
          careTeamAssignments = careTeamAssignments.map((assignment) => ({
            ...assignment,
            is_primary: assignment.user_id === body.user_id,
          }));
        }

        if (existingAssignment) {
          careTeamAssignments = careTeamAssignments.map((assignment) => (
            assignment.user_id === body.user_id ? updatedAssignment : assignment
          ));
        } else {
          careTeamAssignments = [...careTeamAssignments, updatedAssignment];
        }

        return jsonResponse(updatedAssignment);
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderCaseDetailPage();

    const careTeamCard = (await screen.findByRole("heading", { name: "Care team" })).closest("section");
    expect(careTeamCard).not.toBeNull();
    expect(within(careTeamCard as HTMLElement).getByText("Demo Therapist")).toBeInTheDocument();
    expect(within(careTeamCard as HTMLElement).getByText(/read-only care-team summary/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Make primary therapist" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove assignment" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/care-team"))).toBe(false);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/organizations/current/memberships"))).toBe(false);
  });

  it("renders the session intake screen", async () => {
    await renderRecordPage();
    expect(await screen.findByRole("heading", { name: "Session Intake" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Session Details" })).toBeInTheDocument();
    expect(screen.getAllByText("Source Material").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Transcript Setup").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Review & Start").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Child or client")).toBeInTheDocument();
    expect(screen.getByLabelText("Session date")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue to Source Material" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Extract language-sample features" })).toBeInTheDocument();
    expect(screen.getByText("Decision-support only. Not diagnostic. Transcript must be reviewed before report use.")).toBeInTheDocument();
  });

  it.each([
    ["record", async () => await renderRecordPage()],
    ["results", async () => await renderResultsPage()],
    ["review transcript", async () => await renderReviewTranscriptPage()],
    ["report summary", async () => await renderReportSummaryPage()]
  ])("shows explicit local workspace mode on %s when the backend is unreachable", async (_name, renderPage) => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    await renderPage();

    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    expect(screen.getByText("Changes are stored locally only and may not persist across devices or server restarts.")).toBeInTheDocument();
  });

  it("keeps safe local demo input available while backend-required actions remain gated offline", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    await renderRecordPage({ mode: "paste" });

    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Pasted transcript text" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Extract language-sample features" })).toBeDisabled();
  });

  it("shows a useful empty result state with a working next action", async () => {
    await renderResultsPage();
    expect(await screen.findByRole("heading", { name: "No analysis results yet" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Record or add a transcript" })).toHaveAttribute("href", "/cases?intent=start-session");
  });

  it("keeps browser recording unavailable in the v1.7.0 testbed", async () => {
    const getUserMedia = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia },
    });

    await renderRecordPage();
    fireEvent.change(screen.getByLabelText("Child or client"), { target: { value: "Synthetic case" } });
    fireEvent.change(screen.getByLabelText("Clinician"), { target: { value: "Therapist Demo" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));
    fireEvent.click(screen.getByRole("button", { name: "Record in browser" }));

    expect(await screen.findByText("Experimental — unavailable in v1.7.0 testbed", { exact: false })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start recording" })).not.toBeInTheDocument();
    expect(getUserMedia).not.toHaveBeenCalled();
  });

  it("uses verified synthetic audio upload as the milestone audio entry point", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/audio/capabilities")) {
        return jsonResponse({
          processing_state: "available",
          max_duration_seconds: 900,
          max_size_bytes: 100 * 1024 * 1024,
          supported_formats: ["wav", "mp3"],
          browser_recording: { state: "experimental_unavailable" },
        });
      }
      throw new TypeError("Failed to fetch");
    }));

    await renderRecordPage();
    fireEvent.change(screen.getByLabelText("Child or client"), { target: { value: "Synthetic case" } });
    fireEvent.change(screen.getByLabelText("Clinician"), { target: { value: "Therapist Demo" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to Source Material" }));
    fireEvent.click(screen.getByRole("button", { name: "Upload audio" }));

    expect(await screen.findByLabelText("Synthetic audio file")).toBeEnabled();
    expect(screen.getByText(/15 minutes/)).toBeInTheDocument();
    expect(screen.getByText(/100 MB/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upload for transcription" })).not.toBeInTheDocument();
  });

  it("restores the active workflow session after a page refresh", async () => {
    const saved = saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local_persisted_session",
      sessionCreatedAt: "2026-06-18T08:00:00.000Z",
      childName: "Persisted client",
      caseInfo: {
        caseId: "case_persisted",
        clientLabel: "Persisted client"
      },
      source: "paste-transcript",
      transcriptText: "@Begin\n*CHI:\thello .\n@End",
      transcriptReady: true,
      transcriptReviewStatus: "draft",
      analysisStatus: "completed",
      reportStatus: "draft"
    });

    expect(loadWorkflowState()).toEqual(saved);

    await renderResultsPage();
    await waitFor(() => {
      expect(screen.getAllByText("Persisted client").length).toBeGreaterThan(0);
    });
    expect(screen.getByRole("region", { name: "Findings provenance" })).toBeInTheDocument();
    expect(screen.getAllByText("Persisted client").length).toBeGreaterThan(0);
  });

  it("renders clean session results and transcript review routes", async () => {
    await renderResultsPage();
    expect((await screen.findAllByRole("heading", { name: "Session Results" })).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "No analysis results yet" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review Transcript" })).toHaveAttribute("href", "/cases?intent=start-session");
    expect(screen.getByRole("button", { name: "Generate Report" })).toBeDisabled();

    cleanup();
    await renderReviewTranscriptPage();
    expect(screen.getByRole("heading", { name: "Review Transcript" })).toBeInTheDocument();
    expect(screen.getByText("Confirm speaker labels and transcript quality before report generation.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run QA" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Attest transcript" })).toBeInTheDocument();

    cleanup();
    await renderTranscriptAliasPage();
    expect(screen.getByRole("heading", { name: "Review Transcript" })).toBeInTheDocument();
  });

  it("keeps report generation locked until transcript attestation", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      transcriptReady: true,
      transcriptReviewStatus: "in_review",
      transcriptAttested: false,
      transcriptLines: [{ lineId: "line-1", speaker: "CHI", text: "I see it." }]
    });

    await renderReportSummaryPage();
    await waitFor(() => expect(screen.getByText("Transcript review and attestation are required before report generation.")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Generate draft" })).toBeDisabled();
  });

  it("labels ASR output as a draft and keeps review actions required", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      source: "recording",
      transcriptText: "@Begin\n*UNK:\tMock ASR output.\n@End",
      transcriptLines: [{ lineId: "line-1", speaker: "UNK", text: "Mock ASR output." }],
      transcriptReady: true,
      transcriptReviewStatus: "draft",
      transcriptAttested: false,
      transcriptDraftLabel: "Draft transcript — therapist review required.",
      transcriptionJobStatus: "completed"
    });

    await renderReviewTranscriptPage();
    await waitFor(() => {
      expect(screen.getByText("Draft transcript — therapist review required.")).toBeInTheDocument();
    });
    expect(screen.getByText("Experimental ASR can be inaccurate. Verify wording, timestamps, and speaker labels before attestation.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate Report" })).toBeDisabled();
  });

  it("warns when feature extraction is locked before attestation", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-unattested",
      source: "paste-transcript",
      transcriptReady: true,
      transcriptReviewStatus: "in_review",
      transcriptAttested: false,
      transcriptLines: [{ lineId: "line-1", speaker: "CHI", text: "I see it." }]
    });

    await renderRecordPage();
    await waitFor(() => {
      expect(screen.getByText("Feature extraction requires a saved, reviewed, and attested transcript.")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Extract language-sample features" })).toBeDisabled();
  });

  it("shows extracted language-sample cues on results without prediction claims", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/transcripts/TRANSCRIPT-REVIEWED/extract-features")) {
        return jsonResponse({ features: [
          { name: "total_utterance_count", value: 3 },
          { name: "mean_length_of_utterance_words", value: 3.5 },
          { name: "number_of_different_words", value: 8 },
          { name: "question_ratio", value: 0.2 }
        ] });
      }
      return jsonResponse({});
    }));
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-reviewed",
      backendSessionId: "SESSION-REVIEWED",
      backendTranscriptSessionId: "SESSION-REVIEWED",
      backendTranscriptId: "TRANSCRIPT-REVIEWED",
      source: "paste-transcript",
      transcriptReady: true,
      transcriptReviewStatus: "reviewed",
      transcriptAttested: true,
      qaStatus: "pass",
      transcriptLines: [
        { lineId: "line-1", speaker: "THER", text: "What do you see?" },
        { lineId: "line-2", speaker: "CHI", text: "I see a blue car." },
        { lineId: "line-3", speaker: "CHI", text: "Blue car car." }
      ]
    });

    await renderRecordPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Extract language-sample features" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Extract language-sample features" }));
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith(expect.stringMatching(/^\/sessions\/.+\?view=findings/)));

    cleanup();
    await renderResultsPage();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Linguistic Signals" })).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Workflow summary" })).toBeInTheDocument();
    expect(screen.getByText("Transcript quality")).toBeInTheDocument();
    expect(screen.getByText("Features extracted")).toBeInTheDocument();
    expect(screen.getByText("Review flags")).toBeInTheDocument();
    expect(screen.getByText("Report readiness")).toBeInTheDocument();
    expect(screen.getByText("Interpret descriptive cues in context; limitations remain attached to each feature.")).toBeInTheDocument();
  });

  it("renders linguistic signal cards from backend feature definitions with a safety rail", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-EVIDENCE")) {
        return jsonResponse({
          session_id: "SESSION-EVIDENCE",
          case_id: "CASE-EVIDENCE",
          transcript_id: "TRANSCRIPT-EVIDENCE",
          feature_set_id: "FEATURES-EVIDENCE"
        });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-EVIDENCE")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-EVIDENCE",
          session_id: "SESSION-EVIDENCE",
          case_id: "CASE-EVIDENCE",
          raw_text: "@Begin\n*CHI:\tI see the ball.\n@End",
          utterances: [
            { utterance_id: "utt-1", speaker: "CHI", text: "I see the ball." }
          ],
          qa_status: "PASS",
          therapist_attested: true
        });
      }
      if (url.endsWith("/cases/CASE-EVIDENCE")) {
        return jsonResponse({ case_id: "CASE-EVIDENCE", nickname: "Ethan L." });
      }
      if (url.endsWith("/sessions/SESSION-EVIDENCE/audio")) {
        return jsonResponse([]);
      }
      if (url.includes("/ml-readiness")) {
        return jsonResponse({
          ready: true,
          provider_id: "reference_evidence_review",
          reason_codes: [],
          reasons: []
        });
      }
      if (url.endsWith("/sessions/SESSION-EVIDENCE/ml-review")) {
        return jsonResponse({
          result_id: "MLR-EVIDENCE",
          status: "completed",
          provider_name: "ReferenceEvidenceProvider",
          provider_version: "0.9.0",
          input_feature_schema_version: "features-basic-v1",
          generated_at: "2026-06-20T00:00:00Z",
          cues: [
            {
              cue_code: "quality_follow_up",
              title: "Check question scaffolding",
              severity: "review",
              explanation: "Question-turn balance may affect interpretation.",
              supporting_features: { question_ratio: 0.15 },
              limitations: ["Review with transcript context."],
              recommended_next_review_step: "Confirm turn-taking context before drafting the report.",
              review_state: { status: "unreviewed" }
            }
          ],
          pattern_evidence: {
            status: "not_available",
            availability: {
              state: "system_unavailable",
              message: "Additional pattern evidence remains research-only.",
              workflow_can_continue: true,
              next_step: "Continue therapist review."
            },
            associated_features: [],
            review_state: { status: "unreviewed", therapist_note: "" }
          },
          profile_evidence: [],
          artifact_provenance: {},
          limitations: ["Reference evidence is descriptive and therapist-reviewed."],
          not_diagnostic: true,
          decision_support_only: true
        });
      }
      if (url.endsWith("/sessions/SESSION-EVIDENCE/features")) {
        return jsonResponse({
          feature_set_id: "FEATURES-EVIDENCE",
          schema_version: "features-basic-v1",
          therapist_attested: true,
          insufficient_data: false,
          features: [
            {
              name: "mean_length_of_utterance_words",
              value: 3.2,
              value_type: "float",
              unit: "words per utterance",
              interpretation_hint: "Descriptive language sample value; therapist interpretation required."
            },
            {
              name: "question_ratio",
              value: 0.15,
              value_type: "ratio",
              unit: "ratio",
              interpretation_hint: "Descriptive language sample value; therapist interpretation required."
            }
          ]
        });
      }
      if (url.endsWith("/features/definitions")) {
        return jsonResponse([
          {
            feature_name: "mean_length_of_utterance_words",
            display_name: "MLU (Words)",
            description: "Mean number of word tokens per child utterance.",
            value_type: "float",
            unit: "words per utterance",
            calculation_method: "total_word_count / child_utterance_count",
            required_inputs: ["utterances"],
            limitations: ["Word-based MLU only."],
            clinical_interpretation_caution: "Descriptive only; therapist interpretation required.",
            provider_name: "BasicFeatureProvider",
            provider_id: "basic_feature_provider"
          },
          {
            feature_name: "question_ratio",
            display_name: "Question Ratio (Child)",
            description: "Proportion of child utterances containing a question mark.",
            value_type: "ratio",
            unit: "ratio",
            calculation_method: "count(child utterances with '?') / child_utterance_count",
            required_inputs: ["utterances"],
            limitations: ["Punctuation-based heuristic only."],
            clinical_interpretation_caution: "Descriptive only; therapist interpretation required.",
            provider_name: "BasicFeatureProvider",
            provider_id: "basic_feature_provider"
          }
        ]);
      }
      return jsonResponse({});
    }));

    await renderResultsPage({ case_id: "CASE-EVIDENCE", session_id: "SESSION-EVIDENCE", transcript_id: "TRANSCRIPT-EVIDENCE" });

    expect(await screen.findByRole("heading", { name: "Linguistic Signals" })).toBeInTheDocument();
    expect(screen.getByText("MLU (Words)")).toBeInTheDocument();
    expect(screen.getByText("Question Ratio (Child)")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Safety & limitations" })).toBeInTheDocument();
    expect(screen.getByText("Therapist-editable interpretation draft")).toBeInTheDocument();
    expect(screen.getByText("Recommended review points")).toBeInTheDocument();
    expect(screen.getByText("Interpret descriptive cues in context; limitations remain attached to each feature.")).toBeInTheDocument();
  });

  it("shows a missing reference data state on the evidence review screen", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-missing-reference",
      backendSessionId: "SESSION-MISSING-REFERENCE",
      backendTranscriptSessionId: "SESSION-MISSING-REFERENCE",
      backendTranscriptId: "TRANSCRIPT-MISSING-REFERENCE",
      transcriptReady: true,
      transcriptReviewStatus: "reviewed",
      transcriptAttested: true,
      analysisStatus: "completed",
      featuresExtracted: true,
      featurePercent: 88,
      featureSummary: [
        { label: "MLU words", value: "3.2" }
      ],
      mlDecisionSupport: {
        resultId: "MLR-REF-MISSING",
        status: "completed",
        providerName: "ReferenceEvidenceProvider",
        providerVersion: "0.9.0",
        featureSchemaVersion: "features-basic-v1",
        generatedAt: "2026-06-20T00:00:00Z",
        cues: [],
        patternEvidence: {
          status: "not_available",
          availability: {
            state: "insufficient_reference_data",
            reasonCode: "insufficient_participants",
            message: "This public-corpus profile does not have enough independent participants.",
            workflowCanContinue: true
          },
          associatedFeatures: [],
          reviewState: { status: "unreviewed", therapistNote: "" }
        },
        profileEvidence: [
          {
            profileCode: "ASD",
            presentationGroup: "ASD",
            status: "not_available",
            availability: {
              state: "insufficient_reference_data",
              reasonCode: "insufficient_participants",
              message: "This public-corpus profile does not have enough independent participants.",
              workflowCanContinue: true
            },
            participantCount: 17,
            corpusCount: 1,
            associatedFeatures: [],
            reviewState: { status: "unreviewed", therapistNote: "" }
          }
        ],
        artifactProvenance: {},
        limitations: ["Reference evidence remains descriptive only."],
        notDiagnostic: true,
        decisionSupportOnly: true
      }
    });

    await renderResultsPage();

    expect(await screen.findByText("Reference comparison unavailable")).toBeInTheDocument();
  });

  it("blocks report draft generation on results until readiness gates pass", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-results-gate",
      backendSessionId: "SESSION-RESULTS-GATE",
      backendTranscriptSessionId: "SESSION-RESULTS-GATE",
      backendTranscriptId: "TRANSCRIPT-RESULTS-GATE",
      transcriptReady: true,
      transcriptReviewStatus: "reviewed",
      transcriptAttested: true,
      featuresExtracted: false,
      featurePercent: 0,
      featureSummary: [],
      mlReadiness: {
        ready: false,
        providerId: "reference_evidence_review",
        reasonCodes: ["features_missing"],
        reasons: ["Feature extraction has not been completed."]
      }
    });

    await renderResultsPage();

    expect((await screen.findAllByText("Therapist-reviewed transcript and feature extraction are required before generating a draft report. ML evidence review remains optional.")).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Generate report draft" })).toBeDisabled();
  });

  it("keeps report draft generation available when ML readiness is unavailable but transcript review and features are complete", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-results-ml-optional",
      backendSessionId: "SESSION-RESULTS-ML-OPTIONAL",
      backendTranscriptSessionId: "SESSION-RESULTS-ML-OPTIONAL",
      backendTranscriptId: "TRANSCRIPT-RESULTS-ML-OPTIONAL",
      transcriptReady: true,
      transcriptReviewStatus: "reviewed",
      transcriptAttested: true,
      analysisStatus: "completed",
      featuresExtracted: true,
      featurePercent: 100,
      featureSummary: [
        { label: "Child Utterance Count", value: "3" },
      ],
      mlReadiness: {
        ready: false,
        providerId: "reference_evidence_review",
        reasonCodes: ["provider_unavailable"],
        reasons: ["Backend readiness verification is pending."],
      },
    });

    await renderResultsPage();

    expect(await screen.findByText("Report readiness")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate report draft" })).toBeEnabled();
  });

  it("renders independent pattern and reference evidence without scores or ranking", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/settings")) {
        return jsonResponse({ repository_mode: "memory" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-ML/ml-review")) {
        return jsonResponse({
          result_id: "MLR-1",
          status: "completed",
          provider_name: "ReferenceEvidenceProvider",
          provider_version: "0.9.0",
          input_feature_schema_version: "features-basic-v0.7",
          generated_at: "2026-06-20T00:00:00Z",
          cues: [],
          pattern_evidence: {
            status: "not_available",
            availability: {
              state: "system_unavailable",
              reason_code: "gate1_research_only",
              message: "Additional pattern evidence remains research-only.",
              workflow_can_continue: true,
              next_step: "Continue transcript and feature review."
            },
            associated_features: [],
            review_state: { status: "unreviewed", therapist_note: "" }
          },
          profile_evidence: [
            {
              profile_code: "TD",
              presentation_group: "TD",
              status: "comparable_patterns_observed",
              availability: {
                state: "available",
                message: "A descriptive comparison is available.",
                workflow_can_continue: true
              },
              participant_count: 32,
              corpus_count: 2,
              associated_features: [
                { feature_name: "total_words", observed_value: 24, position: "above_iqr", q1: 10, median: 14, q3: 18, caveat: "Interpret with transcript context." },
                { feature_name: "mluw", observed_value: 3.4, position: "above_iqr", q1: 1.8, median: 2.2, q3: 2.8, caveat: "Interpret with transcript context." },
                { feature_name: "question_ratio", observed_value: 0.12, position: "below_iqr", q1: 0.2, median: 0.3, q3: 0.4, caveat: "Interpret with transcript context." }
              ],
              review_state: { status: "unreviewed", therapist_note: "" }
            },
            {
              profile_code: "DD",
              presentation_group: "DD",
              status: "limited_comparison",
              availability: {
                state: "available",
                reason_code: "mapped_feature_subset_only",
                message: "A limited descriptive comparison is available.",
                workflow_can_continue: true
              },
              participant_count: 25,
              corpus_count: 2,
              associated_features: [
                { feature_name: "ttr", observed_value: 0.5, position: "above_iqr", q1: 0.2, median: 0.3, q3: 0.4, caveat: "Interpret with transcript context." },
                { feature_name: "total_utterances", observed_value: 8, position: "below_iqr", q1: 10, median: 12, q3: 14, caveat: "Interpret with transcript context." }
              ],
              review_state: { status: "unreviewed", therapist_note: "" }
            },
            {
              profile_code: "ASD",
              presentation_group: "ASD",
              status: "not_available",
              availability: {
                state: "insufficient_reference_data",
                reason_code: "insufficient_participants",
                message: "This profile does not have enough independent support.",
                workflow_can_continue: true
              },
              participant_count: 17,
              corpus_count: 1,
              associated_features: [],
              review_state: { status: "unreviewed", therapist_note: "" }
            }
          ],
          artifact_provenance: { artifact_version: "test-v1" },
          limitations: ["Descriptive public-corpus evidence only."],
          not_diagnostic: true,
          decision_support_only: true
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    }));
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-ml-support",
      backendTranscriptId: "TRANSCRIPT-ML",
      transcriptReady: true,
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      analysisStatus: "completed",
      featuresExtracted: true,
      featureSummary: [
        { label: "MLU words", value: "3.4" },
        { label: "Question ratio", value: "12%" },
        { label: "Repetition cue", value: "2" }
      ]
    });

    await renderResultsPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Generate evidence review" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Generate evidence review" }));

    expect(await screen.findByRole("heading", { name: "Recommended review points" })).toBeInTheDocument();
    expect(await screen.findByText(/Not diagnostic/i)).toBeInTheDocument();
    expect(screen.getByTestId("evidence-review-panel")).toBeInTheDocument();
    expect(screen.getByText("Comparable patterns observed")).toBeInTheDocument();
    expect(screen.getAllByText("Reference comparison unavailable").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("evidence-cue")).toHaveLength(3);
    fireEvent.click(screen.getByRole("button", { name: "View supporting evidence" }));
    expect(screen.getAllByTestId("evidence-detail")).toHaveLength(5);
    fireEvent.click(screen.getAllByRole("button", { name: "Record disagreement" })[0]);
    expect(screen.getByText("This records clinical disagreement and preserves the original provider output.")).toBeInTheDocument();
    const saveDisagreement = screen.getByRole("button", { name: "Save disagreement" });
    expect(saveDisagreement).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Disagreement note for TD"), {
      target: { value: "The interaction context does not support this comparison." }
    });
    expect(saveDisagreement).toBeEnabled();
    expect(screen.queryByText(/probability|predicted class|winner/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate report draft" })).toBeEnabled();
  });

  it("shows ML readiness locked until transcript attestation", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      transcriptReady: true,
      transcriptAttested: false,
      transcriptReviewStatus: "in_review",
      featuresExtracted: false
    });
    await renderResultsPage();
    expect(screen.getByText("Transcript attestation required")).toBeInTheDocument();
    expect(screen.queryByTestId("evidence-review-panel")).not.toBeInTheDocument();
  });

  it("does not fabricate or display ML cues when backend verification is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new Error("backend unavailable");
    }));
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendTranscriptId: "TRANSCRIPT-OFFLINE",
      transcriptReady: true,
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      analysisStatus: "completed",
      featuresExtracted: true,
      featureSummary: [{ label: "Child utterances", value: "4" }],
      mlDecisionSupport: {
        resultId: "STALE",
        status: "completed",
        providerName: "StaleProvider",
        providerVersion: "0",
        featureSchemaVersion: "stale",
        generatedAt: "2026-01-01T00:00:00Z",
        cues: [],
        profileEvidence: [],
        artifactProvenance: {},
        limitations: [],
        notDiagnostic: true,
        decisionSupportOnly: true
      }
    });
    await renderResultsPage();
    fireEvent.click(screen.getByRole("button", { name: "Generate evidence review" }));
    expect(await screen.findByText("ML review unavailable — backend verification required.")).toBeInTheDocument();
    expect(screen.queryByTestId("evidence-review-panel")).not.toBeInTheDocument();
    expect(screen.queryByText(/Local preview only/i)).not.toBeInTheDocument();
  });

  it("saves review edits, runs QA, attests, and extracts features before report generation unlocks", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/transcripts/TRANSCRIPT-REVIEW") && init?.method === "PATCH") {
        return jsonResponse({ transcript_id: "TRANSCRIPT-REVIEW", session_id: "SESSION-REVIEW", utterances: [] });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-REVIEW/qa")) {
        return jsonResponse({ overall_status: "warning", issues: [{ message: "Short transcript." }], transcript_id: "TRANSCRIPT-REVIEW" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-REVIEW/attest")) {
        return new Response(null, { status: 204 });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-REVIEW/extract-features")) {
        return jsonResponse({ feature_id: "FEATURE-REVIEW", features: { mean_length_of_utterance_words: 2.5, number_of_different_words: 4, question_ratio: "0%" } });
      }
      if (url.endsWith("/sessions/SESSION-REVIEW/reports/draft")) {
        return jsonResponse({ report_id: "REPORT-REVIEW", markdown: "# Draft", status: "Draft" });
      }
      return jsonResponse({});
    }));
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-review-session",
      backendSessionId: "SESSION-REVIEW",
      backendTranscriptSessionId: "SESSION-REVIEW",
      backendTranscriptId: "TRANSCRIPT-REVIEW",
      source: "paste-transcript",
      transcriptReady: true,
      transcriptReviewStatus: "draft",
      transcriptText: "@Begin\n*THER:\tHello.\n*CHI:\tHi.\n@End",
      transcriptLines: [
        { lineId: "line-1", speaker: "THER", text: "Hello." },
        { lineId: "line-2", speaker: "CHI", text: "Hi." }
      ],
      transcriptSaveStatus: "saved"
    });

    await renderReviewTranscriptPage();
    expect(screen.queryByRole("textbox", { name: "Reviewed transcript text" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate Report" })).toBeDisabled();
    expect(screen.getByText("Run transcript QA before generating a report.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Utterance text 2"), { target: { value: "Hi there." } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));

    await waitFor(() => {
      expect(loadWorkflowState()).toEqual(expect.objectContaining({
        transcriptReviewStatus: "in_review",
        transcriptAttested: false,
        transcriptLines: expect.arrayContaining([
          expect.objectContaining({ speaker: "CHI", text: "Hi there." })
        ])
      }));
    });

    await waitFor(() => expect(screen.getByRole("button", { name: "Run QA" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Run QA" }));
    await waitFor(() => expect(screen.getAllByText("Warning").length).toBeGreaterThan(0));
    await waitFor(() => expect(screen.getByRole("button", { name: "Attest transcript" })).toBeEnabled());
    expect(screen.getByText("Click Attest transcript before generating a report.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Attest transcript" }));

    await waitFor(() => expect(loadWorkflowState()).toEqual(expect.objectContaining({
        transcriptReviewStatus: "reviewed",
        transcriptAttested: true,
        transcriptLines: expect.arrayContaining([
          expect.objectContaining({ speaker: "CHI" })
        ])
      })));
    expect(screen.getByText("Extract language-sample features before generating a report.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate Report" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Extract features" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Extract features" }));
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith(expect.stringMatching(/^\/sessions\/.+\?view=findings/)));
    await waitFor(() => expect(loadWorkflowState()).toEqual(expect.objectContaining({
      featuresExtracted: true,
      featureSummary: expect.arrayContaining([
        expect.objectContaining({ label: "MLU words" })
      ])
    })));
    expect(screen.getByRole("button", { name: "Generate Report" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Generate Report" }));
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith(expect.stringMatching(/^\/sessions\/.+\?view=report.*report_id=/)));
  });

  it("re-enables transcript controls after a deferred current save returns a newer backend version", async () => {
    let resolveSave!: (response: Response) => void;
    const saveResponse = new Promise<Response>((resolve) => { resolveSave = resolve; });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/transcripts/TRANSCRIPT-DEFERRED-SAVE") && init?.method === "PATCH") {
        return saveResponse;
      }
      return jsonResponse({});
    }));
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-deferred-save",
      backendSessionId: "SESSION-DEFERRED-SAVE",
      backendTranscriptSessionId: "SESSION-DEFERRED-SAVE",
      backendTranscriptId: "TRANSCRIPT-DEFERRED-SAVE",
      backendTranscriptVersion: 2,
      source: "paste-transcript",
      transcriptReady: true,
      transcriptReviewStatus: "in_review",
      transcriptText: "@Begin\n*CHI:\tHello.\n@End",
      transcriptLines: [{ lineId: "line-1", speaker: "CHI", text: "Hello." }],
      transcriptSaveStatus: "saved",
    });

    await renderReviewTranscriptPage();
    fireEvent.change(screen.getByLabelText("Utterance text 1"), { target: { value: "Hello there." } });
    const saveButton = screen.getByRole("button", { name: "Save draft" });
    fireEvent.click(saveButton);
    expect(saveButton).toBeDisabled();

    resolveSave(await jsonResponse({
      transcript_id: "TRANSCRIPT-DEFERRED-SAVE",
      session_id: "SESSION-DEFERRED-SAVE",
      version: 3,
      raw_text: "@Begin\n*CHI:\tHello there.\n@End",
      utterances: [{ utterance_id: "line-1", speaker: "CHI", text: "Hello there." }],
    }));

    await waitFor(() => expect(saveButton).toBeEnabled());
    expect(loadWorkflowState().backendTranscriptVersion).toBe(3);
  });

  it("blocks unsafe progression after editing an attested transcript until review is re-completed", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-attested-session",
      backendSessionId: "SESSION-ATTESTED",
      backendTranscriptSessionId: "SESSION-ATTESTED",
      backendTranscriptId: "TRANSCRIPT-ATTESTED",
      transcriptReady: true,
      transcriptReviewStatus: "reviewed",
      transcriptAttested: true,
      transcriptSaveStatus: "saved",
      qaStatus: "pass",
      featuresExtracted: true,
      featureSummary: [{ label: "MLU words", value: "3.1" }],
      transcriptLines: [
        { lineId: "line-1", speaker: "THER", text: "Tell me more.", startMs: 0, endMs: 800 },
        { lineId: "line-2", speaker: "CHI", text: "I see a car.", startMs: 900, endMs: 1700 }
      ]
    });

    await renderReviewTranscriptPage();
    expect(screen.getByTestId("transcript-attestation-badge")).toHaveTextContent("Attested");
    expect(screen.getByRole("button", { name: "Generate Report" })).toBeEnabled();

    fireEvent.change(screen.getByLabelText("Utterance text 2"), { target: { value: "I see a blue car." } });

    await waitFor(() => {
      expect(loadWorkflowState()).toEqual(expect.objectContaining({
        transcriptAttested: false,
        transcriptReviewStatus: "in_review",
        qaStatus: "not_run",
        transcriptSaveStatus: "unsaved"
      }));
    });

    expect(screen.getByTestId("transcript-attestation-badge")).toHaveTextContent("Review required");
    expect(screen.getByRole("button", { name: "Generate Report" })).toBeDisabled();
  });

  it("connects paste transcript, analysis, and report actions to backend endpoints", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases")) {
        return jsonResponse([{ case_id: "CASE-001", consent_status: "granted" }]);
      }
      if (url.endsWith("/cases/CASE-001/sessions") && init?.method === "POST") {
        return jsonResponse({ session_id: "SESSION-NEW", case_id: "CASE-001" });
      }
      if (url.endsWith("/sessions/SESSION-NEW/transcripts/manual") && init?.method === "POST") {
        return jsonResponse({ transcript_id: "TRANSCRIPT-NEW", session_id: "SESSION-NEW", raw_text: "@Begin\n*CHI:\tHi.\n@End", review_status: "needs_review" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-NEW/qa") && init?.method === "POST") {
        return jsonResponse({ overall_status: "pass", issues: [], transcript_id: "TRANSCRIPT-NEW", can_extract_features: true });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-NEW/attest") && init?.method === "POST") {
        return jsonResponse({ transcript_id: "TRANSCRIPT-NEW" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-NEW/extract-features")) {
        return jsonResponse({ feature_id: "FEATURE-001", features: { mean_length_of_utterance_words: 3.4, number_of_different_words: 82, question_ratio: "7%" } });
      }
      if (url.endsWith("/sessions/SESSION-NEW/reports/draft") && init?.method === "POST") {
        return jsonResponse({ report_id: "REPORT-001", markdown: "# Draft Report Preview\n\nDecision-support only.", export_status: "draft" });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderRecordPage({ mode: "paste" });
    fireEvent.change(screen.getByRole("textbox", { name: "Pasted transcript text" }), {
      target: { value: "Therapist: Hello.\nChild: Hi." }
    });

    fireEvent.click(screen.getByRole("button", { name: "Save transcript" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/sessions/SESSION-NEW/transcripts/manual"), expect.objectContaining({ method: "POST" })));
    expect(loadWorkflowState()).toEqual(expect.objectContaining({
      backendSessionId: "SESSION-NEW",
      backendTranscriptId: "TRANSCRIPT-NEW"
    }));

    cleanup();
    await renderReviewTranscriptPage();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run QA" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Run QA" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/transcripts/TRANSCRIPT-NEW/qa"), expect.any(Object)));
    fireEvent.click(screen.getByRole("button", { name: "Attest transcript" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/transcripts/TRANSCRIPT-NEW/attest"), expect.objectContaining({ method: "POST" })));
    const attestCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/transcripts/TRANSCRIPT-NEW/attest"));
    expect(JSON.parse(String(attestCall?.[1]?.body ?? "{}"))).not.toHaveProperty("attested_by");

    cleanup();
    await renderRecordPage();
    fireEvent.click(screen.getByRole("button", { name: "Extract language-sample features" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/transcripts/TRANSCRIPT-NEW/extract-features"), expect.objectContaining({ method: "POST" })));
    expect(routerPush).toHaveBeenCalledWith(expect.stringMatching(/^\/sessions\/.+\?view=findings/));

    cleanup();
    await renderResultsPage();
    fireEvent.click(screen.getByRole("button", { name: "Generate report draft" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/sessions/SESSION-NEW/reports/draft"), expect.objectContaining({ method: "POST" })));
    expect(routerPush).toHaveBeenCalledWith(expect.stringMatching(/^\/sessions\/.+\?view=report.*report_id=/));
  });

  it("reloads a transcript from backend route IDs instead of stale browser state", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendSessionId: "STALE-SESSION",
      backendTranscriptId: "STALE-TRANSCRIPT",
      transcriptText: "@Begin\n*CHI:\tStale text.\n@End",
      transcriptLines: [{ lineId: "stale", speaker: "CHI", text: "Stale text." }]
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-REOPEN")) {
        return jsonResponse({ session_id: "SESSION-REOPEN", case_id: "CASE-REOPEN", transcript_id: "TRANSCRIPT-REOPEN" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-REOPEN")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-REOPEN",
          session_id: "SESSION-REOPEN",
          case_id: "CASE-REOPEN",
          raw_text: "@Begin\n@Languages:\teng\n*CHI:\tPersisted text.\n@End",
          utterances: [{ utterance_id: "utt-1", speaker: "CHI", text: "Persisted text." }],
          qa_status: "PASS",
          therapist_attested: true
        });
      }
      if (url.endsWith("/cases/CASE-REOPEN")) {
        return jsonResponse({ case_id: "CASE-REOPEN", child_code: "C-REOPEN", nickname: "Reopened case" });
      }
      return jsonResponse({});
    }));

    await renderReviewTranscriptPage({
      case_id: "CASE-REOPEN",
      session_id: "SESSION-REOPEN",
      transcript_id: "TRANSCRIPT-REOPEN"
    });

    expect(await screen.findByRole("textbox", { name: "Utterance text 1" })).toHaveValue("Persisted text.");
    expect(loadWorkflowState()).toEqual(expect.objectContaining({
      backendSessionId: "SESSION-REOPEN",
      backendTranscriptId: "TRANSCRIPT-REOPEN",
      transcriptAttested: true,
      transcriptSaveStatus: "saved"
    }));
  });

  it("reloads a finalized report from backend and keeps it read-only", async () => {
    const signedFixture = signedSnapshotFixture({
      markdown: "# Finalized persisted report",
      report_version: 3,
      signed_by: "Persisted therapist",
      signed_at: "2026-07-16T09:00:00Z",
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-FINAL")) {
        return jsonResponse({ session_id: "SESSION-FINAL", case_id: "CASE-FINAL", transcript_id: "TRANSCRIPT-FINAL", report_id: "REPORT-FINAL" });
      }
      if (url.endsWith("/reports/REPORT-FINAL")) {
        return jsonResponse({
          report_id: "REPORT-FINAL",
          session_id: "SESSION-FINAL",
          case_id: "CASE-FINAL",
          markdown: "# Finalized persisted report",
          status: "Signed Off",
          version: 3,
          signed_snapshot_version: 3,
          signed_snapshot_hash: signedFixture.reportHash,
          signed_snapshot: signedFixture.snapshot,
        });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-FINAL")) {
        return jsonResponse({ transcript_id: "TRANSCRIPT-FINAL", session_id: "SESSION-FINAL", therapist_attested: true });
      }
      if (url.endsWith("/cases/CASE-FINAL")) {
        return jsonResponse({ case_id: "CASE-FINAL", child_code: "C-FINAL" });
      }
      return jsonResponse({});
    }));

    await renderReportSummaryPage({
      case_id: "CASE-FINAL",
      session_id: "SESSION-FINAL",
      transcript_id: "TRANSCRIPT-FINAL",
      report_id: "REPORT-FINAL"
    });

    const finalizedReport = await screen.findByRole("textbox", { name: "Finalized report" });
    await waitFor(() => expect(finalizedReport).toHaveValue("# Finalized persisted report"));
    expect(screen.getByRole("button", { name: "Report Finalized" })).toBeDisabled();
    expect(loadWorkflowState().backendReportId).toBe("REPORT-FINAL");
  });

  it("keeps pasted transcript input locally without claiming backend save success", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new Error("offline");
    }));

    await renderRecordPage({ mode: "paste" });
    fireEvent.change(screen.getByRole("textbox", { name: "Pasted transcript text" }), {
      target: {
        value: [
          "Therapist: What do you see?",
          "Child: A blue car.",
          "Parent: It is his favorite."
        ].join("\n")
      }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save transcript" }));

    await waitFor(() => {
      const stored = JSON.parse(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "{}");
      expect(stored.sessionId).toMatch(/^local_/);
      expect(stored.source).toBe("paste-transcript");
      expect(stored.transcriptReviewStatus).toBe("draft");
      expect(stored.transcriptSaveStatus).toBe("failed");
      expect(stored.transcriptReady).toBe(false);
      expect(stored.transcriptLines).toEqual([
        expect.objectContaining({ speaker: "THER", text: "What do you see?" }),
        expect.objectContaining({ speaker: "CHI", text: "A blue car." }),
        expect.objectContaining({ speaker: "PAR", text: "It is his favorite." })
      ]);
      expect(stored.transcriptText).toContain("*THER:\tWhat do you see?");
      expect(stored.transcriptText).toContain("*CHI:\tA blue car.");
    });

    cleanup();
    await renderReviewTranscriptPage();
    expect(await screen.findByRole("textbox", { name: "Utterance text 2" })).toHaveValue("A blue car.");
    expect(screen.getByText("Failed to save transcript")).toBeInTheDocument();
  });

  it("parses uploaded CHA speaker tiers and preserves media timestamps", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new Error("offline");
    }));
    const chaText = [
      "@Begin",
      "@Languages:\teng",
      "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
      "@ID:\teng|Demo|CHI|4;00.00|female|||Target_Child|||",
      "@Media:\tdemo_audio, audio",
      "*THER:\tShow me the car. \u0015100_900\u0015",
      "%mor:\tv|show pro:obj|me det|the n|car",
      "*CHI:\tBlue car. \u0015950_1600\u0015",
      "@End"
    ].join("\n");
    const file = new File([chaText], "sample.cha", { type: "text/plain" });
    Object.defineProperty(file, "text", { value: async () => chaText });

    await renderRecordPage({ mode: "cha" });
    fireEvent.change(screen.getByLabelText("CHA transcript file"), {
      target: { files: [file] }
    });
    await waitFor(() => {
      expect(screen.getByRole("textbox", { name: "CHA transcript text" })).toHaveValue(chaText);
    });
    expect(screen.getByText("Unsupported dependent tier %mor was not imported.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save transcript" }));

    await waitFor(() => {
      const stored = JSON.parse(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "{}");
      expect(stored.sourceFilename).toBe("sample.cha");
      expect(stored.transcriptLines).toEqual([
        expect.objectContaining({ speaker: "THER", text: "Show me the car.", startMs: 100, endMs: 900 }),
        expect.objectContaining({ speaker: "CHI", text: "Blue car.", startMs: 950, endMs: 1600 })
      ]);
      expect(stored.transcriptText).toContain("\u0015100_900\u0015");
      expect(stored.transcriptText).toContain("\u0015950_1600\u0015");
      expect(stored.chatMetadata).toEqual(expect.objectContaining({
        languages: ["eng"],
        media: { name: "demo_audio", type: "audio" }
      }));
      expect(stored.chatWarnings).toContain("Unsupported dependent tier %mor was not imported.");
    });

    cleanup();
    await renderReviewTranscriptPage();
    expect(await screen.findByRole("textbox", { name: "Utterance text 1" })).toHaveValue("Show me the car.");
    expect(screen.getByLabelText("Timestamp for line 1")).toHaveValue("00:00.100 – 00:00.900");
  });

  it("shows a clear error and does not save an invalid CHA file", async () => {
    const invalidText = "This file has no CHAT headers or speaker tiers.";
    const file = new File([invalidText], "invalid.cha", { type: "text/plain" });
    Object.defineProperty(file, "text", { value: async () => invalidText });

    await renderRecordPage({ mode: "cha" });
    fireEvent.change(screen.getByLabelText("CHA transcript file"), {
      target: { files: [file] }
    });

    expect(await screen.findByText("Invalid .cha file: expected @Begin, @End, and at least one speaker line such as *CHI:.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save transcript" })).toBeDisabled();
    expect(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY)).toBeNull();
  });

  it("generates, reviews, exports, shares, and finalizes an editable report", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn(async () => undefined) }
    });
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:report") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-001/reports/draft") && init?.method === "POST") {
        return jsonResponse({
          report_id: "REPORT-001",
          session_id: "SESSION-001",
          case_id: "CASE-001",
          report_type: "Session Review Report",
          title: "Session Review Report",
          markdown: "# Draft Report Preview\n\nCaregiver reports improved turn-taking.\n\nIncrease spontaneous questions\n\nDecision-support only.",
          html: "<p>Draft Report Preview</p>"
        });
      }
      if (url.endsWith("/reports/REPORT-001") && init?.method === "PATCH") {
        return jsonResponse({ report_id: "REPORT-001", markdown: "# Edited report\n\nTherapist review required.\n\nDecision-support only. Not diagnostic.", status: "Draft" });
      }
      if (url.endsWith("/reports/REPORT-001/sign-off") && init?.method === "POST") {
        const body = JSON.parse(String(init.body ?? "{}"));
        expect(body.therapist_name).toBeUndefined();
        expect(body.signed_by).toBeUndefined();
        expect(body.confirmation_checked).toBe(true);
        return jsonResponse({ report_id: "REPORT-001", markdown: "# Edited report\n\nSigned by: Demo Therapist", status: "Signed Off" });
      }
      if (url.includes("/reports/REPORT-001/export")) {
        return jsonResponse({ filename: "REPORT-001.md", content: "# Edited report", content_type: "text/markdown" });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-report-session",
      backendSessionId: "SESSION-001",
      backendTranscriptSessionId: "SESSION-001",
      backendTranscriptId: "TRANSCRIPT-001",
      sessionCreatedAt: "2026-06-19T08:00:00.000Z",
      transcriptReady: true,
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      featuresExtracted: true,
      featureSummary: [{ label: "MLU words", value: "3.4" }],
      therapistNotes: "Caregiver reports improved turn-taking.",
      therapyGoals: ["Increase spontaneous questions", "Expand two-word combinations"]
    });

    await renderReportSummaryPage();
    expect(screen.getByRole("heading", { name: "Report Summary" })).toBeInTheDocument();
    expect(screen.getByText("Ethan L.")).toBeInTheDocument();
    expect(screen.getAllByText("Never generated").length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Overall Progress" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Strengths" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("heading", { name: "Needs Support" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("heading", { name: "Next Steps" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("textbox", { name: "Therapist notes" })).toHaveValue("Caregiver reports improved turn-taking.");
    expect(screen.getByRole("textbox", { name: "Therapy goals" })).toHaveValue("Increase spontaneous questions\nExpand two-word combinations");
    expect(screen.getByRole("textbox", { name: "Report not generated" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate draft" }));
    await waitFor(() => {
      expect((screen.getByRole("textbox", { name: "Editable draft report preview" }) as HTMLTextAreaElement).value).toContain("Caregiver reports improved turn-taking.");
    });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Working" })).not.toBeInTheDocument());
    expect((screen.getByRole("textbox", { name: "Editable draft report preview" }) as HTMLTextAreaElement).value).toContain("Increase spontaneous questions");
    expect((screen.getByRole("textbox", { name: "Editable draft report preview" }) as HTMLTextAreaElement).value).toContain("Decision-support only.");

    fireEvent.change(screen.getByRole("textbox", { name: "Editable draft report preview" }), {
      target: { value: "# Edited report\n\nTherapist review required.\n\nDecision-support only. Not diagnostic." }
    });
    expect(screen.getAllByText("Unsaved changes").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(screen.getAllByText("Saved").length).toBeGreaterThan(0));
    expect(screen.getByRole("button", { name: "Export PDF later" })).toBeDisabled();

    expect(screen.getByText("Not shared")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copy local demo share link" }));
    await waitFor(() => expect(screen.getByText("Local demo share link copied")).toBeInTheDocument());
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringMatching(/^\/sessions\/SESSION-001\?view=report.*report_id=REPORT-001$/),
    );
    fireEvent.click(screen.getByRole("button", { name: "Mark caregiver share recorded" }));
    expect(screen.getByText("Caregiver share recorded locally")).toBeInTheDocument();
    expect(screen.queryByText("Secure link copied")).not.toBeInTheDocument();

    expect(screen.getByRole("button", { name: "Finalize Report" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Finalize Report" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Report Finalized" })).toBeInTheDocument());
    const finalizedReport = screen.getByRole("textbox", { name: "Finalized report" });
    expect(finalizedReport).toHaveAttribute("readonly");
    expect(finalizedReport).toHaveValue("");
    expect(await screen.findByText("Signed snapshot integrity error.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate draft" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Export Markdown" }));
    fireEvent.click(screen.getByRole("button", { name: "Export HTML" }));
  });

  it("renders the grouped report library with canonical Session actions", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/reports")) {
        return jsonResponse([
          {
            report_id: "REPORT-DRAFT",
            session_id: "SESSION-DRAFT",
            case_id: "CASE-DRAFT",
            report_type: "Progress Report",
            title: "Draft progress report",
            markdown: "# Draft progress report\n\nDecision-support only.",
            status: "Draft",
            actual_provider: "template",
            updated_at: "2026-06-20T10:00:00Z"
          },
          {
            report_id: "REPORT-SIGNED",
            session_id: "SESSION-SIGNED",
            case_id: "CASE-SIGNED",
            report_type: "Progress Report",
            title: "Signed progress report",
            markdown: "# Signed progress report\n\nDecision-support only.",
            status: "Signed Off",
            actual_provider: "template",
            updated_at: "2026-06-21T10:00:00Z"
          }
        ]);
      }
      return jsonResponse({});
    }));

    render(<ReportsPage />);

    expect(await screen.findByRole("heading", { name: "Needs review" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Needs regeneration" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Signed reports" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Draft progress report" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Signed progress report" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review draft" })).toHaveAttribute(
      "href",
      "/sessions/SESSION-DRAFT?view=report&case_id=CASE-DRAFT&report_id=REPORT-DRAFT",
    );
    expect(screen.getByRole("link", { name: "View signed report" })).toHaveAttribute(
      "href",
      "/sessions/SESSION-SIGNED?view=report&case_id=CASE-SIGNED&report_id=REPORT-SIGNED",
    );
    expect(screen.queryByRole("textbox", { name: /report/i })).not.toBeInTheDocument();
  });

  it("exports the reviewed line-first transcript as basic CHAT", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/transcripts/TRANSCRIPT-EXPORT/export-cha")) {
        return jsonResponse({
          filename: "TRANSCRIPT-EXPORT_reviewed.cha",
          cha_text: "@Languages:\teng\n*INV:\tTell me more.\n*GRM:\tBlue car."
        });
      }
      return jsonResponse({});
    }));
    saveWorkflowState({
      ...createInitialWorkflowState(),
      sessionId: "local-export-session",
      transcriptReady: true,
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      backendTranscriptId: "TRANSCRIPT-EXPORT",
      transcriptLines: [
        { lineId: "line-1", speaker: "INV", text: "Tell me more.", startMs: 100, endMs: 900 },
        { lineId: "line-2", speaker: "GRM", text: "Blue car.", startMs: 950, endMs: 1600 }
      ],
      chatMetadata: {
        languages: ["eng"],
        participants: [
          { code: "INV", name: "Investigator", role: "Investigator" },
          { code: "GRM", name: "Grandmother", role: "Adult" }
        ],
        ids: [],
        media: { name: "session_audio", type: "audio" },
        headers: {}
      }
    });
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:chat-export") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    await renderReportSummaryPage();
    fireEvent.click(screen.getByRole("button", { name: "Export reviewed .cha" }));

    const exported = await screen.findByRole("textbox", { name: "Exported reviewed CHA" }) as HTMLTextAreaElement;
    expect(exported.value).toContain("@Languages:\teng");
    expect(exported.value).toContain("*GRM:\tBlue car.");
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it("keeps admin runtime controls role-scoped in settings", async () => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "org_admin",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
    await renderSettingsPage({});
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Account" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Team" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Integration Status" }));

    expect(await screen.findByText("Auth lifecycle")).toBeInTheDocument();
    expect(await screen.findByText("Runtime diagnostics")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Integration Status" })).toBeInTheDocument();
  });

  it("opens settings in admin scope from mock org-admin login query", async () => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "org_admin",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
    await renderSettingsPage({ scope: "admin" });

    expect(await screen.findByRole("heading", { name: "Team" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Care-team administration" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Account" })).not.toBeInTheDocument();
  });

  it("walks through the complete simplified flow: Today -> Paste -> Review -> Results -> Report Summary -> Export .cha", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases")) {
        return jsonResponse([{ case_id: "CASE-123", consent_status: "granted" }]);
      }
      if (url.endsWith("/cases/CASE-123/sessions") && init?.method === "POST") {
        return jsonResponse({ session_id: "SESSION-123", case_id: "CASE-123" });
      }
      if (url.endsWith("/sessions/SESSION-123/transcripts/manual") && init?.method === "POST") {
        return jsonResponse({ transcript_id: "TRANSCRIPT-123", session_id: "SESSION-123", raw_text: "@Begin\n*CHI:\tHi.\n@End", review_status: "needs_review" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-123/qa") && init?.method === "POST") {
        return jsonResponse({ overall_status: "pass", issues: [], transcript_id: "TRANSCRIPT-123", can_extract_features: true });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-123/attest") && init?.method === "POST") {
        return jsonResponse({ transcript_id: "TRANSCRIPT-123" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-123/export-cha")) {
        return jsonResponse({ filename: "TRANSCRIPT-123_reviewed.cha", cha_text: "@Begin\n*CHI:\tA blue ball.\n@End" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-123/extract-features")) {
        return jsonResponse({ feature_id: "FEAT-123", features: { mean_length_of_utterance_words: 3.2, number_of_different_words: 78, question_ratio: "5%" } });
      }
      if (url.endsWith("/sessions/SESSION-123/reports/draft") && init?.method === "POST") {
        return jsonResponse({ report_id: "REP-123", markdown: "# Draft Report Preview\n\nDecision-support only.", export_status: "draft" });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:reviewed-cha") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    render(<TodayPage />);
    expect(screen.getByRole("heading", { name: "Work Queue" })).toBeInTheDocument();

    cleanup();
    await renderRecordPage({ mode: "paste" });
    expect(screen.getByRole("heading", { name: "Session Intake" })).toBeInTheDocument();
    
    const textarea = screen.getByRole("textbox", { name: "Pasted transcript text" });
    fireEvent.change(textarea, {
      target: { value: "Therapist: What is that?\nChild: A red ball.\nChild: I want it.\nChild: Yes it is." }
    });

    const saveButton = screen.getByRole("button", { name: "Save transcript" });
    fireEvent.click(saveButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/sessions/SESSION-123/transcripts/manual"), expect.objectContaining({ method: "POST" })));
    expect(routerPush).toHaveBeenCalledWith(expect.stringMatching(/^\/sessions\/SESSION-123\?view=transcript/));

    cleanup();
    await renderReviewTranscriptPage();
    expect(screen.getByRole("heading", { name: "Review Transcript" })).toBeInTheDocument();

    expect(await screen.findByRole("textbox", { name: "Utterance text 2" })).toHaveValue("A red ball.");
    fireEvent.change(screen.getByRole("textbox", { name: "Utterance text 2" }), {
      target: { value: "A blue ball." }
    });

    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => {
      const stored = JSON.parse(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "{}");
      expect(stored.transcriptLines[1].text).toBe("A blue ball.");
    });

    fireEvent.click(screen.getByRole("button", { name: "Run QA" }));
    await waitFor(() => {
      const qaCall = fetchMock.mock.calls.find(([input, init]) => (
        String(input).includes("/transcripts/TRANSCRIPT-123/qa") && init?.method === "POST"
      ));
      expect(qaCall).toBeDefined();
    });
    await waitFor(() => expect(loadWorkflowState()).toEqual(expect.objectContaining({ qaStatus: "pass" })));
    await waitFor(() => expect(screen.getByRole("button", { name: "Attest transcript" })).toBeEnabled());

    fireEvent.click(screen.getByRole("button", { name: "Export reviewed .cha" }));
    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Attest transcript" }));
    await waitFor(() => expect(screen.getByText("Transcript attested")).toBeInTheDocument());

    cleanup();
    await renderRecordPage();
    const extractButton = screen.getByRole("button", { name: "Extract language-sample features" });
    expect(extractButton).toBeEnabled();
    fireEvent.click(extractButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/transcripts/TRANSCRIPT-123/extract-features"), expect.objectContaining({ method: "POST" })));
    expect(routerPush).toHaveBeenCalledWith(expect.stringMatching(/^\/sessions\/SESSION-123\?view=findings/));

    cleanup();
    await renderResultsPage();
    expect(screen.getByRole("heading", { name: "Linguistic Signals" })).toBeInTheDocument();
    expect(screen.getByText("MLU words")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Generate report draft" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/sessions/SESSION-123/reports/draft"), expect.objectContaining({ method: "POST" })));
    expect(routerPush).toHaveBeenCalledWith(expect.stringMatching(/^\/sessions\/.+\?view=report.*report_id=/));

    cleanup();
    await renderReportSummaryPage();
    expect(screen.getByRole("heading", { name: "Report Summary" })).toBeInTheDocument();
  });

  it("strictly overrides stale sessionStorage transcript if transcript_id is in URL", async () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendSessionId: "STALE-SESSION",
      backendTranscriptId: "STALE-TRANSCRIPT",
      transcriptText: "@Begin\n*CHI:\tStale sessionStorage text.\n@End",
      transcriptLines: [{ lineId: "stale", speaker: "CHI", text: "Stale sessionStorage text." }]
    });
    
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-OK")) {
        return jsonResponse({ session_id: "SESSION-OK", case_id: "CASE-OK", transcript_id: "TRANSCRIPT-OK" });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-OK")) {
        return jsonResponse({
          transcript_id: "TRANSCRIPT-OK",
          session_id: "SESSION-OK",
          case_id: "CASE-OK",
          raw_text: "@Begin\n@Languages:\teng\n*CHI:\tWinner backend text.\n@End",
          utterances: [{ utterance_id: "utt-1", speaker: "CHI", text: "Winner backend text." }],
          qa_status: "PASS",
          therapist_attested: true
        });
      }
      if (url.endsWith("/cases/CASE-OK")) {
        return jsonResponse({ case_id: "CASE-OK", child_code: "C-OK" });
      }
      return jsonResponse({});
    }));

    await renderReviewTranscriptPage({
      case_id: "CASE-OK",
      session_id: "SESSION-OK",
      transcript_id: "TRANSCRIPT-OK"
    });

    // Backend text must win
    expect(await screen.findByRole("textbox", { name: "Utterance text 1" })).toHaveValue("Winner backend text.");
    expect(loadWorkflowState().transcriptText).toContain("Winner backend text.");
  });

  it("enters offline mode, disables clinical-final buttons with Online only label, and hides success messages", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));
    
    saveWorkflowState({
      ...createInitialWorkflowState(),
      backendSessionId: "SESSION-OFFLINE",
      backendTranscriptId: "TRANSCRIPT-OFFLINE",
      transcriptText: "@Begin\n*CHI:\thello .\n@End",
      transcriptLines: [{ lineId: "line-1", speaker: "CHI", text: "hello" }],
      transcriptReady: true,
      qaStatus: "pass",
      transcriptSaveStatus: "saved",
      statusMessage: "Transcript draft saved." // Stale success message
    });

    await renderReviewTranscriptPage({
      case_id: "CASE-OFFLINE",
      session_id: "SESSION-OFFLINE",
      transcript_id: "TRANSCRIPT-OFFLINE"
    });

    // Shows banner
    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    
    // Suppresses the success status message
    expect(screen.queryByText("Transcript draft saved.")).not.toBeInTheDocument();
    
    // Explicit locator failures must not restore a prior transcript or enable clinical-final actions.
    expect(screen.queryByDisplayValue("hello")).not.toBeInTheDocument();
    const attestBtn = screen.getByRole("button", { name: "Attest transcript" });
    expect(attestBtn).toBeDisabled();
  });

  it("strictly disables report finalization inputs and save actions when finalized", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/sessions/SESSION-FIN")) {
        return jsonResponse({ session_id: "SESSION-FIN", case_id: "CASE-FIN", transcript_id: "TRANSCRIPT-FIN", report_id: "REPORT-FIN" });
      }
      if (url.endsWith("/reports/REPORT-FIN")) {
        return jsonResponse({
          report_id: "REPORT-FIN",
          session_id: "SESSION-FIN",
          case_id: "CASE-FIN",
          markdown: "# Finalized report markdown",
          status: "Signed Off"
        });
      }
      if (url.endsWith("/transcripts/TRANSCRIPT-FIN")) {
        return jsonResponse({ transcript_id: "TRANSCRIPT-FIN", session_id: "SESSION-FIN", therapist_attested: true });
      }
      if (url.endsWith("/cases/CASE-FIN")) {
        return jsonResponse({ case_id: "CASE-FIN", child_code: "C-FIN" });
      }
      return jsonResponse({});
    }));

    await renderReportSummaryPage({
      case_id: "CASE-FIN",
      session_id: "SESSION-FIN",
      transcript_id: "TRANSCRIPT-FIN",
      report_id: "REPORT-FIN"
    });

    const reportArea = await screen.findByRole("textbox", { name: "Finalized report" });
    expect((reportArea as HTMLTextAreaElement).readOnly).toBe(true);
    
    const finalizeBtn = screen.getByRole("button", { name: "Report Finalized" });
    expect(finalizeBtn).toBeDisabled();
    
    const saveBtn = screen.getByRole("button", { name: "Save draft" });
    expect(saveBtn).toBeDisabled();
    
    const generateBtn = screen.getByRole("button", { name: "Generate draft" });
    expect(generateBtn).toBeDisabled();
  });

  it("renders backend unavailable banner on /record, /results, and /report-summary pages in offline mode", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));
    
    // Test for /record page (RecordPage)
    const recordRes = await renderRecordPage({ case_id: "OFFLINE-CASE" });
    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    recordRes.unmount();

    // Test for /results page (ResultsPage)
    const resultsRes = await renderResultsPage({ case_id: "OFFLINE-CASE" });
    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    resultsRes.unmount();

    // Test for /report-summary page (ReportSummaryPage)
    const reportRes = await renderReportSummaryPage({ case_id: "OFFLINE-CASE" });
    expect(await screen.findByText("Backend unavailable — local workspace mode")).toBeInTheDocument();
    reportRes.unmount();
  });
});

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init
  }));
}
