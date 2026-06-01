import { describe, expect, it, vi } from "vitest";
import { createApiRepository } from "../persistence/api-repository.js";

function createClient() {
  return {
    get: vi.fn(async path => {
      if (path === "/api/me") return { user: { user_id: "therapist_a", role: "therapist" } };
      if (path === "/api/cases") return [{ case_id: "CASE-A", owner_user_id: "therapist_a" }];
      if (path === "/api/sessions") return [{ session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" }];
      if (path === "/api/sessions/SESSION-A/reference-comparison") return { status: "ok", cohorts: [] };
      if (path === "/api/cases/CASE-A/progress") return { case_id: "CASE-A", n_sessions: 1 };
      if (path === "/api/audit-logs") return [{ audit_id: "AUDIT-A", actor_user_id: "therapist_a" }];
      return null;
    }),
    post: vi.fn(async (path, body) => ({ path, body })),
    patch: vi.fn(async (path, body) => ({ path, body }))
  };
}

describe("API repository boundary", () => {
  it("hydrates frontend snapshot collections from backend routes", async () => {
    const client = createClient();
    const repository = createApiRepository({ apiClient: client });

    const snapshot = await repository.hydrate();

    expect(snapshot.users).toEqual([{ user_id: "therapist_a", role: "therapist" }]);
    expect(snapshot.child_cases).toHaveLength(1);
    expect(snapshot.sessions).toHaveLength(1);
    expect(snapshot.consent_records).toEqual([]);
    expect(client.get).toHaveBeenCalledWith("/api/cases");
  });

  it("uses explicit case, consent, session, transcript line, and progress routes", async () => {
    const client = createClient();
    const repository = createApiRepository({ apiClient: client });

    await repository.createCase({ anonymized_child_code: "CHI-A" });
    await repository.patchCase("CASE-A", { notes: "updated" });
    await repository.recordConsent("CASE-A", { audio_permission: true });
    await repository.createSession({ case_id: "CASE-A" });
    await repository.patchSession("SESSION-A", { notes: "updated" });
    await repository.patchTranscriptLine("TRANSCRIPT-A", "LINE-A", { text: "corrected", expected_version: 1 });
    await repository.getReferenceComparison("SESSION-A");
    await repository.getCaseProgress("CASE-A");
    await repository.createProgressReport("SESSION-A");

    expect(client.post).toHaveBeenCalledWith("/api/cases", { anonymized_child_code: "CHI-A" });
    expect(client.patch).toHaveBeenCalledWith("/api/cases/CASE-A", { notes: "updated" });
    expect(client.post).toHaveBeenCalledWith("/api/cases/CASE-A/consent", { audio_permission: true });
    expect(client.post).toHaveBeenCalledWith("/api/sessions", { case_id: "CASE-A" });
    expect(client.patch).toHaveBeenCalledWith("/api/sessions/SESSION-A", { notes: "updated" });
    expect(client.patch).toHaveBeenCalledWith("/api/transcripts/TRANSCRIPT-A/lines/LINE-A", {
      text: "corrected",
      expected_version: 1
    });
    expect(client.get).toHaveBeenCalledWith("/api/sessions/SESSION-A/reference-comparison");
    expect(client.get).toHaveBeenCalledWith("/api/cases/CASE-A/progress");
    expect(client.post).toHaveBeenCalledWith("/api/sessions/SESSION-A/report", {});
  });
});
