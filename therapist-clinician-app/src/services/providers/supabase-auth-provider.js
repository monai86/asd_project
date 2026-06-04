import { supabase } from "../supabase-client.js";

export function createSupabaseAuthProvider({
  client = null,
  sessionStore = null
} = {}) {
  return {
    async signUp(email, password, name, role, organization) {
      const activeClient = client || supabase;
      if (!activeClient?.auth?.signUp) {
        return {
          user: null,
          error: "Supabase auth client is not configured for registration."
        };
      }

      const { data, error } = await activeClient.auth.signUp({
        email,
        password,
        options: {
          data: {
            name,
            role,
            organization,
            credentials: role === "admin" ? "Systems Administrator" : (role === "clinician" ? "MD Clinician" : "Certified Speech Therapist")
          }
        }
      });

      if (error) return { user: null, error: error.message || "Supabase sign-up failed." };
      const user = data?.user ? mapSupabaseUser(data.user) : null;
      return { user, error: "" };
    },

    async signIn(email, password) {
      const activeClient = client || supabase;
      if (!activeClient?.auth?.signInWithPassword) {
        return {
          user: null,
          error: "Supabase auth client is not configured. Use AUTH_MODE=mock or configure Supabase before sign-in."
        };
      }

      const { data, error } = await activeClient.auth.signInWithPassword({ email, password });
      if (error) return { user: null, error: error.message || "Supabase sign-in failed." };
      const user = data?.user ? mapSupabaseUser(data.user) : null;
      const session = {
        mode: "supabase",
        access_token: data?.session?.access_token || null,
        refresh_token: data?.session?.refresh_token || null,
        user
      };
      sessionStore?.save(session);
      return { user, session, error: "" };
    },

    async restoreSession(session) {
      const activeClient = client || supabase;
      if (!activeClient?.auth?.getUser) {
        return { user: null, session: null, error: "" };
      }
      const { data, error } = await activeClient.auth.getUser();
      if (error || !data?.user) {
        sessionStore?.clear();
        return { user: null, session: null, error: error?.message || "" };
      }
      const user = mapSupabaseUser(data.user);
      return { user, session: { mode: "supabase", user }, error: "" };
    },

    async signOut() {
      const activeClient = client || supabase;
      if (activeClient?.auth?.signOut) {
        await activeClient.auth.signOut();
      }
      sessionStore?.clear();
      return { user: null, error: "" };
    }
  };
}

function mapSupabaseUser(user) {
  const metadata = user.user_metadata || {};
  const appMetadata = user.app_metadata || {};
  return {
    user_id: user.id,
    email: user.email,
    name: metadata.name || user.email || "Clinical User",
    credentials: metadata.credentials || "",
    role: appMetadata.role || metadata.role || "therapist",
    organization: metadata.organization || "",
    last_login: new Date().toISOString()
  };
}
