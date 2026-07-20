# LinguaLens UX/UI Modernization Report

## Modernization completion evidence — 2026-07-20

Status: **implementation and verification complete**.

### A. Initial audit

The required baseline freeze is recorded in
`docs/frontend/UX_UI_BASELINE_AUDIT.md`. It was completed before production UI
changes and includes the route map, navigation inventory, duplicate workflows,
component line counts, direct API ownership, fallback/data-mode behavior, 40
baseline captures across the five required viewports, responsive and
accessibility defects, bundle evidence, known failures, and the approved phase
sequence. The pre-modernization worktree was preserved in an external patch and
its changed-file inventory was recorded rather than reset or overwritten.

The audit confirmed the main defects described by the prompt: competing legacy
workflow routes, duplicate landing behavior, concentrated Session state and
rendering, unsafe fallback ambiguity, incomplete tablet behavior, inconsistent
tokens, and insufficient viewport/e2e proof.

### B. Approved architecture

- `/today` is the single landing workbench: one prioritized queue, one next
  action per row, one prominent Start session action, and a quiet contextual
  rail. Cases and Reports load in parallel through an authenticated feature
  adapter; pending, confirmed, unavailable, and retry states are explicit;
  malformed or failed responses cannot become sample success. Status grouping
  is internal to the queue rather than a Kanban board.
- `/cases` and `/cases/[caseId]` use intentional list/detail behavior and the
  approved responsive split-view pattern. Identifier-less legacy workflow
  routes resolve to `/cases?intent=start-session`.
- `/sessions/[sessionId]?view=intake|transcript|findings|report` is canonical.
  Missing or invalid view values resolve safely to Intake.
- Session rendering is separated from workflow orchestration. The thin route
  dispatcher selects Report or the identity-scoped `useSessionWorkspace`
  controller; a typed presentational dispatcher lazy-loads Intake, Transcript,
  and Findings. Intake steps, Findings derivations, the directly editable
  transcript line list, and Report orchestration are separated from their
  presentational views. An architecture test keeps complex feature containers
  at or below 500 lines and prevents Session presentation from importing raw
  backend transport. The identity-scoped Session controller is the documented
  non-layout exception because it coordinates request cancellation and stale
  settlements across the complete Session identity.
- `/settings` is the only Settings route. Team and Audit are organization-admin
  sections, denied at the backend and server/data boundary for ordinary
  therapists. Therapists receive only the safe read-only care-team summary of a
  case they are already authorized to access.

#### Clinical workflow and contract safety

- Frontend runtime capabilities and workflow values are decoded from explicit
  schemas. Product state distinguishes backend, sample, local draft, stale, and
  unavailable data without converting backend failure into fake success.
- Transcript edits invalidate existing downstream findings and report drafts
  server-side. `not_started` remains distinct for outputs never generated;
  persisted legacy records are parsed compatibly; stale findings are not
  current; stale reports cannot be signed or exported; regeneration actions
  explain recovery.
- Request and mutation settlements are identity- and revision-scoped. Coverage
  includes session changes during requests, late responses, navigation during
  save, duplicate save suppression, recovery retry, and downstream
  invalidation.
- Role, invitation, privacy, care-team, and organization management actions
  retain backend audit logging. Production authorization guards were not
  relaxed to make UI or fixture tests pass.

#### Design and responsive contract

- `apps/lingualens-app/DESIGN.md` and `src/styles/globals.css` are the single
  documented/executable design contract. The unified product font stack is
  `Noto Sans Thai`, `Noto Sans`, `Leelawadee UI`, Tahoma, sans-serif. Atkinson
  Hyperlegible is reserved for an explicit accessibility preference or a
  Latin-only transcript context.
- Executable motion tokens use 100ms selection/hover, 160ms popover/menu,
  220ms panel, and 0ms resize timing. Reduced-motion behavior remains global.
- Transcript lines are directly editable and expose `aria-selected`; the
  selected line remains clearly highlighted; secondary actions are in an
  overflow menu. Desktop keeps the editor dominant and the inspector
  collapsible. Tablet portrait can switch/collapse Audio and QA. Mobile sticky
  regions respect safe-area insets and reserve content space.
