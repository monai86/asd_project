"use client";

import { useEffect, useState } from "react";

import { loadMockAccessSession, MOCK_ACCESS_SESSION_EVENT, type MockAccessSession } from "@/lib/mock-access-session";

export function useMockAccessSession() {
  const [session, setSession] = useState<MockAccessSession | null>(null);

  useEffect(() => {
    const syncSession = () => setSession(loadMockAccessSession());
    syncSession();
    window.addEventListener(MOCK_ACCESS_SESSION_EVENT, syncSession);
    return () => window.removeEventListener(MOCK_ACCESS_SESSION_EVENT, syncSession);
  }, []);

  return session;
}
