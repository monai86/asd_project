import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsWorkspaceClient } from "@/components/settings-workspace-client";

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("SettingsWorkspaceClient admin lifecycle UX", () => {
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
    expect(screen.getByText("Pilot Clinician")).toBeInTheDocument();
    expect(screen.getByText("clinician@example.test")).toBeInTheDocument();
    expect(screen.getByText("Demo Therapist")).toBeInTheDocument();
    expect(screen.getByText("Invitation and MFA are enforced by backend guards in production-capable auth mode.")).toBeInTheDocument();
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
});

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init
  }));
}
