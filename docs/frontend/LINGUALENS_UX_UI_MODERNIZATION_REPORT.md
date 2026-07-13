# LinguaLens UX/UI Modernization Report

## Contracts and data-mode phase gate — 2026-07-13

Status: **implementation and automated contract gates passed; responsive visual gate incomplete**.

### Implemented contract

- Runtime settings are decoded with a shared Zod schema (`feature_schema: lingualens-app.1`). Unknown authentication modes fail closed.
- Backend capabilities are server-owned and conservative. Audio upload is experimental only for committed local storage modes; transcription is experimental only in the mock runtime with operational upload. Uncommitted Supabase upload work is not advertised as available.
- Remote state distinguishes `backend`, `sample`, `local-draft`, and `unavailable`. Data-bearing states cannot use `unavailable` mode, errors expose fixed safe UI text, and stale state records its invalidation cause.
- Request state is owned by session/resource identity. Older success or error responses cannot replace newer state, previous identity data is synchronously hidden, requests abort on identity changes/unmount, and inline loader functions do not cause request churn.
- Product Cases no longer imports or substitutes sample records. Backend list failure, missing IDs, and incomplete case detail fail explicitly. Timeline or goals request failures are not presented as confirmed-empty clinical data.
- Sample Cases access is isolated to `src/features/demo/services/sample-cases-adapter.ts`.

### Verification evidence

| Gate | Command | Result |
|---|---|---|
| Affected frontend contracts | `cd apps/lingualens-app && npm test -- src/__tests__/runtime-settings-contract.test.ts src/__tests__/backend-capabilities.test.ts src/__tests__/remote-state.test.ts src/__tests__/use-remote-resource.test.tsx src/__tests__/cases-data-mode.test.tsx src/__tests__/cases-workspace-client.test.tsx src/__tests__/api-auth.test.ts` | 7 files, 37 tests passed |
| Full frontend characterization | `cd apps/lingualens-app && npm test` | 32 files, 205 tests passed |
| Backend settings and organization authorization | `PYTHONPATH=apps/api .venv/bin/python -m pytest apps/api/tests/test_runtime_settings_contract.py apps/api/tests/test_organization_admin_routes.py -q` | 37 tests passed; 3 existing deprecation warnings |
| TypeScript | `cd apps/lingualens-app && npm run typecheck` | Exit 0 |
| Lint | `cd apps/lingualens-app && npm run lint` | Exit 0; 2 existing warnings in `supabase-mfa-panel.tsx`; `next lint` deprecation remains |
| Production build | `cd apps/lingualens-app && npm run build` | Exit 0; 21 routes generated, including static `/cases` and dynamic `/cases/[caseId]`; same 2 lint warnings |

### Recorded deviations and exceptions

- The implementation intentionally tightens the plan examples: `auth_mode` is an enum, raw error messages never enter shared UI state, `unavailable` cannot be data-bearing, and capability values reflect executable committed adapters rather than planned behavior.
- A global `mock-data` scan still finds pre-existing imports in `components/stepper.tsx` and `components/work-queue-dashboard.tsx`. They are outside the completed Cases adapter slice and remain an explicit exception for the next data-mode/decomposition gate. They must not be treated as proof that product/sample separation is globally complete.
- The baseline Playwright smoke failure at the pasted-transcript save transition remains unresolved and is not masked by this phase.

### Missing responsive evidence

Required Cases captures at `390x844`, `768x1024`, and `1440x900` for `/cases` and a missing-case deep link were not produced. The managed sandbox rejects localhost binding with `EPERM`; two escalated `npm run dev -- --hostname 127.0.0.1 --port 3000` attempts stalled before starting a server, and the port remained unreachable. Both stalled processes were terminated safely.

A serverless fallback was also attempted: the real `CasesWorkspaceClient` and `AppShell` were bundled into a temporary Playwright harness with the production build CSS and contract-faithful settings/cases responses. The harness compiled successfully without changing production code. Sandboxed Chromium then failed at launch with macOS Mach-port permission denial; the escalated browser launch also stalled awaiting external approval and was terminated. WebKit was not installed in the managed Playwright cache. No synthetic or partial capture was accepted as visual evidence.

Therefore this phase **does not pass its visual completion gate yet**. No claim is made about responsive overflow or approved-concept comparison for the changed Cases states. Capture must be rerun in a browser-capable environment before the phase can be marked complete.
