import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsWorkspaceClient } from "@/components/settings-workspace-client";
import { saveMockAccessSession } from "@/lib/mock-access-session";

beforeEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
  window.localStorage.clear();
  saveMockAccessSession({ role: "org_admin", organizationId: "pilot_org_001", aal: "aal2" });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("SettingsWorkspaceClient admin lifecycle UX", () => {
  it("uses a mobile category index before drilling into one selected settings page", () => {
    saveMockAccessSession({ role: "therapist", organizationId: "pilot_org_001", aal: "aal2" });
    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialScope="therapist" />);

    const workspace = screen.getByTestId("settings-workspace");
    expect(workspace).toHaveAttribute("data-mobile-view", "categories");

    const mobileNavigation = screen.getByRole("navigation", { name: "Settings categories mobile" });
    fireEvent.click(within(mobileNavigation).getByRole("link", { name: "Privacy & Security" }));
    expect(workspace).toHaveAttribute("data-mobile-view", "detail");

    fireEvent.click(screen.getByRole("button", { name: "All settings categories" }));
    expect(workspace).toHaveAttribute("data-mobile-view", "categories");
  });

  it("renders one therapist category at a time and no admin navigation", () => {
    saveMockAccessSession({ role: "therapist", organizationId: "pilot_org_001", aal: "aal2" });
    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialScope="therapist" />);

    expect(screen.getByRole("heading", { name: "Account" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Account" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Organization" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Accessibility & Display" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Notifications" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Privacy & Security" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Export" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Help" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Team" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Invitations" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Notification preferences" })).not.toBeInTheDocument();
    expect(screen.getByText("Demo mode")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pilot access lifecycle" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Accessibility & Display" }));
    expect(screen.getByRole("heading", { name: "Accessibility & Display" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Account" })).not.toBeInTheDocument();
    expect(window.location.search).toBe("?section=accessibility");
  });

  it("renders and requests no admin feature data for an ordinary therapist", async () => {
    saveMockAccessSession({ role: "therapist", organizationId: "pilot_org_001", aal: "aal2" });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialSection="invitations" />);

    expect(await screen.findByRole("heading", { name: "Account" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Team" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Team" })).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps care-team mutations inside authorized settings and sends org-admin headers", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases") && !init?.method) {
        return jsonResponse([{ case_id: "case_demo_001", nickname: "Demo child", care_team_user_ids: ["therapist-demo"], primary_therapist_user_id: "therapist-demo" }]);
      }
      if (url.endsWith("/cases/case_demo_001/care-team") && init?.method === "POST") {
        const headers = new Headers(init.headers);
        expect(headers.get("X-Mock-Role")).toBe("org_admin");
        expect(JSON.parse(String(init.body))).toMatchObject({ user_id: "supervisor-demo", active: true });
        return jsonResponse({ assignment_id: "team-2", organization_id: "pilot_org_001", case_id: "case_demo_001", user_id: "supervisor-demo", role: "clinical_supervisor", active: true, is_primary: false });
      }
      if (url.endsWith("/cases/case_demo_001/care-team")) return jsonResponse([]);
      if (url.includes("/organizations/current/memberships")) return jsonResponse([{ membership_id: "mbr-2", organization_id: "pilot_org_001", user_id: "supervisor-demo", display_name: "Demo Supervisor", role: "clinical_supervisor", active: true, created_at: "2026-06-25T08:00:00Z" }]);
      if (url.includes("/organizations/current/invitations")) return jsonResponse([]);
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialSection="team" caseId="case_demo_001" />);

    expect(await screen.findByRole("heading", { name: "Care-team administration" })).toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Care-team role"), { target: { value: "clinical_supervisor" } });
    fireEvent.click(screen.getByRole("button", { name: "Assign" }));

    expect(await screen.findByText(/backend audit trail records this organization action/i)).toBeInTheDocument();
  });

  it("honors an authoritative organization-admin role without a mock session", async () => {
    window.sessionStorage.clear();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/organizations/current/memberships") || url.includes("/organizations/current/invitations")) {
        return jsonResponse([]);
      }
      return jsonResponse({});
    }));

    render(
      <SettingsWorkspaceClient
        confirmedAuthMode="mock"
        initialSection="team"
        role="org_admin"
        organizationId="clinic_001"
      />,
    );

    expect(await screen.findByRole("heading", { name: "Team" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Team" })).toHaveAttribute("aria-current", "page");
  });

  it("keeps admin controls separate with explicit pilot and audit warnings", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/organizations/current/readiness")) {
        return jsonResponse({
          organization_id: "pilot_org_001",
          checked_by: "admin-demo",
          role: "org_admin",
          environment: "local_pilot",
          pilot_ready: true,
          production_ready: false,
          active_memberships: 1,
          pending_invitations: 0,
          items: [
            {
              key: "auth_mode",
              label: "Production-capable auth",
              status: "blocked",
              detail: "Production SaaS requires Supabase auth with mock mode disabled.",
              evidence: ["auth_mode=mock", "mock_mode=true"],
              next_action: "Configure Supabase auth and set LINGUALENS_MOCK_MODE=false for production-like runtime."
            },
            {
              key: "mfa_policy",
              label: "AAL2 / MFA gate",
              status: "ready",
              detail: "AAL2 is required before clinical or admin workflow access.",
              evidence: ["supabase_require_mfa=true", "required_app_aal=aal2"],
              next_action: ""
            }
          ]
        });
      }
      if (url.includes("/organizations/current/memberships")) {
        return jsonResponse([
          {
            membership_id: "mem-admin",
            organization_id: "pilot_org_001",
            user_id: "admin-demo",
            display_name: "Pilot Org Admin",
            role: "org_admin",
            active: true,
            created_at: "2026-06-25T08:00:00Z"
          }
        ]);
      }
      if (url.includes("/organizations/current/invitations")) {
        return jsonResponse([]);
      }
      return jsonResponse({});
    }));

    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialSection="integration_status" />);

    expect(await screen.findByRole("heading", { name: "Integration Status" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Organization readiness cockpit" })).toBeInTheDocument();
    expect(screen.getByText("Pilot-ready, production blocked")).toBeInTheDocument();
    expect(screen.getByText("Production-capable auth")).toBeInTheDocument();
    expect(screen.getByText("Production SaaS requires Supabase auth with mock mode disabled.")).toBeInTheDocument();
    expect(screen.getByText("auth_mode=mock")).toBeInTheDocument();
    expect(screen.getByText(/Next action: Configure Supabase auth/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Admin safety boundaries" })).toBeInTheDocument();
    expect(screen.getByText("Real MFA enrollment")).toBeInTheDocument();
    expect(screen.getAllByText("Not configured").length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Account" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Audit" }));
    expect(screen.getByRole("heading", { name: "Audit" })).toBeInTheDocument();
    expect(screen.getByText("Break-glass access")).toBeInTheDocument();
    expect(screen.getByText("Audit trail available")).toBeInTheDocument();
  });

  it("renders backend-backed invitation and membership workflow state", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/organizations/current/memberships")) {
        return jsonResponse([
          {
            membership_id: "mem-therapist",
            organization_id: "pilot_org_001",
            user_id: "therapist-demo",
            display_name: "Demo Therapist",
            role: "therapist",
            active: true,
            created_at: "2026-06-25T08:00:00Z"
          }
        ]);
      }
      if (url.includes("/organizations/current/invitations")) {
        return jsonResponse([
          {
            invitation_id: "inv-001",
            organization_id: "pilot_org_001",
            email: "clinician@example.test",
            display_name: "Pilot Clinician",
            role: "therapist",
            status: "pending",
            invited_by: "admin-demo",
            expires_at: "2026-07-02T08:00:00Z",
            created_at: "2026-06-25T08:00:00Z"
          }
        ]);
      }
      return jsonResponse({});
    }));

    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialSection="invitations" />);

    expect(await screen.findByRole("heading", { name: "Pilot access lifecycle" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Loading organization settings...")).not.toBeInTheDocument());
    expect(await screen.findByText("Pilot Clinician")).toBeInTheDocument();
    expect(await screen.findByText("clinician@example.test")).toBeInTheDocument();
    expect(screen.getByText("This panel does not send real invitation emails or provision production MFA enrollment.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Team" }));
    expect(await screen.findByText("Demo Therapist")).toBeInTheDocument();
  });

  it("fails closed without rendering sample admin records when lifecycle payloads are malformed", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/organizations/current/memberships")) {
        return jsonResponse({ memberships: [] });
      }
      if (url.includes("/organizations/current/invitations")) {
        return jsonResponse({ invitations: [] });
      }
      return jsonResponse({});
    }));

    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialSection="invitations" />);

    expect(await screen.findByRole("status")).toHaveTextContent("Backend unavailable");
    expect(screen.queryByText("Pilot Org Admin")).not.toBeInTheDocument();
    expect(screen.queryByText("Pilot Clinician")).not.toBeInTheDocument();
    expect(screen.getByText("No invitation records returned by the backend.")).toBeInTheDocument();
  });

  it("creates an invitation through the org-admin API with scoped mock headers", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/organizations/current/memberships")) {
        return jsonResponse([]);
      }
      if (url.includes("/organizations/current/invitations") && init?.method === "POST") {
        const headers = new Headers(init.headers);
        expect(headers.get("X-Mock-Role")).toBe("org_admin");
        expect(JSON.parse(String(init.body))).toEqual({
          email: "new.clinician@example.test",
          display_name: "New Clinician",
          role: "therapist"
        });
        return jsonResponse({
          invitation_id: "inv-new",
          organization_id: "pilot_org_001",
          email: "new.clinician@example.test",
          display_name: "New Clinician",
          role: "therapist",
          status: "pending",
          invited_by: "admin-demo",
          expires_at: "2026-07-02T08:00:00Z",
          created_at: "2026-06-25T08:00:00Z"
        });
      }
      if (url.includes("/organizations/current/invitations")) {
        return jsonResponse([]);
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialSection="invitations" />);

    fireEvent.change(await screen.findByLabelText("Invite email"), { target: { value: "new.clinician@example.test" } });
    fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "New Clinician" } });
    fireEvent.click(screen.getByRole("button", { name: "Create invitation" }));

    expect(await screen.findByText("Invitation created for New Clinician.")).toBeInTheDocument();
    expect(screen.getByText("new.clinician@example.test")).toBeInTheDocument();
  });

  it("accepts an invitation, refreshes memberships, and prepares an aal1 invited session", async () => {
    let invitationAccepted = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/organizations/current/invitations/inv-001/accept")) {
        const headers = new Headers(init?.headers);
        expect(headers.get("X-Mock-Role")).toBe("org_admin");
        expect(JSON.parse(String(init?.body))).toEqual({
          user_id: "invite_clinician_example_test"
        });
        invitationAccepted = true;
        return jsonResponse({
          invitation_id: "inv-001",
          organization_id: "pilot_org_001",
          email: "clinician@example.test",
          display_name: "Pilot Clinician",
          role: "therapist",
          status: "accepted",
          invited_by: "admin-demo",
          accepted_user_id: "invite_clinician_example_test",
          expires_at: "2026-07-02T08:00:00Z",
          created_at: "2026-06-25T08:00:00Z",
          accepted_at: "2026-06-26T08:00:00Z"
        });
      }
      if (url.includes("/organizations/current/memberships")) {
        if (invitationAccepted) {
          return jsonResponse([
            {
              membership_id: "mem-therapist",
              organization_id: "pilot_org_001",
              user_id: "invite_clinician_example_test",
              display_name: "Pilot Clinician",
              role: "therapist",
              active: true,
              created_at: "2026-06-26T08:00:00Z"
            }
          ]);
        }
        return jsonResponse([]);
      }
      if (url.includes("/organizations/current/invitations")) {
        if (invitationAccepted) {
          return jsonResponse([
            {
              invitation_id: "inv-001",
              organization_id: "pilot_org_001",
              email: "clinician@example.test",
              display_name: "Pilot Clinician",
              role: "therapist",
              status: "accepted",
              invited_by: "admin-demo",
              accepted_user_id: "invite_clinician_example_test",
              expires_at: "2026-07-02T08:00:00Z",
              created_at: "2026-06-25T08:00:00Z",
              accepted_at: "2026-06-26T08:00:00Z"
            }
          ]);
        }
        return jsonResponse([
          {
            invitation_id: "inv-001",
            organization_id: "pilot_org_001",
            email: "clinician@example.test",
            display_name: "Pilot Clinician",
            role: "therapist",
            status: "pending",
            invited_by: "admin-demo",
            expires_at: "2026-07-02T08:00:00Z",
            created_at: "2026-06-25T08:00:00Z"
          }
        ]);
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialSection="invitations" />);

    await waitFor(() => expect(screen.queryByText("Loading organization settings...")).not.toBeInTheDocument());
    fireEvent.click(await screen.findByRole("button", { name: "Accept invite locally" }));

    expect(await screen.findByRole("button", { name: "Prepare mock MFA session" })).toBeInTheDocument();
    expect(screen.getAllByText("Pilot Clinician").length).toBeGreaterThan(0);
    expect(screen.getByText("Membership is active. Prepare an AAL1 invited session to validate the post-acceptance MFA gate.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Prepare mock MFA session" }));

    expect(await screen.findByRole("heading", { name: "Account" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Team" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Team" })).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem("lingualens.mock-access-session.v1")).toContain("\"aal\":\"aal1\"");
    expect(window.sessionStorage.getItem("lingualens.mock-access-session.v1")).toContain("\"role\":\"therapist\"");
  });

  it("revokes a membership and keeps the action visibly audited", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/organizations/current/invitations")) {
        return jsonResponse([]);
      }
      if (url.includes("/memberships/mem-therapist/revoke")) {
        const headers = new Headers(init?.headers);
        expect(headers.get("X-Mock-Role")).toBe("org_admin");
        return jsonResponse({
          membership_id: "mem-therapist",
          organization_id: "pilot_org_001",
          user_id: "therapist-demo",
          display_name: "Demo Therapist",
          role: "therapist",
          active: false,
          created_at: "2026-06-25T08:00:00Z"
        });
      }
      if (url.includes("/organizations/current/memberships")) {
        return jsonResponse([
          {
            membership_id: "mem-therapist",
            organization_id: "pilot_org_001",
            user_id: "therapist-demo",
            display_name: "Demo Therapist",
            role: "therapist",
            active: true,
            created_at: "2026-06-25T08:00:00Z"
          }
        ]);
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialScope="admin" />);

    await waitFor(() => expect(screen.queryByText("Loading organization settings...")).not.toBeInTheDocument());

    fireEvent.click(await screen.findByRole("button", { name: "Revoke Demo Therapist" }));

    expect(await screen.findByText("Membership revoked for Demo Therapist. Care-team assignments are deactivated by the backend.")).toBeInTheDocument();
    expect(screen.getByText("Inactive")).toBeInTheDocument();
  });

  it("refetches admin lifecycle state when the active organization session changes", async () => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "org_admin",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const headers = new Headers(init?.headers);
      const orgId = headers.get("X-Organization-Id");

      if (url.includes("/organizations/current/memberships")) {
        return jsonResponse(orgId === "pilot_org_ops"
          ? [{
              membership_id: "mem-ops",
              organization_id: "pilot_org_ops",
              user_id: "ops-admin",
              display_name: "Operations Admin",
              role: "org_admin",
              active: true,
              created_at: "2026-06-26T08:00:00Z"
            }]
          : [{
              membership_id: "mem-pilot",
              organization_id: "pilot_org_001",
              user_id: "pilot-admin",
              display_name: "Pilot Org Admin",
              role: "org_admin",
              active: true,
              created_at: "2026-06-25T08:00:00Z"
            }]);
      }
      if (url.includes("/organizations/current/invitations")) {
        return jsonResponse(orgId === "pilot_org_ops"
          ? [{
              invitation_id: "inv-ops",
              organization_id: "pilot_org_ops",
              email: "ops@example.test",
              display_name: "Ops Invite",
              role: "therapist",
              status: "pending",
              invited_by: "ops-admin",
              expires_at: "2026-07-02T08:00:00Z",
              created_at: "2026-06-26T08:00:00Z"
            }]
          : []);
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialScope="admin" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading organization settings...")).not.toBeInTheDocument();
    });
    await waitFor(() => {
      expect(getRequestedOrganizationIds(fetchMock, "/organizations/current/memberships")).toContain("pilot_org_001");
    });

    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "org_admin",
      organizationId: "pilot_org_ops",
      aal: "aal2",
    }));
    act(() => {
      window.dispatchEvent(new CustomEvent("lingualens:mock-access-session-changed"));
    });

    expect(await screen.findByRole("button", { name: "Revoke Operations Admin" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Invitations" }));
    expect(screen.getByText("Ops Invite")).toBeInTheDocument();
    expect(getRequestedOrganizationIds(fetchMock, "/organizations/current/memberships")).toContain("pilot_org_ops");
  });

  it("ignores an admin mutation response after the active organization changes", async () => {
    const createResponse = deferred<Response>();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/organizations/current/invitations") && init?.method === "POST") {
        return createResponse.promise;
      }
      if (url.includes("/organizations/current/memberships") || url.includes("/organizations/current/invitations")) {
        return jsonResponse([]);
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SettingsWorkspaceClient confirmedAuthMode="mock" initialSection="invitations" />);
    fireEvent.change(await screen.findByLabelText("Invite email"), {
      target: { value: "cross-org@example.test" },
    });
    fireEvent.change(screen.getByLabelText("Display name"), {
      target: { value: "Cross Org Clinician" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create invitation" }));

    act(() => {
      saveMockAccessSession({ role: "org_admin", organizationId: "pilot_org_ops", aal: "aal2" });
    });

    await act(async () => {
      createResponse.resolve(new Response(JSON.stringify({
        invitation_id: "inv-old-org",
        organization_id: "pilot_org_001",
        email: "cross-org@example.test",
        display_name: "Cross Org Clinician",
        role: "therapist",
        status: "pending",
        invited_by: "admin-demo",
        expires_at: "2026-07-02T08:00:00Z",
        created_at: "2026-06-25T08:00:00Z",
      }), { headers: { "content-type": "application/json" } }));
      await createResponse.promise;
    });

    await waitFor(() => {
      expect(getRequestedOrganizationIds(fetchMock, "/organizations/current/memberships")).toContain("pilot_org_ops");
    });
    expect(screen.queryByText("Invitation created for Cross Org Clinician.")).not.toBeInTheDocument();
  });
});

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init
  }));
}

function getRequestedOrganizationIds(fetchMock: ReturnType<typeof vi.fn>, pathFragment: string) {
  return fetchMock.mock.calls
    .filter(([input]) => String(input).includes(pathFragment))
    .map(([, init]) => new Headers(init?.headers).get("X-Organization-Id"));
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}
