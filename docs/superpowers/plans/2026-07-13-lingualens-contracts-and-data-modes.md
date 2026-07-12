# LinguaLens Contracts and Data Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add schema-validated runtime capabilities, shared remote states, and strictly separated backend, sample, local-draft, and unavailable data modes.

**Architecture:** Keep `lib/api.ts` as transport during migration, decode backend payloads at the service boundary, and expose feature-safe discriminated states through focused hooks. Product adapters never import sample records; demo adapters own all sample imports.

**Tech Stack:** Next.js 15, React 19, TypeScript, Zod, Vitest, Testing Library, FastAPI, pytest

---

## File map

- Create `apps/lingualens-app/src/services/api/runtime-settings-schema.ts`: Zod decoder and inferred runtime settings type.
- Create `apps/lingualens-app/src/services/capabilities/backend-capabilities.ts`: capability derivation only.
- Create `apps/lingualens-app/src/services/adapters/remote-state.ts`: shared remote/data-mode types and helpers.
- Create `apps/lingualens-app/src/services/adapters/use-remote-resource.ts`: identity-safe request lifecycle.
- Create `apps/lingualens-app/src/features/cases/services/cases-adapter.ts`: product cases adapter.
- Create `apps/lingualens-app/src/features/demo/services/sample-cases-adapter.ts`: demo-only sample adapter.
- Modify `apps/lingualens-app/src/lib/api.ts`: decode runtime settings and preserve transport behavior.
- Modify `apps/lingualens-app/src/lib/workflow.ts`: allow case reads to receive an `AbortSignal`.
- Modify `apps/lingualens-app/src/lib/use-runtime-settings.ts`: return explicit remote state.
- Modify `apps/lingualens-app/src/components/cases-workspace-client.tsx`: consume explicit state and remove fallback imports.
- Modify `apps/api/app/api/v1/routes/settings.py`: add explicit capability payload without weakening existing fields.
- Test with focused frontend and backend contract suites.

### Task 1: Characterize the current runtime settings contract

**Files:**
- Create: `apps/lingualens-app/src/__tests__/runtime-settings-contract.test.ts`
- Test: `apps/api/tests/test_runtime_settings_contract.py`

- [ ] **Step 1: Add the frontend characterization test**

```ts
import { getRuntimeSettings } from "@/lib/api";

test("preserves the current runtime settings contract", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
    mock_mode: false,
    auth_mode: "supabase",
    model_version: "v2-mock",
    feature_schema: "lingualens-app.1",
    guideline_mapping: "review-support-only",
    user_roles: ["therapist", "clinical_supervisor", "org_admin"],
    data_retention: "configured retention",
    consent_policy: "visible per case",
    pipeline_settings: {
      audio_processing: "experimental_async",
      job_queue_mode: "redis",
      repository_mode: "sql",
      storage_mode: "supabase",
    },
  }), { status: 200 })));

  await expect(getRuntimeSettings()).resolves.toMatchObject({
    auth_mode: "supabase",
    pipeline_settings: { audio_processing: "experimental_async" },
  });
});
```

- [ ] **Step 2: Add the backend characterization test**

```py
def test_runtime_settings_exposes_stable_contract(client):
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {
        "mock_mode", "auth_mode", "model_version", "feature_schema",
        "guideline_mapping", "user_roles", "access_model",
        "data_retention", "consent_policy", "pipeline_settings",
    }
```

- [ ] **Step 3: Run the characterization tests**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/runtime-settings-contract.test.ts`  
Expected: PASS.

Run: `cd apps/api && PYTHONPATH=. pytest tests/test_runtime_settings_contract.py -q`  
Expected: PASS.

- [ ] **Step 4: Commit the characterization**

```bash
git add apps/lingualens-app/src/__tests__/runtime-settings-contract.test.ts apps/api/tests/test_runtime_settings_contract.py
git commit -m "test: characterize runtime settings contract" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 2: Add schema decoding and explicit capabilities

**Files:**
- Create: `apps/lingualens-app/src/services/api/runtime-settings-schema.ts`
- Create: `apps/lingualens-app/src/services/capabilities/backend-capabilities.ts`
- Create: `apps/lingualens-app/src/__tests__/backend-capabilities.test.ts`
- Modify: `apps/lingualens-app/src/lib/api.ts`
- Modify: `apps/api/app/api/v1/routes/settings.py`
- Modify: `apps/api/tests/test_runtime_settings_contract.py`

- [ ] **Step 1: Write failing capability tests**

```ts
import { deriveBackendCapabilities } from "@/services/capabilities/backend-capabilities";

test("derives experimental and disabled capabilities from runtime settings", () => {
  expect(deriveBackendCapabilities({
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
      storage_mode: "supabase",
    },
  })).toMatchObject({ audioUpload: "experimental", aiReview: "disabled" });
});

test("rejects an unknown backend capability value", () => {
  expect(() => deriveBackendCapabilities({ capabilities: { cases: "maybe" } } as never)).toThrow();
});
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/backend-capabilities.test.ts`  
Expected: FAIL because the modules do not exist.

