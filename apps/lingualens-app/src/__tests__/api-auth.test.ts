import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  apiBlob,
  apiRequest,
  apiUploadBlob,
  getRuntimeSettings,
  resetApiRuntimeSettingsCacheForTests,
} from "@/lib/api";
import { exportBackendReport, exportReviewedCha } from "@/lib/workflow";

const getSession = vi.fn();

vi.mock("@/lib/supabase-browser-client", () => ({
  getSupabaseBrowserClient: () => ({
    auth: {
      getSession,
    },
  }),
}));

describe("api auth headers", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    getSession.mockReset();
    resetApiRuntimeSettingsCacheForTests();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("sends bearer auth and active organization headers in supabase runtime", async () => {
    window.sessionStorage.setItem("lingualens.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      role: "therapist",
      aal: "aal2",
      organizationId: "clinic_001",
      availableOrganizations: [
        { organizationId: "clinic_001", label: "LinguaLens Clinic" },
      ],
    }));
    window.sessionStorage.setItem("lingualens.supabase-session-token.v1", "supabase-access-token");

    getSession.mockResolvedValue({
      data: { session: null },
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "lingualens-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer supabase-access-token");
      expect(headers.get("X-Organization-Id")).toBe("clinic_001");
      expect(headers.get("X-User-Id")).toBeNull();
      return jsonResponse({ ok: true });
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    await apiRequest("/protected");
    expect(getSession).not.toHaveBeenCalled();
  });

  it("sends bearer auth headers for blob downloads in supabase runtime", async () => {
    window.sessionStorage.setItem("lingualens.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      role: "therapist",
      aal: "aal2",
      organizationId: "clinic_001",
    }));
    window.sessionStorage.setItem("lingualens.supabase-session-token.v1", "supabase-access-token");

    getSession.mockResolvedValue({
      data: { session: null },
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "lingualens-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer supabase-access-token");
      expect(headers.get("X-Organization-Id")).toBe("clinic_001");
      return new Response(new Blob(["audio-bytes"], { type: "audio/webm" }), {
        status: 200,
        headers: { "Content-Type": "audio/webm" },
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    const blob = await apiBlob("/audio/audio_001/file");
    expect(blob.type).toBe("audio/webm");
    expect(getSession).not.toHaveBeenCalled();
  });

  it("falls back to demo user headers in mock runtime", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: true,
          auth_mode: "mock",
          model_version: "v2-mock",
          feature_schema: "lingualens-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "local_only",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("X-User-Id")).toBe("user_therapist_001");
      expect(headers.get("Authorization")).toBeNull();
      return jsonResponse({ ok: true });
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    await apiRequest("/protected");
  });

  it("sends bearer auth for relative backend blob uploads in supabase runtime", async () => {
    window.sessionStorage.setItem("lingualens.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      organizationId: "clinic_001",
      aal: "aal2",
    }));
    window.sessionStorage.setItem("lingualens.supabase-session-token.v1", "supabase-access-token");

    getSession.mockResolvedValue({
      data: { session: null },
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "lingualens-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer supabase-access-token");
      expect(headers.get("X-Organization-Id")).toBe("clinic_001");
      expect(headers.get("content-type")).toBe("audio/webm");
      return new Response(null, { status: 200 });
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    await apiUploadBlob("/audio/audio_001/upload-file", new Blob(["audio"], { type: "audio/webm" }));
    expect(getSession).not.toHaveBeenCalled();
  });

  it("does not add app auth headers to absolute signed upload URLs", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBeNull();
      expect(headers.get("X-Organization-Id")).toBeNull();
      expect(headers.get("content-type")).toBe("audio/webm");
      return new Response(null, { status: 200 });
    });

    vi.stubGlobal("fetch", fetchMock);

    await apiUploadBlob("https://storage.example.test/upload", new Blob(["audio"], { type: "audio/webm" }));
  });

  it("sends bearer auth for report export and reviewed CHA export in supabase runtime", async () => {
    window.sessionStorage.setItem("lingualens.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      organizationId: "clinic_001",
      aal: "aal2",
    }));
    window.sessionStorage.setItem("lingualens.supabase-session-token.v1", "supabase-access-token");

    getSession.mockResolvedValue({
      data: { session: null },
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "lingualens-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer supabase-access-token");
      expect(headers.get("X-Organization-Id")).toBe("clinic_001");

      if (url.includes("/reports/REPORT-001/export")) {
        return jsonResponse({
          filename: "report.md",
          content: "# Report",
          content_type: "text/markdown",
        });
      }

      if (url.endsWith("/transcripts/TRANSCRIPT-001/export-cha")) {
        return jsonResponse({
          filename: "reviewed.cha",
          cha_text: "@Begin\n@End\n",
        });
      }

      return jsonResponse({});
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    const report = await exportBackendReport("REPORT-001", "markdown");
    const transcript = await exportReviewedCha("TRANSCRIPT-001");

    expect(report.filename).toBe("report.md");
    expect(transcript.filename).toBe("reviewed.cha");
    expect(getSession).not.toHaveBeenCalled();
  });
});

function jsonResponse(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