- Required canonical screens were reviewed at 390×844, 768×1024, 1024×1366,
  1280×800, and 1440×900. The evidence and intentional deviations are indexed
  in `docs/frontend/visual-deviations.md`.

### C. Screen-by-screen changes

| Screen | Implemented change |
|---|---|
| Today | Replaced static mock/fallback rows with an authorized backend-derived focused queue, one next action per row, one Start session action, explicit pending/error/retry states, status grouping inside the queue, recent context, and a quiet rail. |
| Cases | Added search, consent/workflow filters, authorized clinician behavior, priority/next-action rows, mobile cards, deliberate session selection, and a responsive list/detail boundary. |
| Case Detail | Added Overview, Sessions, Goals, Progress, Reports, consent gating, a primary next action, and safe read-only care-team context without organization-admin fetches. |
| Session Intake | Consolidated CHAT upload, paste, audio upload, and recording into the canonical four-step flow with consent, source validation, experimental-audio disclosure, processing state, and backend-confirmed advancement. |
| Transcript | Kept line text directly editable; added dominant desktop editor, switchable/collapsible tablet inspector, safe-area-aware mobile sticky player/actions, selected-line semantics, overflow actions, QA/attestation gates, and stale invalidation. |
| Findings | Shows backend provenance, reviewed transcript/feature versions, descriptive cues, missing-data limitations, AI-support disposition, explicit `not_started`/processing/stale states, and regeneration. |
| Report | Uses the single Session editor with source evidence, safety and limitations, version provenance, editable drafts, immutable signed snapshots, stale locks, sign-off/export gates, and revision/regeneration paths. |
| Reports | Functions as a status-grouped library/task queue and routes editing to canonical Session Report rather than duplicating editor logic. |
| Settings/Admin | Keeps `/settings` canonical; ordinary therapists see explicit profile, organization/sample mode, credentials, accessibility/display, and fail-closed owned privacy-request status without mounting admin data, while backend-authorized organization admins receive separate Team, invitations, audit, privacy-operation, runtime, and integration sections. |

### D. Responsive evidence

The table below records the required viewport result and representative exact
Today/Transcript captures. The complete screen matrix is in the directories
listed by `docs/frontend/visual-deviations.md`.

| Viewport | Screenshot paths | Layout used | Overflow | Primary action | Transcript usability |
|---|---|---|---|---|---|
| 390×844 | `docs/frontend/navigation-phase-screenshots/today-mobile-390x844.png`; `docs/frontend/session-transcript-phase-screenshots/session-transcript-390x844.png` | One column, bottom navigation, sticky safe-area controls | Passed | Start session and row next action remain visible | Readable vertical editable lines; Audio/QA and row actions collapse without covering content |
| 768×1024 | `docs/frontend/navigation-phase-screenshots/today-tablet-portrait-768x1024.png`; `docs/frontend/session-transcript-phase-screenshots/session-transcript-768x1024.png` | Compact rail; tablet portrait Session with switchable/collapsible inspector | Passed | Queue action remains in the primary region | Transcript keeps usable width; Audio/QA switches instead of squeezing a desktop grid |
| 1024×1366 | `docs/frontend/navigation-phase-screenshots/today-tablet-landscape-1024x1366.png`; `docs/frontend/session-transcript-phase-screenshots/session-transcript-1024x1366.png` | Compact expanded navigation and split workspace | Passed | Primary task/action remains above secondary context | Editor remains primary; inspector is available without clipping |
| 1280×800 | `docs/frontend/navigation-phase-screenshots/today-desktop-compact-1280x800.png`; `docs/frontend/session-transcript-phase-screenshots/session-transcript-1280x800.png` | Compact desktop workbench with contextual rail | Passed | Start session is prominent in the first viewport | Editor holds at least 60%; inspector can collapse and controls remain keyboard reachable |
| 1440×900 | `docs/frontend/navigation-phase-screenshots/today-desktop-1440x900.png`; `docs/frontend/session-transcript-phase-screenshots/session-transcript-1440x900.png` | Full desktop navigation, reading surface, and quiet rail | Passed | Queue hierarchy exposes one unambiguous next action per row | Full editable transcript workspace, selected-line state, player, QA, and overflow actions remain visible |

