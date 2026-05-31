export const AUTH_SESSION_STORAGE_KEY = "asdProject.therapistClinician.authSession.v1";

function hasStorageShape(storage) {
  return storage && typeof storage.getItem === "function" && typeof storage.setItem === "function";
}

export function createAuthSessionStore({
  storage = typeof window !== "undefined" ? window.sessionStorage : null,
  storageKey = AUTH_SESSION_STORAGE_KEY
} = {}) {
  return {
    load() {
      if (!hasStorageShape(storage)) return null;
      const raw = storage.getItem(storageKey);
      if (!raw) return null;
      try {
        return JSON.parse(raw);
      } catch {
        storage.removeItem?.(storageKey);
        return null;
      }
    },

    save(session) {
      if (!hasStorageShape(storage)) return null;
      storage.setItem(storageKey, JSON.stringify(session));
      return session;
    },

    clear() {
      if (storage && typeof storage.removeItem === "function") {
        storage.removeItem(storageKey);
      }
    }
  };
}

export const authSessionStore = createAuthSessionStore();
