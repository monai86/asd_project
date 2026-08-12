import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchCases, fetchSession } from "@/lib/api-client";

describe("api-client resilience", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns fallback data gracefully when backend fetch fails for cases", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network Error")));
    const cases = await fetchCases();
    expect(Array.isArray(cases)).toBe(true);
    expect(cases.length).toBeGreaterThan(0);
  });

  it("returns fallback data gracefully when backend fetch fails for session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network Error")));
    const session = await fetchSession("session-123");
    expect(session).toBeDefined();
    expect(session.id).toBe("session-123");
    expect(session.caseId).toBeDefined();
  });
});