Additional exact five-viewport matrices cover Cases/list/detail/selector,
Intake, Findings, Session Report, Reports, therapist Settings, and admin Settings
under `docs/frontend/*-phase-screenshots/`. Each Playwright matrix asserts
document width against viewport width, primary-action visibility, and the
screen-specific responsive contract.

### E. Accessibility evidence

- Transcript `aria-selected`, live save/job/error announcements, input-error
  `aria-describedby`, menu focus restoration, browser-default shortcut safety,
  and focus-preserving nearest-line scrolling have automated coverage.
- Global forced-colors rules and a Chromium forced-colors capture prove selected
  state, current navigation, control borders, and focus indication remain
  visible. A 640px-wide capture provides the approved 200%-zoom-equivalent
  reflow evidence.
- The modernization introduces no modal dialog or drawer. The transcript menu,
  the only new popup interaction, moves focus into the menu and restores it to
  the trigger on Escape/close.

### F. Performance evidence

| Budget or benchmark | Evidence | Result |
|---|---|---|
| Shared initial JavaScript | production build budget | 102 / 112 kB |
| Today | production build budget | 213 / 213 kB |
| Cases | production build budget | 225 / 242 kB |
| Reports | production build budget | 212 / 229 kB |
| Settings | production build budget | 218 / 232 kB |
| Session | production build after controller/view split | 219 / 230 kB |
| Largest measured lazy client chunk | gzip budget | 13.2 / 80 kB |
| 500-line transcript | five production runs | keystroke p95 23.0ms; worst scroll 60.45fps |
| 1,000-line transcript | five production runs | keystroke p95 19.7ms; worst scroll 61.84fps |

The 100/500/1,000-line benchmark evidence supports retaining direct rendering;
virtualization is not justified by the recorded keystroke and scroll results.

### G. Tests

| Gate | Result |
|---|---|
| Repository consistency | Passed using the canonical filesystem policy |
| Local secret scan | Passed |
| Python/core/backend suite | 777 passed, 3 intentionally deselected on Python 3.12.13 |
| Fresh API migrations | Passed through `0012_report_runtime_fields`, 24 tables |
| Frontend characterization | 49 files, 377 tests passed |
| TypeScript | Passed |
| Lint | Passed with two known non-blocking warnings in `supabase-mfa-panel.tsx` |
| Production build | Passed, 21 routes generated |
| Bundle budgets | Passed after Session split, Session 219/230 kB |
| Real/contract-faithful Playwright smoke | 3/3 passed |
| Explicit demo-mode Playwright smoke | 2/2 passed, including rendered descriptive-copy assertions for Features and Report |
| Required responsive matrices | Passed with no horizontal overflow after the recorded Settings form and intrinsic-width case-selector fixes |

The repository-wide command was:

```sh
PATH=/Users/porschecaa/lingualens/.venv312/bin:$PATH bash scripts/check_project.sh
```

Python 3.12 is the repository’s recommended verified runtime. A separate Python
3.13 run and one Python 3.12 repository-wide process exposed a native
Numba/Librosa crash. The Python 3.12 failure did not reproduce in three fresh
isolated processes, the containing test file, or the subsequent 777-test core
suite. It is recorded as a native-process flake rather than a fixed product
defect; no production workaround or guard weakening was introduced to conceal
it.

Two load-heavy frontend runs timed out before the first cold-loaded Intake view
reached its heading, while three isolated Intake runs passed. The traced path
showed that the production `SessionIntakeView` dynamic import could take about
3.1 seconds under full-suite load, exceeding Testing Library's one-second query
default. The first characterization query now allows five seconds for that cold
lazy boundary; production loading and workflow behavior are unchanged. The
subsequent full run passed all 49 files and 377 tests. The experiment ledger is
`docs/frontend/debug-ledgers/settings-and-intake-verification-2026-07-19.md`.

Actual frontend commands verified for this report are:

