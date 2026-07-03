import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadPersistedSupabaseSessionFromStorage } from "@/lib/supabase-auth-runtime";

function createUnsignedJwt(payload: Record<string, unknown>) {
  const encode = (value: Record<string, unknown>) =>
    btoa(JSON.stringify(value)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  return `${encode({ alg: "none", typ: "JWT" })}.${encode(payload)}.`;
}

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

  it("derives aal from the access token when Supabase storage omits the aal field", () => {
    window.localStorage.setItem("sb-cbhwxklvcpgizeqriqxi-auth-token", JSON.stringify({
      access_token: createUnsignedJwt({ aal: "aal2" }),
      refresh_token: "refresh-token",
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
      aal: "aal2",
      user: {
        id: "user_org_admin_a",
      },
    });
  });
});
