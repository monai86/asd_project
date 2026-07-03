import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadPersistedSupabaseSessionFromStorage } from "@/lib/supabase-auth-runtime";

describe("supabase auth runtime", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("loads a persisted Supabase session from the browser auth-token key", () => {
    window.localStorage.setItem("sb-cbhwxklvcpgizeqriqxi-auth-token", JSON.stringify({
      access_token: "access-token",
      refresh_token: "refresh-token",
      aal: "aal2",
      user: {
        id: "user_org_admin_a",
        email: "org.admin.a@lingualens-staging.test",
        app_metadata: {
          role: "org_admin",
          membership_active: true,
          invitation_status: "accepted",
          organization_id: "org_lingualens_a",
        },
      },
    }));

    expect(loadPersistedSupabaseSessionFromStorage()).toMatchObject({
      access_token: "access-token",
      aal: "aal2",
      user: {
        id: "user_org_admin_a",
        email: "org.admin.a@lingualens-staging.test",
      },
    });
  });

  it("returns null when the persisted browser record is missing required session fields", () => {
    window.localStorage.setItem("sb-cbhwxklvcpgizeqriqxi-auth-token", JSON.stringify({
      token_type: "bearer",
    }));

    expect(loadPersistedSupabaseSessionFromStorage()).toBeNull();
  });
});
