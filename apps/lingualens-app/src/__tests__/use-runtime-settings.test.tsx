import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import type { RuntimeSettings } from "@/lib/api";

const { getRuntimeSettings } = vi.hoisted(() => ({
  getRuntimeSettings: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api")>();
  return { ...original, getRuntimeSettings };
});

beforeEach(() => {
  getRuntimeSettings.mockReset();
});

test("returns explicit loading and confirmed runtime settings states", async () => {
  const request = deferred<RuntimeSettings>();
  getRuntimeSettings.mockReturnValue(request.promise);

  const { result } = renderHook(() => useRuntimeSettings());

  expect(result.current).toEqual({ status: "loading", mode: "backend" });

  act(() => request.resolve(runtimeSettings));

  await waitFor(() => {
    expect(result.current).toEqual({
      status: "success",
      mode: "backend",
      data: runtimeSettings,
    });
  });
});

test("returns a fail-closed safe error state when runtime settings cannot be confirmed", async () => {
  getRuntimeSettings.mockRejectedValue(new Error("schema details must not leak"));

  const { result } = renderHook(() => useRuntimeSettings());

  await waitFor(() => {
    expect(result.current).toEqual({
      status: "error",
      mode: "backend",
      message: "Runtime settings unavailable",
    });
  });
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

const runtimeSettings: RuntimeSettings = {
  mock_mode: false,
  auth_mode: "supabase",
  model_version: "v2-mock",
  feature_schema: "lingualens-app.1",
  guideline_mapping: "review-support-only",
  user_roles: ["therapist"],
  data_retention: "configured",
  consent_policy: "required",
  capabilities: {
    cases: "available",
    audio_upload: "experimental",
    transcription: "experimental",
    transcript_qa: "available",
    feature_extraction: "available",
    ai_review: "disabled",
    report_drafting: "disabled",
    pdf_export: "unavailable",
  },
  pipeline_settings: {
    audio_processing: "experimental_async",
    job_queue_mode: "redis",
    repository_mode: "sql",
    storage_mode: "supabase_private",
  },
};
