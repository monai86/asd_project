# LinguaLens UX/UI Modernization Report

## Contracts and data-mode phase gate — 2026-07-13

Status: **contracts and data-mode phase gate passed**.

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
| Responsive Cases evidence | Temporary real-component Playwright harness using the production CSS and contract-faithful runtime/Cases responses | 6/6 passed; zero page errors; no horizontal overflow at `390x844`, `768x1024`, or `1440x900` |

### Recorded deviations and exceptions

- The implementation intentionally tightens the plan examples: `auth_mode` is an enum, raw error messages never enter shared UI state, `unavailable` cannot be data-bearing, and capability values reflect executable committed adapters rather than planned behavior.
- A global `mock-data` scan still finds pre-existing imports in `components/stepper.tsx` and `components/work-queue-dashboard.tsx`. A read-only call-site audit found that `SessionStepper` currently has no callers, so its mock-backed steps are unreachable. `WorkQueueDashboard`, however, is the active component for both `/` and `/today`; it combines imported mock cases/workload with hard-coded sample priority, agenda, upload, and result rows. Its copy labels the data as demo/fallback, but there is no explicit runtime-mode adapter boundary. Replacing that behavior belongs to the approved Today/decomposition work and could conflict with the preserved frontend WIP, so production code was intentionally left unchanged. This remains an explicit exception and must not be treated as proof that product/sample separation is globally complete.
- The screenshot review exposed a pre-existing display inconsistency in “Workflow at a glance”: its labels use backend status values while its count compares derived workflow-stage labels, so the harness case shows “Needs Review — 0 case(s)” beside a one-case review queue. This is not a safety or authorization regression from the contracts slice, and production WIP was not silently replaced; it requires characterization before correction in the approved Cases decomposition work.
- The baseline Playwright smoke failure at the pasted-transcript save transition remains unresolved and is not masked by this phase.

### Responsive visual evidence

The permission profile changed after the previously recorded launch blocker, allowing an approved Playwright process to start Chromium. The same temporary harness was rebuilt with the real `CasesWorkspaceClient` and `AppShell`, production build CSS, contract-valid runtime settings, backend Cases data, and an explicit missing-case `404`. No production UI source was changed by the harness.

The six reviewed captures are in `docs/frontend/contracts-phase-screenshots/`:

- `/cases`: `cases-390x844.png`, `cases-768x1024.png`, `cases-1440x900.png`
- `/cases/missing-case`: `cases-missing-390x844.png`, `cases-missing-768x1024.png`, `cases-missing-1440x900.png`

Visual review confirms the approved responsive hierarchy for this slice: mobile uses a single readable column and bottom navigation; tablet uses the compact side rail without narrowing or clipping the case content; desktop uses the full navigation and quiet contextual rail. The unavailable deep-link state remains explicit and non-identifying at all three viewports. All captures preserve decision-support language, readable controls, and safe navigation spacing. No horizontal overflow or covered content was observed.

The earlier failed localhost and Mach-port attempts remain historical evidence of the environment blocker; they are superseded by these successful captures rather than erased.