```sh
cd apps/lingualens-app
npm run lint
npm run typecheck
npm test
npm run verify:bundle
PATH=/Users/porschecaa/lingualens/.venv312/bin:$PATH \
  PLAYWRIGHT_FRONTEND_PORT=3197 PLAYWRIGHT_BACKEND_PORT=8197 \
  npm run e2e:smoke
PATH=/Users/porschecaa/lingualens/.venv312/bin:$PATH \
  NEXT_PUBLIC_DEMO_MODE=true \
  PLAYWRIGHT_FRONTEND_PORT=3199 PLAYWRIGHT_BACKEND_PORT=8199 \
  npx playwright test e2e/demo-mode.smoke.spec.ts
```

### H. Remaining limitations

- **Frontend:** Long transcripts are intentionally not virtualized because the
  measured 100/500/1,000-line results remain within budget. Two known
  non-blocking lint warnings remain in the pre-existing Supabase MFA panel.
- **Backend-dependent:** Provider, storage, PDF, integrations, and AI-support
  affordances remain governed by the runtime capability payload. The frontend
  does not claim an unavailable backend capability is operational.
- **Experimental audio:** Upload/record/transcription remains explicitly draft
  and experimental. Raw audio is memory-only in the browser and is never stored
  in browser persistence.
- **Production:** Deployment readiness still depends on the configured
  production identity, private storage, provider, and integration environment;
  demo or memory-repository success is not treated as production proof.
- **Clinical:** LinguaLens remains decision-support only. Therapist review and
  attestation are required, signed reports are immutable, and the product does
  not provide diagnosis, validated Thai norms, or treatment recommendations.

#### Completed demo-copy correction

After explicit authorization, the two preserved uncommitted demo pages were
backed up outside the repository and their unsupported Thai age-norm, threshold,
and evaluative wording was replaced with descriptive sample observations. The
rendered Features and Report pages state that values are for therapist review,
are not comparisons against age norms, and are not diagnostic. The targeted
copy scan is clean, explicit demo-mode Playwright passes 2/2, and reviewed
1280×800 captures are recorded as
`demo-features-descriptive-copy-1280x800.png` and
`demo-report-descriptive-copy-1280x800.png` under the navigation evidence
directory. Production authentication and authorization paths were unchanged.

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
- The earlier phase audit found product `mock-data` in `WorkQueueDashboard`. That exception is now resolved: Today loads authorized Cases and Reports through `today-workbench-adapter.ts`, rejects malformed contracts, derives queue state in a pure model, and renders no sample fallback. The only remaining production-tree `mock-data` import outside explicit demo adapters is the unreachable `SessionStepper`, which has no callers and is not part of a route bundle.
- The earlier “Workflow at a glance” count mismatch is resolved: the live Cases view derives both displayed labels and counts from the same `workflowStage` function.
- The historical pasted-transcript Playwright failure is superseded by the current real/contract-faithful workflow smoke, which passes 3/3.

### Responsive visual evidence

The permission profile changed after the previously recorded launch blocker, allowing an approved Playwright process to start Chromium. The same temporary harness was rebuilt with the real `CasesWorkspaceClient` and `AppShell`, production build CSS, contract-valid runtime settings, backend Cases data, and an explicit missing-case `404`. No production UI source was changed by the harness.

The six reviewed captures are in `docs/frontend/contracts-phase-screenshots/`:

- `/cases`: `cases-390x844.png`, `cases-768x1024.png`, `cases-1440x900.png`
- `/cases/missing-case`: `cases-missing-390x844.png`, `cases-missing-768x1024.png`, `cases-missing-1440x900.png`

Visual review confirms the approved responsive hierarchy for this slice: mobile uses a single readable column and bottom navigation; tablet uses the compact side rail without narrowing or clipping the case content; desktop uses the full navigation and quiet contextual rail. The unavailable deep-link state remains explicit and non-identifying at all three viewports. All captures preserve decision-support language, readable controls, and safe navigation spacing. No horizontal overflow or covered content was observed.

The earlier failed localhost and Mach-port attempts remain historical evidence of the environment blocker; they are superseded by these successful captures rather than erased.
