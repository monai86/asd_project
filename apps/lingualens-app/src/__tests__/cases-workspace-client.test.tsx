import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderAsyncPage } from "@/__tests__/setup";
import CasesPage from "@/app/cases/page";
import CaseDetailPage from "@/app/cases/[caseId]/page";

beforeEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("cases workspace", () => {
  it("renders a table-style case workspace with search, filters, right rail, and pagination footer", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
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
            notes: "Referral context: language sampling follow-up.",
            review_priority: "moderate",
            latest_session_date: "2026-06-12",
            latest_session_status: "Needs Review",
            latest_report_status: "Draft",
            care_team_user_ids: ["therapist-demo"]
          },
          {
            case_id: "case_demo_002",
            child_code: "C-1031",
            nickname: "Follow-up sample",
            age_months: 56,
            language: "Thai-English",
            consent_status: "pending",
            notes: "",
            review_priority: "low",
            latest_session_date: "2026-06-10",
            latest_session_status: "Attested",
            latest_report_status: "Ready",
            care_team_user_ids: ["therapist-demo", "clinician-jane"]
          }
        ]);
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<CasesPage />);

    const table = await screen.findByRole("table", { name: "Cases workspace" });
    expect(table).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: "Search cases" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All statuses" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Needs Review" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Clinician filter" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Workflow stage" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Next action" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Clinician" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Case overview stats" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Workflow at a glance" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recent activity" })).toBeInTheDocument();
    expect(screen.getByText("Showing 1-2 of 2 cases")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: "Search cases" }), {
      target: { value: "Follow-up" }
    });

    await waitFor(() => {
      expect(within(table).queryByText("Demo child")).not.toBeInTheDocument();
    });
    expect(within(table).getByText("Follow-up sample")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("combobox", { name: "Clinician filter" }), {
      target: { value: "clinician-jane" }
    });

    await waitFor(() => {
      expect(within(table).getByText("Follow-up sample")).toBeInTheDocument();
    });
  });

  it("renders a safe empty state when no cases are returned", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases")) {
        return jsonResponse([]);
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<CasesPage />);

    expect(await screen.findByRole("heading", { name: "No cases yet" })).toBeInTheDocument();
    expect(screen.getByText("Create or open a case from the backend workspace to view session progress here.")).toBeInTheDocument();
    expect(screen.getByText("No recent case activity yet.")).toBeInTheDocument();
  });

  it("renders case detail sections with session history and communication goals", async () => {
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
          notes: "Referral context: parent requested follow-up language review.",
          review_priority: "moderate",
          latest_session_date: "2026-06-12",
          latest_session_status: "Needs Review",
          latest_report_status: "Draft",
          care_team_user_ids: ["therapist-demo"]
        });
      }
      if (url.endsWith("/cases/case_demo_001/timeline")) {
        return jsonResponse([
          {
            event_id: "evt_1",
            label: "Session 2026-06-12",
            status: "Needs Review",
            occurred_at: "2026-06-12T09:30:00Z",
            target_id: "session_demo_001"
          }
        ]);
      }
      if (url.endsWith("/cases/case_demo_001/goals")) {
        return jsonResponse([
          {
            goal_id: "goal_1",
            case_id: "case_demo_001",
            title: "Expand spontaneous utterances",
            target: "Increase independent two-word phrases",
            status: "active",
            notes: "Carry into the next reviewed session."
          }
        ]);
      }
      if (url.endsWith("/cases")) {
        return jsonResponse([
          {
            case_id: "case_demo_001",
            child_code: "C-1024",
            nickname: "Demo child",
            age_months: 62,
            language: "English",
            consent_status: "granted",
            notes: "Referral context: parent requested follow-up language review.",
            review_priority: "moderate",
            latest_session_date: "2026-06-12",
            latest_session_status: "Needs Review",
            latest_report_status: "Draft",
            care_team_user_ids: ["therapist-demo"]
          }
        ]);
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    await renderAsyncPage(CaseDetailPage, { params: { caseId: "case_demo_001" } });

    expect(await screen.findByRole("heading", { name: "Demo child" })).toBeInTheDocument();
    expect(screen.getByText("Primary therapist")).toBeInTheDocument();
    expect(screen.getByText("Consent status")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Case summary" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Communication goals" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Session history" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Progress snapshot" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Upcoming tasks" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recent notes" })).toBeInTheDocument();
    expect(screen.getByText("Expand spontaneous utterances")).toBeInTheDocument();
    expect(screen.getByText("Session 2026-06-12")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open session workspace" })).toHaveAttribute("href", "/record?case_id=case_demo_001&session_id=session_demo_001");
  });

  it("refetches care-team management state when the active organization session changes", async () => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "org_admin",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const headers = new Headers(init?.headers);
      const orgId = headers.get("X-Organization-Id");

      if (url.endsWith("/cases/case_demo_001")) {
        return jsonResponse({
          case_id: "case_demo_001",
          child_code: "C-1024",
          nickname: "Demo child",
          age_months: 62,
          language: "English",
          consent_status: "granted",
          notes: "Referral context.",
          review_priority: "moderate",
          latest_session_date: "2026-06-12",
          latest_session_status: "Needs Review",
          latest_report_status: "Draft",
          care_team_user_ids: ["therapist-demo"],
          primary_therapist_user_id: "therapist-demo",
        });
      }
      if (url.endsWith("/cases/case_demo_001/timeline")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/cases/case_demo_001/goals")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/cases")) {
        return jsonResponse([{
          case_id: "case_demo_001",
          child_code: "C-1024",
          nickname: "Demo child",
          age_months: 62,
          language: "English",
          consent_status: "granted",
          notes: "Referral context.",
          review_priority: "moderate",
          latest_session_date: "2026-06-12",
          latest_session_status: "Needs Review",
          latest_report_status: "Draft",
          care_team_user_ids: ["therapist-demo"],
          primary_therapist_user_id: "therapist-demo",
        }]);
      }
      if (url.endsWith("/cases/case_demo_001/care-team")) {
        return jsonResponse(orgId === "pilot_org_ops"
          ? [{
              assignment_id: "team_ops",
              organization_id: "pilot_org_ops",
              case_id: "case_demo_001",
              user_id: "ops_therapist",
              role: "therapist",
              active: true,
              is_primary: true,
            }]
          : [{
              assignment_id: "team_pilot",
              organization_id: "pilot_org_001",
              case_id: "case_demo_001",
              user_id: "therapist-demo",
              role: "therapist",
              active: true,
              is_primary: true,
            }]);
      }
      if (url.endsWith("/organizations/current/memberships")) {
        return jsonResponse(orgId === "pilot_org_ops"
          ? [{
              membership_id: "mbr_ops",
              organization_id: "pilot_org_ops",
              user_id: "ops_therapist",
              display_name: "Ops Therapist",
              role: "therapist",
              active: true,
            }]
          : [{
              membership_id: "mbr_pilot",
              organization_id: "pilot_org_001",
              user_id: "therapist-demo",
              display_name: "Demo Therapist",
              role: "therapist",
              active: true,
            }]);
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    await renderAsyncPage(CaseDetailPage, { params: { caseId: "case_demo_001" } });

    await waitFor(() => {
      expect(getRequestedOrganizationIds(vi.mocked(fetch), "/cases/case_demo_001/care-team")).toContain("pilot_org_001");
    });

    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "org_admin",
      organizationId: "pilot_org_ops",
      aal: "aal2",
    }));
    act(() => {
      window.dispatchEvent(new CustomEvent("lingualens:mock-access-session-changed"));
    });

    const careTeamCard = screen.getByRole("heading", { name: "Care team & sign-off ownership" }).closest("section");
    expect(careTeamCard).not.toBeNull();

    await waitFor(() => {
      expect(getRequestedOrganizationIds(vi.mocked(fetch), "/cases/case_demo_001/care-team")).toContain("pilot_org_ops");
    });
    expect((await within(careTeamCard as HTMLElement).findAllByText("Ops Therapist")).length).toBeGreaterThan(0);
  });

  it("renders safe empty states in case detail when goals and sessions are missing", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases/case_demo_empty")) {
        return jsonResponse({
          case_id: "case_demo_empty",
          child_code: "C-1100",
          nickname: "New intake",
          age_months: 48,
          language: "Language not recorded",
          consent_status: "pending",
          notes: "",
          review_priority: "low",
          latest_session_date: null,
          latest_session_status: "Draft",
          latest_report_status: "Draft",
          care_team_user_ids: []
        });
      }
      if (url.endsWith("/cases/case_demo_empty/timeline")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/cases/case_demo_empty/goals")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/cases")) {
        return jsonResponse([
          {
            case_id: "case_demo_empty",
            child_code: "C-1100",
            nickname: "New intake",
            age_months: 48,
            language: "Language not recorded",
            consent_status: "pending",
            notes: "",
            review_priority: "low",
            latest_session_date: null,
            latest_session_status: "Draft",
            latest_report_status: "Draft",
            care_team_user_ids: []
          }
        ]);
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    await renderAsyncPage(CaseDetailPage, { params: { caseId: "case_demo_empty" } });

    expect(await screen.findByText("No communication goals recorded yet.")).toBeInTheDocument();
    expect(screen.getByText("No sessions recorded yet for this case.")).toBeInTheDocument();
    expect(screen.getByText("No recent therapist notes recorded yet.")).toBeInTheDocument();
    expect(screen.getByText("Referral or intake context has not been added yet.")).toBeInTheDocument();
  });
});

function jsonResponse(body: unknown) {
  return {
    ok: true,
    json: async () => body
  } as Response;
}

function getRequestedOrganizationIds(fetchMock: ReturnType<typeof vi.fn>, pathFragment: string) {
  return fetchMock.mock.calls
    .filter(([input]) => String(input).includes(pathFragment))
    .map(([, init]) => new Headers(init?.headers).get("X-Organization-Id"));
}
