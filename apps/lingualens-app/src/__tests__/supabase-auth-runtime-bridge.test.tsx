import { cleanup, render, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SUPABASE_SESSION_SOURCE_EVENT } from "@/lib/supabase-session-source";

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "supabase" },
  }),
}));

vi.mock("@/lib/supabase-auth-runtime", () => ({
  ensureSupabaseAuthRuntimeSync: () => {
    window.dispatchEvent(new CustomEvent(SUPABASE_SESSION_SOURCE_EVENT, {
      detail: {
        kind: "session",
        session: {
          aal: "aal2",
          access_token: "test-access-token",
          user: {
            id: "user_org_admin_a",
            email: "org.admin.a@lingualens-staging.test",
            app_metadata: {
              role: "org_admin",
              membership_active: true,
              invitation_status: "accepted",
              organization_id: "org_lingualens_a",
              organizations: [
                {
                  organization_id: "org_lingualens_a",
                  name: "LinguaLens",
                  role: "org_admin",
                  active: true,
                },
              ],
            },
            user_metadata: {
              display_name: "Org Admin A",
            },
          },
        },
      },
    }));
  },
}));

describe("SupabaseAuthRuntimeBridge", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("captures an immediate session event emitted during runtime sync startup", async () => {
    render(<SupabaseAuthRuntimeBridge />);

    await waitFor(() => {
      expect(window.sessionStorage.getItem("lingualens.supabase-session-token.v1")).toBe("test-access-token");
      expect(window.sessionStorage.getItem("lingualens.supabase-browser-auth.v1")).toContain("\"organization_id\":\"org_lingualens_a\"");
      expect(window.sessionStorage.getItem("lingualens.supabase-access-session.v1")).toContain("\"stage\":\"authenticated\"");
    });
  });
});
