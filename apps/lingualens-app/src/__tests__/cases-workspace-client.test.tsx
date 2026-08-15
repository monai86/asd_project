import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderAsyncPage, routerPush } from "@/__tests__/setup";
import CasesPage from "@/app/cases/page";
import CaseDetailPage from "@/app/cases/[caseId]/page";

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "mock" },
  }),
}));

beforeEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("cases workspace", () => {
  it("renders a table-style case workspace with search, filters, right rail, and pagination footer", async () => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "org_admin",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
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

    await renderAsyncPage(CasesPage);

    const table = await screen.findByRole("table", { name: "Cases workspace" });
    expect(table).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: "Search cases" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All statuses" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Needs Review" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Clinician filter" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Latest activity" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Workflow status" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Next action" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Clinician" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Case overview stats" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Workflow at a glance" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Recent activity" })).not.toBeInTheDocument();
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

    await renderAsyncPage(CasesPage);

    expect(await screen.findByRole("heading", { name: "No cases yet" })).toBeInTheDocument();
    expect(screen.getByText("Create a de-identified case before recording consent or starting a session.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create case" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Recent activity" })).not.toBeInTheDocument();
  });

  it("creates a de-identified case with pending consent before opening its record", async () => {
    let createPayload: Record<string, unknown> | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases") && init?.method === "POST") {
        createPayload = JSON.parse(init.body as string);
        return jsonResponse({ case_id: "case_staging_001", child_code: "STAGING-001", nickname: "Test Child A", age_months: 60, language: "Thai", consent_status: "pending", notes: "Synthetic staging case", care_team_user_ids: ["therapist-demo"] });
      }
      if (url.endsWith("/cases")) return jsonResponse([]);
      throw new Error(`Unexpected request: ${url}`);
    }));

    await renderAsyncPage(CasesPage);
    fireEvent.click(await screen.findByRole("button", { name: "Create case" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Case code" }), { target: { value: " STAGING-001 " } });
    fireEvent.change(screen.getByRole("textbox", { name: "Nickname" }), { target: { value: " Test Child A " } });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Age in months" }), { target: { value: "60" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Language" }), { target: { value: " Thai " } });
    fireEvent.change(screen.getByRole("textbox", { name: "Case notes" }), { target: { value: " Synthetic staging case " } });
    fireEvent.click(screen.getByRole("button", { name: "Save case" }));

    await waitFor(() => {
      expect(createPayload).toEqual({ child_code: "STAGING-001", nickname: "Test Child A", age_months: 60, language: "Thai", notes: "Synthetic staging case", consent_status: "pending" });
      expect(routerPush).toHaveBeenCalledWith("/cases/case_staging_001");
    });
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
    expect(screen.getByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Goals" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sessions" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Progress" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Reports" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Upcoming tasks" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recent notes" })).toBeInTheDocument();
    expect(await screen.findByText("Expand spontaneous utterances")).toBeInTheDocument();
    expect(await screen.findByText("Session 2026-06-12")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Open session workspace" })).toHaveAttribute("href", "/sessions/session_demo_001?view=intake");
  });

  it("keeps case care-team data read-only and never fetches admin-only resources", async () => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "therapist",
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

    expect(await screen.findByRole("heading", { name: "Care team" })).toBeInTheDocument();
    expect(screen.getByText("This is a read-only care-team summary. Organization administrators manage assignments in the role-gated Team section of Settings.")).toBeInTheDocument();
    expect(getRequestedOrganizationIds(vi.mocked(fetch), "/cases/case_demo_001/care-team")).toEqual([]);
    expect(getRequestedOrganizationIds(vi.mocked(fetch), "/organizations/current/memberships")).toEqual([]);

    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "org_admin",
      organizationId: "pilot_org_ops",
      aal: "aal2",
    }));
    act(() => {
      window.dispatchEvent(new CustomEvent("lingualens:mock-access-session-changed"));
    });

    expect(getRequestedOrganizationIds(vi.mocked(fetch), "/cases/case_demo_001/care-team")).toEqual([]);
    expect(screen.queryByText("Assign or reassign therapist")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove assignment" })).not.toBeInTheDocument();
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
          consent_status: "granted",
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
            consent_status: "granted",
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

    expect(await screen.findByRole("heading", { name: "New intake" })).toBeInTheDocument();
    expect(screen.getByText("No communication goals recorded yet.")).toBeInTheDocument();
    expect(screen.getByText("No sessions recorded yet for this case.")).toBeInTheDocument();
    expect(screen.getByText("No recent therapist notes recorded yet.")).toBeInTheDocument();
    expect(screen.getByText("Referral or intake context has not been added yet.")).toBeInTheDocument();
  });

  it("disables session creation and shows warning alert when consent is pending", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases/case_demo_pending")) {
        return jsonResponse({
          case_id: "case_demo_pending",
          child_code: "C-pending",
          nickname: "Pending child",
          age_months: 60,
          language: "English",
          consent_status: "pending",
          notes: "Some notes",
          review_priority: "low",
          latest_session_date: null,
          latest_session_status: "Draft",
          latest_report_status: "Draft",
          care_team_user_ids: []
        });
      }
      if (url.endsWith("/cases/case_demo_pending/timeline")) return jsonResponse([]);
      if (url.endsWith("/cases/case_demo_pending/goals")) return jsonResponse([]);
      if (url.endsWith("/cases")) {
        return jsonResponse([
          {
            case_id: "case_demo_pending",
            child_code: "C-pending",
            nickname: "Pending child",
            age_months: 60,
            language: "English",
            consent_status: "pending",
            notes: "Some notes",
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

    await renderAsyncPage(CaseDetailPage, { params: { caseId: "case_demo_pending" } });

    expect(await screen.findByText("Caregiver Consent Verification Required")).toBeInTheDocument();
    
    const createButton = screen.getByRole("link", { name: "Create new session" });
    expect(createButton).toHaveClass("opacity-60");
    expect(createButton).toHaveClass("cursor-not-allowed");
    expect(createButton).toHaveAttribute("href", "#");
  });

  it("submitting the consent verification form calls update API and unlocks session creation", async () => {
    let patchPayload: any = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases/case_demo_pending") && init?.method === "PATCH") {
        patchPayload = JSON.parse(init.body as string);
        return jsonResponse({
          case_id: "case_demo_pending",
          child_code: "C-pending",
          nickname: "Pending child",
          age_months: 60,
          language: "English",
          consent_status: "granted",
          notes: "Some notes\nConsent verified...",
          review_priority: "low",
          latest_session_date: null,
          latest_session_status: "Draft",
          latest_report_status: "Draft",
          care_team_user_ids: []
        });
      }
      if (url.endsWith("/cases/case_demo_pending")) {
        return jsonResponse({
          case_id: "case_demo_pending",
          child_code: "C-pending",
          nickname: "Pending child",
          age_months: 60,
          language: "English",
          consent_status: "pending",
          notes: "Some notes",
          review_priority: "low",
          latest_session_date: null,
          latest_session_status: "Draft",
          latest_report_status: "Draft",
          care_team_user_ids: []
        });
      }
      if (url.endsWith("/cases/case_demo_pending/timeline")) return jsonResponse([]);
      if (url.endsWith("/cases/case_demo_pending/goals")) return jsonResponse([]);
      if (url.endsWith("/cases")) {
        return jsonResponse([
          {
            case_id: "case_demo_pending",
            child_code: "C-pending",
            nickname: "Pending child",
            age_months: 60,
            language: "English",
            consent_status: "pending",
            notes: "Some notes",
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

    await renderAsyncPage(CaseDetailPage, { params: { caseId: "case_demo_pending" } });

    expect(await screen.findByRole("heading", { name: "Pending child" })).toBeInTheDocument();

    const checkbox = await screen.findByRole("checkbox", { name: /I verify/i });
    expect(checkbox).toBeInTheDocument();

    fireEvent.click(checkbox);

    const relationshipInput = screen.getByPlaceholderText("e.g. Parent, Guardian");
    fireEvent.change(relationshipInput, { target: { value: "Mother" } });

    const notesInput = screen.getByPlaceholderText(/Add any verification comments/i);
    fireEvent.change(notesInput, { target: { value: "Verified on phone call." } });

    const submitButton = screen.getByRole("button", { name: "Verify and Grant Consent" });
    await act(async () => {
      fireEvent.click(submitButton);
    });

    await waitFor(() => {
      expect(patchPayload).not.toBeNull();
      expect(patchPayload.consent_status).toBe("granted");
      expect(patchPayload.notes).toContain("Mother");
      expect(patchPayload.notes).toContain("Verified on phone call.");
    });

    const createButton = screen.getByRole("link", { name: "Create new session" });
    expect(createButton).not.toHaveClass("opacity-60");
    expect(createButton).not.toHaveClass("cursor-not-allowed");
    expect(createButton).toHaveAttribute("href", "/cases?intent=start-session");

    expect(screen.getByText("Consent Active")).toBeInTheDocument();
  });

  it("clicking withdraw consent calls the withdraw API and marks consent as withdrawn", async () => {
    let withdrawCalled = false;
    let withdrawPayload: any = null;
    vi.spyOn(window, "confirm").mockImplementation(() => true);

    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases/case_demo_granted/withdraw-consent") && init?.method === "POST") {
        withdrawCalled = true;
        withdrawPayload = JSON.parse(init.body as string);
        return jsonResponse({ status: "success", message: "withdrawn" });
      }
      if (url.endsWith("/cases/case_demo_granted")) {
        return jsonResponse({
          case_id: "case_demo_granted",
          child_code: "C-granted",
          nickname: "Granted child",
          age_months: 60,
          language: "English",
          consent_status: "granted",
          notes: "Some notes",
          review_priority: "low",
          latest_session_date: null,
          latest_session_status: "Draft",
          latest_report_status: "Draft",
          care_team_user_ids: []
        });
      }
      if (url.endsWith("/cases/case_demo_granted/timeline")) return jsonResponse([]);
      if (url.endsWith("/cases/case_demo_granted/goals")) return jsonResponse([]);
      if (url.endsWith("/cases")) {
        return jsonResponse([
          {
            case_id: "case_demo_granted",
            child_code: "C-granted",
            nickname: "Granted child",
            age_months: 60,
            language: "English",
            consent_status: "granted",
            notes: "Some notes",
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

    await renderAsyncPage(CaseDetailPage, { params: { caseId: "case_demo_granted" } });

    expect(await screen.findByRole("heading", { name: "Granted child" })).toBeInTheDocument();

    const withdrawButton = await screen.findByRole("button", { name: "Withdraw Consent" });
    expect(withdrawButton).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(withdrawButton);
    });

    await waitFor(() => {
      expect(withdrawCalled).toBe(true);
      expect(withdrawPayload.reason).toBe("Therapist request");
      expect(withdrawPayload.redact_notes).toBe(true);
    });

    expect(screen.getByText("Caregiver Consent Verification Required")).toBeInTheDocument();

    const createButton = screen.getByRole("link", { name: "Create new session" });
    expect(createButton).toHaveClass("opacity-60");
    expect(createButton).toHaveAttribute("href", "#");
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
