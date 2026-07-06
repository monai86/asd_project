import { beforeEach, describe, expect, it, vi } from "vitest";

import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";

const signOut = vi.fn();

vi.mock("@/lib/supabase-browser-client", () => ({
  getSupabaseBrowserClient: () => ({
    auth: {
      signOut,
    },
  }),
}));

describe("signOutSupabaseWorkspace", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
    signOut.mockReset();
    signOut.mockResolvedValue({ error: null });
  });

  it("clears browser auth, app access session, and cached bearer token", async () => {
    window.sessionStorage.setItem("lingualens.supabase-session-token.v1", "token");
    window.sessionStorage.setItem("lingualens.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      aal: "aal2",
      appMetadata: {
        role: "therapist",
        membership_active: true,
        invitation_status: "accepted",
        organization_id: "clinic_001",
      },
    }));
    window.sessionStorage.setItem("lingualens.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      role: "therapist",
      aal: "aal2",
      organizationId: "clinic_001",
    }));
    window.localStorage.setItem("lingualens.supabase-organization-hint.v1", JSON.stringify({
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      organizationId: "clinic_001",
    }));

    await signOutSupabaseWorkspace();

    expect(signOut).toHaveBeenCalledOnce();
    expect(window.sessionStorage.getItem("lingualens.supabase-session-token.v1")).toBeNull();
    expect(window.sessionStorage.getItem("lingualens.supabase-browser-auth.v1")).toBeNull();
    expect(window.localStorage.getItem("lingualens.supabase-organization-hint.v1")).toBeNull();
    expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"stage\":\"signed_out\"");
  });
});
