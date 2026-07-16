import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  it("renders therapist settings cards with privacy and consent reminders", () => {
    render(<SettingsWorkspaceClient initialScope="therapist" />);

    expect(screen.getByRole("heading", { name: "Profile" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Preferences" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Notification preferences" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Export/report preferences" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Security" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Help & guidance" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Privacy & consent reminder" })).toBeInTheDocument();
    expect(screen.getByText("Demo mode")).toBeInTheDocument();
    expect(screen.getAllByText("Not configured").length).toBeGreaterThan(0);
    expect(screen.getByText("No HIPAA compliance claim is made by this prototype workspace.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pilot access lifecycle" })).not.toBeInTheDocument();
  });

  it("renders and requests no admin feature data for an ordinary therapist", async () => {
    saveMockAccessSession({ role: "therapist", organizationId: "pilot_org_001", aal: "aal2" });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<SettingsWorkspaceClient initialScope="admin" />);

    expect(await screen.findByRole("heading", { name: "Profile" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pilot admin controls" })).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
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
        initialSection="team"
        role="org_admin"
        organizationId="clinic_001"
      />,
    );

    expect(await screen.findByRole("heading", { name: "Pilot admin controls" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Admin" })).toBeInTheDocument();
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

    render(<SettingsWorkspaceClient initialScope="admin" />);

    expect(await screen.findByRole("heading", { name: "Pilot admin controls" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Organization readiness cockpit" })).toBeInTheDocument();
    expect(screen.getByText("Pilot-ready, production blocked")).toBeInTheDocument();
    expect(screen.getByText("Production-capable auth")).toBeInTheDocument();
    expect(screen.getByText("Production SaaS requires Supabase auth with mock mode disabled.")).toBeInTheDocument();
    expect(screen.getByText("auth_mode=mock")).toBeInTheDocument();
    expect(screen.getByText(/Next action: Configure Supabase auth/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pilot access lifecycle" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Admin safety boundaries" })).toBeInTheDocument();
    expect(screen.getByText("Break-glass access")).toBeInTheDocument();
    expect(screen.getByText("Audit trail available")).toBeInTheDocument();
    expect(screen.getByText("Real MFA enrollment")).toBeInTheDocument();
    expect(screen.getAllByText("Not configured").length).toBeGreaterThan(0);
    expect(screen.getByText("These controls are pilot/admin lifecycle tools, not production account management.")).toBeInTheDocument();
    expect(screen.getByText("This panel does not send real invitation emails, does not represent the production Supabase acceptance path, and cannot provision production MFA enrollment on its own.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Profile" })).not.toBeInTheDocument();
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

    render(<SettingsWorkspaceClient initialScope="admin" />);

    expect(await screen.findByRole("heading", { name: "Pilot access lifecycle" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Loading pilot access lifecycle...")).not.toBeInTheDocument());
    expect(await screen.findByText("Pilot Clinician")).toBeInTheDocument();
    expect(await screen.findByText("clinician@example.test")).toBeInTheDocument();
    expect(await screen.findByText("Demo Therapist")).toBeInTheDocument();
    expect(screen.getByText("Production invitation delivery and acceptance stay outside this panel. This pilot UI exists only to exercise local lifecycle scaffolding and backend guard behavior.")).toBeInTheDocument();
  });

  it("fails closed to local workspace mode when admin lifecycle payloads are malformed", async () => {
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

    render(<SettingsWorkspaceClient initialScope="admin" />);

    expect(await screen.findByRole("status")).toHaveTextContent("Backend unavailable");
    expect(screen.getByText("Pilot Org Admin")).toBeInTheDocument();
    expect(screen.getByText("Pilot Clinician")).toBeInTheDocument();
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

    render(<SettingsWorkspaceClient initialScope="admin" />);

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

    render(<SettingsWorkspaceClient initialScope="admin" />);

    await waitFor(() => expect(screen.queryByText("Loading pilot access lifecycle...")).not.toBeInTheDocument());
    fireEvent.click(await screen.findByRole("button", { name: "Accept invite locally" }));

    expect(await screen.findByRole("button", { name: "Prepare mock MFA session" })).toBeInTheDocument();
    expect(screen.getAllByText("Pilot Clinician").length).toBeGreaterThan(0);
    expect(screen.getByText("Membership is active. Prepare an AAL1 invited session to validate the post-acceptance MFA gate.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Prepare mock MFA session" }));

    expect(await screen.findByRole("heading", { name: "Profile" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pilot admin controls" })).not.toBeInTheDocument();
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

    render(<SettingsWorkspaceClient initialScope="admin" />);

    await waitFor(() => expect(screen.queryByText("Loading pilot access lifecycle...")).not.toBeInTheDocument());

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

    render(<SettingsWorkspaceClient initialScope="admin" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading pilot access lifecycle...")).not.toBeInTheDocument();
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

    render(<SettingsWorkspaceClient initialScope="admin" />);
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