- [ ] **Step 3: Implement the runtime schema**

```ts
import { z } from "zod";

const availability = z.enum(["available", "unavailable"]);
const experimentalAvailability = z.enum(["available", "experimental", "unavailable"]);
const optionalAvailability = z.enum(["available", "disabled", "unavailable"]);

export const runtimeSettingsSchema = z.object({
  mock_mode: z.boolean(),
  auth_mode: z.string(),
  model_version: z.string(),
  feature_schema: z.string(),
  guideline_mapping: z.string(),
  user_roles: z.array(z.string()),
  access_model: z.object({
    invitation_only: z.boolean(),
    required_app_aal: z.enum(["aal1", "aal2"]),
    active_organization_session: z.string(),
    production_mock_mode: z.string(),
  }).optional(),
  data_retention: z.string(),
  consent_policy: z.string(),
  capabilities: z.object({
    cases: availability,
    audio_upload: experimentalAvailability,
    transcription: experimentalAvailability,
    transcript_qa: availability,
    feature_extraction: availability,
    ai_review: optionalAvailability,
    report_drafting: optionalAvailability,
    pdf_export: availability,
  }),
  pipeline_settings: z.object({
    audio_processing: z.string(),
    job_queue_mode: z.string(),
    repository_mode: z.string(),
    storage_mode: z.string(),
    ai_review_policy: z.string().optional(),
    ai_report_drafting_enabled: z.boolean().optional(),
  }),
});

export type RuntimeSettings = z.infer<typeof runtimeSettingsSchema>;
```

- [ ] **Step 4: Implement capability derivation**

```ts
import { runtimeSettingsSchema, type RuntimeSettings } from "@/services/api/runtime-settings-schema";

export type BackendCapabilities = {
  cases: "available" | "unavailable";
  audioUpload: "available" | "experimental" | "unavailable";
  transcription: "available" | "experimental" | "unavailable";
  transcriptQa: "available" | "unavailable";
  featureExtraction: "available" | "unavailable";
  aiReview: "available" | "disabled" | "unavailable";
  reportDrafting: "available" | "disabled" | "unavailable";
  pdfExport: "available" | "unavailable";
};

export function deriveBackendCapabilities(input: RuntimeSettings): BackendCapabilities {
  const settings = runtimeSettingsSchema.parse(input);
  return {
    cases: settings.capabilities.cases,
    audioUpload: settings.capabilities.audio_upload,
    transcription: settings.capabilities.transcription,
    transcriptQa: settings.capabilities.transcript_qa,
    featureExtraction: settings.capabilities.feature_extraction,
    aiReview: settings.capabilities.ai_review,
    reportDrafting: settings.capabilities.report_drafting,
    pdfExport: settings.capabilities.pdf_export,
  };
}
```

- [ ] **Step 5: Extend the backend payload with server-owned capability values**

Add to `settings()`:

```py
"capabilities": {
    "cases": "available",
    "audio_upload": "experimental",
    "transcription": "experimental",
    "transcript_qa": "available",
    "feature_extraction": "available",
    "ai_review": "disabled",
    "report_drafting": "available" if config.ai_report_drafting_enabled else "disabled",
    "pdf_export": "unavailable",
},
```

Update `getRuntimeSettings()` to parse `runtimeSettingsSchema.parse(await apiGet("/settings"))` and re-export the inferred type.

- [ ] **Step 6: Run focused frontend and backend tests**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/backend-capabilities.test.ts src/__tests__/runtime-settings-contract.test.ts src/__tests__/api-auth.test.ts`  
Expected: PASS.

Run: `pytest apps/api/tests/test_runtime_settings_contract.py -q`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/lingualens-app/src/services apps/lingualens-app/src/lib/api.ts apps/lingualens-app/src/__tests__ apps/api/app/api/v1/routes/settings.py apps/api/tests/test_runtime_settings_contract.py
git commit -m "feat: add validated backend capabilities" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 3: Add shared remote and data-mode states

**Files:**
- Create: `apps/lingualens-app/src/services/adapters/remote-state.ts`
- Create: `apps/lingualens-app/src/__tests__/remote-state.test.ts`
- Modify: `apps/lingualens-app/src/lib/use-runtime-settings.ts`

- [ ] **Step 1: Write failing state tests**

```ts
import { confirmed, failedWithPrevious, stale } from "@/services/adapters/remote-state";

test("preserves only confirmed data when a refresh fails", () => {
  expect(failedWithPrevious(new Error("offline"), [{ id: "case-1" }])).toMatchObject({
    status: "error",
    mode: "backend",
    previous: [{ id: "case-1" }],
  });
});

