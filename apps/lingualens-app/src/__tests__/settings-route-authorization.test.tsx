import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SettingsPage from "@/app/settings/page";
import { MOCK_ACCESS_SESSION_KEY, saveMockAccessSession } from "@/lib/mock-access-session";
import { saveSupabaseAccessSession } from "@/lib/supabase-access-session";
import { saveSupabaseBrowserAuthSnapshot } from "@/lib/supabase-browser-auth";

const { routerReplace, runtimeSettingsState, mockRuntimeSettings, useRuntimeSettingsMock } = vi.hoisted(() => {
  const settings = {
    mock_mode: true,
    auth_mode: "mock" as const,
    model_version: "test",
    feature_schema: "test",
    guideline_mapping: "review-support-only",
    user_roles: ["therapist", "clinical_supervisor", "org_admin"],
    access_model: {
      invitation_only: true,
      required_app_aal: "aal2" as const,
      active_organization_session: "explicit_selection_when_ambiguous",
      production_mock_mode: "local_only",
    },
    data_retention: "local test data",
    consent_policy: "visible per case",
    capabilities: {},
    pipeline_settings: {},
  };
  const runtimeState = {
    current: { status: "success", mode: "backend", data: settings },
  } as { current: Record<string, unknown> };
  return {
    routerReplace: vi.fn(),
    runtimeSettingsState: runtimeState,
    mockRuntimeSettings: settings,
    useRuntimeSettingsMock: vi.fn(() => runtimeState.current),
  };
});

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: useRuntimeSettingsMock,
}));

vi.mock("@/components/sidebar", () => ({ Sidebar: () => null }));
vi.mock("@/components/topbar", () => ({ Topbar: () => null }));
vi.mock("@/components/mobile-header", () => ({ MobileHeader: () => null }));
vi.mock("@/components/supabase-auth-runtime-bridge", () => ({ SupabaseAuthRuntimeBridge: () => null }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: routerReplace,
    prefetch: vi.fn(),
    refresh: vi.fn(),
  }),
}));

async function renderSettingsPage(searchParams?: Record<string, string | string[] | undefined>) {
  render(await SettingsPage({ searchParams: searchParams ? Promise.resolve(searchParams) : undefined }));
}

function saveBrowserMockSession(role: string) {
  if (role === "platform_operator") {
    saveSupabaseAccessSession({
      stage: "authenticated",
      role: "platform_operator",
      organizationId: "pilot_org_001",
      aal: "aal2",
      userId: "platform-operator-test",
    });
    return;
  }
  window.sessionStorage.setItem(MOCK_ACCESS_SESSION_KEY, JSON.stringify({
    role,
    organizationId: "pilot_org_001",
    aal: "aal2",
  }));
}

function setRuntimeAuthMode(authMode: "mock" | "supabase") {
  runtimeSettingsState.current = {
    status: "success",
    mode: "backend",
    data: {
      ...mockRuntimeSettings,
      mock_mode: authMode === "mock",
      auth_mode: authMode,
    },
  };
}

function stubAdminApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/organization-readiness")) {
      return new Response(JSON.stringify({ status: "ready", items: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify([]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  runtimeSettingsState.current = { status: "success", mode: "backend", data: mockRuntimeSettings };
  useRuntimeSettingsMock.mockReset();
  useRuntimeSettingsMock.mockImplementation(() => runtimeSettingsState.current);
  routerReplace.mockReset();
  window.sessionStorage.clear();
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("settings route authorization", () => {
  it("reuses the shell-confirmed runtime setting for an admin route without a child refetch or profile fallback", async () => {
    saveBrowserMockSession("org_admin");
    stubAdminApi();
    useRuntimeSettingsMock
      .mockImplementationOnce(() => runtimeSettingsState.current)
      .mockImplementation(() => ({ status: "error", mode: "backend", message: "duplicate request failed" }));

    await renderSettingsPage({ section: "team" });

    expect(await screen.findByRole("heading", { name: "Pilot admin controls" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Profile" })).not.toBeInTheDocument();
    expect(routerReplace).not.toHaveBeenCalled();
    expect(useRuntimeSettingsMock).toHaveBeenCalledTimes(1);
  });

  it("validates the server query and ignores a forged role query", async () => {
    saveMockAccessSession({ role: "therapist", organizationId: "pilot_org_001", aal: "aal2" });

    await renderSettingsPage({ section: "audit", role: "org_admin" });

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    await waitFor(() => {
      expect(routerReplace).toHaveBeenCalledWith("/settings?section=profile&notice=not-authorized");
    });
    expect(screen.queryByRole("button", { name: "Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pilot admin controls" })).not.toBeInTheDocument();
  });

  it.each([
    ["therapist", "team"],
    ["therapist", "audit"],
    ["clinical_supervisor", "team"],
    ["clinical_supervisor", "audit"],
    ["platform_operator", "team"],
    ["platform_operator", "audit"],
  ] as const)("redirects %s away from a direct %s deep link without loading admin data", async (role, section) => {
    saveBrowserMockSession(role);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await renderSettingsPage({ section });

    await waitFor(() => {
      expect(routerReplace).toHaveBeenCalledWith("/settings?section=profile&notice=not-authorized");
    });
    expect(await screen.findByRole("heading", { name: "Profile" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("You do not have access to that settings section.");
    expect(screen.queryByRole("button", { name: "Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pilot admin controls" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create invitation" })).not.toBeInTheDocument();
    expect(screen.queryByText("Audit & break-glass")).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each(["team", "audit"] as const)("retains an organization-admin direct %s deep link and loads admin data", async (section) => {
    saveBrowserMockSession("org_admin");
    const fetchMock = stubAdminApi();

    await renderSettingsPage({ section });

    expect(await screen.findByRole("heading", { name: "Pilot admin controls" })).toBeInTheDocument();
    expect(routerReplace).not.toHaveBeenCalled();
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: "Admin" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create invitation" })).toBeInTheDocument();
  });

  it("uses only the confirmed mock identity when a stale Supabase admin session exists", async () => {
    setRuntimeAuthMode("mock");
    saveMockAccessSession({ role: "therapist", organizationId: "pilot_org_001", aal: "aal2" });
    saveSupabaseAccessSession({
      stage: "authenticated",
      role: "org_admin",
      organizationId: "stale_supabase_org",
      aal: "aal2",
      userId: "stale-admin",
    });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await renderSettingsPage({ section: "team" });

    await waitFor(() => expect(routerReplace).toHaveBeenCalledWith("/settings?section=profile&notice=not-authorized"));
    expect(screen.queryByRole("button", { name: "Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pilot admin controls" })).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("authorizes the current mock admin even when a stale Supabase therapist session exists", async () => {
    setRuntimeAuthMode("mock");
    saveMockAccessSession({ role: "org_admin", organizationId: "pilot_org_001", aal: "aal2" });
    saveSupabaseAccessSession({
      stage: "authenticated",
      role: "therapist",
      organizationId: "stale_supabase_org",
      aal: "aal2",
      userId: "stale-therapist",
    });
    const fetchMock = stubAdminApi();

    await renderSettingsPage({ section: "team" });

    expect(await screen.findByRole("heading", { name: "Pilot admin controls" })).toBeInTheDocument();
    expect(routerReplace).not.toHaveBeenCalled();
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  });

  it.each([
    [undefined, "missing"],
    ["therapist", "therapist"],
  ] as const)("uses only the confirmed Supabase identity when its role is %s", async (supabaseRole, _roleLabel) => {
    setRuntimeAuthMode("supabase");
    saveMockAccessSession({ role: "org_admin", organizationId: "stale_mock_org", aal: "aal2" });
    saveSupabaseAccessSession({
      stage: "authenticated",
      role: supabaseRole,
      organizationId: "pilot_org_001",
      aal: "aal2",
      userId: "supabase-user",
    });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await renderSettingsPage({ section: "audit" });

    await waitFor(() => expect(routerReplace).toHaveBeenCalledWith("/settings?section=profile&notice=not-authorized"));
    expect(screen.queryByRole("button", { name: "Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pilot admin controls" })).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("fails closed without redirect or admin loading while runtime auth mode is unresolved", async () => {
    runtimeSettingsState.current = { status: "loading", mode: "backend" };
    saveMockAccessSession({ role: "org_admin", organizationId: "stale_mock_org", aal: "aal2" });
    saveSupabaseAccessSession({
      stage: "authenticated",
      role: "org_admin",
      organizationId: "stale_supabase_org",
      aal: "aal2",
      userId: "stale-admin",
    });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await renderSettingsPage({ section: "team" });

    expect(routerReplace).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pilot admin controls" })).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("does not redirect before a saved mock organization-admin session hydrates", async () => {
    saveBrowserMockSession("org_admin");
    stubAdminApi();

    await renderSettingsPage({ section: "team" });

    expect(routerReplace).not.toHaveBeenCalled();
    expect(await screen.findByRole("heading", { name: "Pilot admin controls" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Admin" })).toBeInTheDocument());
    expect(routerReplace).not.toHaveBeenCalled();
  });

  it("does not redirect a saved Supabase organization-admin session during hydration", async () => {
    setRuntimeAuthMode("supabase");
    saveMockAccessSession({ role: "therapist", organizationId: "stale_mock_org", aal: "aal2" });
    saveSupabaseBrowserAuthSnapshot({
      userId: "admin-test",
      email: "admin@example.test",
      aal: "aal2",
      appMetadata: {
        role: "org_admin",
        membership_active: true,
        invitation_status: "accepted",
        organization_id: "pilot_org_001",
        organizations: [{
          organizationId: "pilot_org_001",
          label: "Pilot organization",
          role: "org_admin",
        }],
      },
    });
    saveSupabaseAccessSession({
      stage: "authenticated",
      role: "org_admin",
      organizationId: "pilot_org_001",
      aal: "aal2",
      userId: "admin-test",
    });
    stubAdminApi();

    await renderSettingsPage({ section: "audit" });

    expect(await screen.findByRole("heading", { name: "Pilot admin controls" })).toBeInTheDocument();
    expect(routerReplace).not.toHaveBeenCalled();
  });

  it("safe-defaults missing and invalid sections to profile", async () => {
    saveMockAccessSession({ role: "org_admin", organizationId: "pilot_org_001", aal: "aal2" });

    await renderSettingsPage({ section: "not-a-section", scope: "admin-ish" });

    expect(await screen.findByRole("heading", { name: "Profile" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pilot admin controls" })).not.toBeInTheDocument();
    expect(routerReplace).not.toHaveBeenCalled();
  });
});
