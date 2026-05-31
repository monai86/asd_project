export function createSupabaseAuthProvider({
  client = null,
  sessionStore = null
} = {}) {
  return {
    async signIn(email, password) {
      if (!client?.auth?.signInWithPassword) {
        return {
          user: null,
          error: "Supabase auth client is not configured. Use AUTH_MODE=mock or configure Supabase before sign-in."
        };
      }

      const { data, error } = await client.auth.signInWithPassword({ email, password });
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

    async restoreSession() {
      if (!client?.auth?.getUser) {
        return { user: null, session: null, error: "" };
      }
      const { data, error } = await client.auth.getUser();
      if (error || !data?.user) {
        sessionStore?.clear();
        return { user: null, session: null, error: error?.message || "" };
      }
      const user = mapSupabaseUser(data.user);
      return { user, session: { mode: "supabase", user }, error: "" };
    },

    async signOut() {
      if (client?.auth?.signOut) {
        await client.auth.signOut();
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