test("records the cause of downstream staleness", () => {
  expect(stale({ reportId: "report-1" }, "transcript-edited")).toMatchObject({
    status: "stale",
    invalidatedBy: "transcript-edited",
  });
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/remote-state.test.ts`  
Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the discriminated types and helpers**

```ts
export type DataMode = "backend" | "sample" | "local-draft" | "unavailable";
export type StaleCause = "transcript-edited" | "report-revised" | "session-changed";

export type RemoteState<T> =
  | { status: "idle"; mode: DataMode }
  | { status: "loading"; mode: DataMode; previous?: T }
  | { status: "success"; mode: DataMode; data: T }
  | { status: "empty"; mode: DataMode }
  | { status: "error"; mode: DataMode; message: string; previous?: T }
  | { status: "unavailable"; mode: "unavailable"; reason: string }
  | { status: "stale"; mode: DataMode; data: T; invalidatedBy: StaleCause };

export const confirmed = <T>(data: T, mode: DataMode = "backend"): RemoteState<T> =>
  Array.isArray(data) && data.length === 0 ? { status: "empty", mode } : { status: "success", mode, data };

export const failedWithPrevious = <T>(error: Error, previous?: T): RemoteState<T> => ({
  status: "error", mode: "backend", message: error.message || "Request failed", previous,
});

export const stale = <T>(data: T, invalidatedBy: StaleCause): RemoteState<T> => ({
  status: "stale", mode: "backend", data, invalidatedBy,
});
```

- [ ] **Step 4: Change `useRuntimeSettings` to return `RemoteState<RuntimeSettings>`**

Initialize with `{ status: "loading", mode: "backend" }`, return confirmed data on success, and return `{ status: "error", mode: "backend", message: "Runtime settings unavailable" }` on failure. Keep the cancellation guard.

- [ ] **Step 5: Run focused tests and typecheck**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/remote-state.test.ts src/__tests__/app-shell-auth-gate.test.tsx`  
Expected: PASS after updating shell callers to narrow `status === "success"`.

Run: `cd apps/lingualens-app && npm run typecheck`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/lingualens-app/src/services/adapters/remote-state.ts apps/lingualens-app/src/lib/use-runtime-settings.ts apps/lingualens-app/src/__tests__ apps/lingualens-app/src/components
git commit -m "refactor: model explicit remote states" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 4: Prevent stale responses from crossing identities

**Files:**
- Create: `apps/lingualens-app/src/services/adapters/use-remote-resource.ts`
- Create: `apps/lingualens-app/src/__tests__/use-remote-resource.test.tsx`

- [ ] **Step 1: Write the failing race test**

```tsx
test("ignores a response for the previous session identity", async () => {
  const first = deferred<string>();
  const second = deferred<string>();
  const load = vi.fn((key: string) => key === "one" ? first.promise : second.promise);
  const { result, rerender } = renderHook(({ key }) => useRemoteResource(key, load), {
    initialProps: { key: "one" },
  });
  rerender({ key: "two" });
  second.resolve("new");
  await waitFor(() => expect(result.current).toMatchObject({ status: "success", data: "new" }));
  first.resolve("old");
  await act(async () => Promise.resolve());
  expect(result.current).toMatchObject({ status: "success", data: "new" });
});
```

Include a local `deferred<T>()` helper in the test that returns `{ promise, resolve, reject }`.

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/use-remote-resource.test.tsx`  
Expected: FAIL because the hook does not exist.

- [ ] **Step 3: Implement the hook with request sequencing**

```ts
export function useRemoteResource<T>(identity: string, load: (identity: string, signal: AbortSignal) => Promise<T>) {
  const requestId = useRef(0);
  const [state, setState] = useState<RemoteState<T>>({ status: "loading", mode: "backend" });
  useEffect(() => {
    const controller = new AbortController();
    const current = ++requestId.current;
    setState((previous) => ({ status: "loading", mode: "backend", previous: "data" in previous ? previous.data : undefined }));
    void load(identity, controller.signal).then((data) => {
      if (current === requestId.current) setState(confirmed(data));
    }).catch((error: Error) => {
      if (!controller.signal.aborted && current === requestId.current) setState(failedWithPrevious(error));
    });
    return () => controller.abort();
  }, [identity, load]);
  return state;
}
```

- [ ] **Step 4: Run and confirm GREEN**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/use-remote-resource.test.tsx`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/src/services/adapters/use-remote-resource.ts apps/lingualens-app/src/__tests__/use-remote-resource.test.tsx
git commit -m "feat: cancel stale frontend requests" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 5: Separate product cases from sample cases

**Files:**
- Create: `apps/lingualens-app/src/features/cases/services/cases-adapter.ts`
- Create: `apps/lingualens-app/src/features/demo/services/sample-cases-adapter.ts`
- Create: `apps/lingualens-app/src/__tests__/cases-data-mode.test.tsx`
- Modify: `apps/lingualens-app/src/components/cases-workspace-client.tsx`
- Modify: `apps/lingualens-app/src/lib/api.ts`
- Modify: `apps/lingualens-app/src/lib/workflow.ts`

- [ ] **Step 1: Write failing no-fallback tests**

```tsx
test("shows unavailable state without sample cases when backend loading fails", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("offline"); }));
  render(<CasesWorkspaceClient />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Cases are unavailable");
  expect(screen.queryByText("Demo child")).not.toBeInTheDocument();
});

test("does not substitute the first sample case for an unknown case id", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("not found", { status: 404 })));
  render(<CasesWorkspaceClient caseId="missing-case" />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Case could not be loaded");
  expect(screen.queryByText("Demo child")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run and confirm RED**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/cases-data-mode.test.tsx`  
Expected: FAIL because current state initializes from fallback cases.

- [ ] **Step 3: Implement the product adapter**

```ts
export const casesAdapter = {
  list: (signal: AbortSignal) => listBackendCases({ signal }),
  get: (caseId: string, signal: AbortSignal) => getBackendCase(caseId, { signal }),
};
```

Extend the transport and workflow reads without changing default callers:

```ts
export async function apiGet<T>(path: string, init: RequestInit = {}): Promise<T> {
  return apiRequest<T>(path, init);
}

type ReadOptions = Pick<RequestInit, "signal">;

export function listBackendCases(options: ReadOptions = {}): Promise<BackendCase[]> {
  return apiGet<BackendCase[]>("/cases", options);
}

export function getBackendCase(caseId: string, options: ReadOptions = {}): Promise<BackendCase> {
  return apiGet<BackendCase>(`/cases/${encodeURIComponent(caseId)}`, options);
}
```

Implement the demo adapter in the demo feature only:

```ts
import { cases } from "@/lib/mock-data";
export const sampleCasesAdapter = { list: async () => cases };
```

Remove `fallbackCases`, `mapFallbackCase`, and fallback state initialization from the product component. Render explicit loading, empty, error, and unavailable branches.

- [ ] **Step 4: Run focused cases tests**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/cases-data-mode.test.tsx src/__tests__/cases-workspace-client.test.tsx`  
Expected: PASS after updating existing assertions from fallback content to explicit state content.

- [ ] **Step 5: Verify sample imports stay inside demo**

Run: `rtk rg -n 'mock-data' apps/lingualens-app/src/app apps/lingualens-app/src/components apps/lingualens-app/src/features`  
Expected: Product route/component paths contain no sample-record imports; demo feature paths may contain them.

- [ ] **Step 6: Commit**

```bash
git add apps/lingualens-app/src/features apps/lingualens-app/src/components/cases-workspace-client.tsx apps/lingualens-app/src/__tests__
git commit -m "fix: prevent sample fallback on product cases" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```

### Task 6: Run the contracts phase gate

**Files:**
- Modify: `docs/frontend/LINGUALENS_UX_UI_MODERNIZATION_REPORT.md` if already created
- Modify: `docs/frontend/UX_UI_BASELINE_AUDIT.md` only to append post-phase evidence, never rewrite baseline facts

- [ ] **Step 1: Run affected frontend suites**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/runtime-settings-contract.test.ts src/__tests__/backend-capabilities.test.ts src/__tests__/remote-state.test.ts src/__tests__/use-remote-resource.test.tsx src/__tests__/cases-data-mode.test.tsx src/__tests__/cases-workspace-client.test.tsx src/__tests__/api-auth.test.ts`  
Expected: PASS with zero failed tests.

- [ ] **Step 2: Run backend contract tests**

Run: `pytest apps/api/tests/test_runtime_settings_contract.py apps/api/tests/test_organization_admin_routes.py -q`  
Expected: PASS.

- [ ] **Step 3: Run typecheck and lint**

Run: `cd apps/lingualens-app && npm run typecheck`  
Expected: PASS.

Run: `cd apps/lingualens-app && npm run lint`  
Expected: Exit 0; record any warnings rather than claiming a clean lint if warnings remain.

- [ ] **Step 4: Capture affected Cases screenshots**

Capture `/cases` and `/cases/missing-case` at 390x844, 768x1024, and 1440x900. Verify no sample records appear after backend failure and no horizontal overflow occurs.

- [ ] **Step 5: Record the phase gate**

Add exact commands, results, screenshots, schema version, and any approved exceptions to the modernization report.

- [ ] **Step 6: Commit phase evidence**

```bash
git add docs/frontend
git commit -m "docs: record contracts phase evidence" -m "Co-Authored-By: GPT-5 Codex <codex@openai.com>"
```
