# LinguaLens final UX/UI polish report

Date: 2026-07-23
Canonical frontend: `apps/lingualens-app/`
Canonical API: `apps/api/`
Design direction: Airtable-inspired structural restraint adapted to the
LinguaLens clinical workbench

## A. Baseline

The pre-edit freeze is recorded in
`docs/frontend/FINAL_UX_UI_POLISH_BASELINE.md`. It includes the complete changed
file inventory, route and API contracts, screenshots, bundle budgets, known
warnings, workflow behavior, and an external binary patch plus untracked-file
archive. Existing unrelated backend, ML, deployment, release, and documentation
work was preserved; no reset, revert, discard, or checkout-over operation was
used.

The baseline identified five material polish issues:

- executable design tokens and reusable primitives were mixed into
  `globals.css`, while root `DESIGN.md` described an obsolete Outfit/Inter,
  cyan-heavy, large-radius system;
- active component names still said `GlassCard`, `GradientButton`, and
  `liquid-ui` even though their semantics had changed;
- Transcript needed an intentional tablet inspector and a simpler mobile review
  path;
- Findings, Cases, and Settings exposed too much information at once;
- Settings initialized organization-admin lifecycle state from sample
  memberships and invitations, which could survive a malformed or failed
  backend response.

The last issue was held until explicit user approval. It was then changed with a
failing regression test first. Admin lifecycle collections now initialize and
fail empty, and the production backend authorization guards were not changed.

## B. Airtable-inspired adaptations

Adopted principles:

- true-white reading surfaces on a very light cool-neutral canvas;
- near-black ink, neutral hairlines, compact rows, and precise selected states;
- restrained radii and elevation, with whitespace and hierarchy doing more
  work than shadows or decorative color;
- lists, tables, rails, inspectors, and progressive disclosure for structured
  clinical work;
- one obvious primary action and contextual secondary actions.

Intentionally rejected:

- Airtable branding, logos, proprietary typography, and marketing assets;
- coral, peach, mustard, forest, or rainbow palettes as LinguaLens identity;
- marketing-page composition, giant pills, card grids, Kanban as the Today
  landing page, glassmorphism, and decorative gradients;
- any simplification that weakens provenance, consent, stale-state,
  authorization, therapist review, report sign-off, or export gates.

The translation is a quiet clinical workbench: teal is reserved for action,
focus, selection, and workflow progress; amber/red/green retain strict semantic
meaning; clinical information remains descriptive and non-diagnostic.

## C. Design-system changes

The executable source of truth is now split by responsibility:

- `src/design-system/tokens.css`: semantic color, spacing, radius, border,
  shadow, typography, motion, and layering tokens;
- `src/design-system/typography.css`: the shared product type hierarchy;
- `src/design-system/components.css`: reusable panels, buttons, fields, rows,
  selected states, sticky regions, and workbench primitives;
- `src/styles/globals.css`: imports, reset, body/app defaults, generic transition
  binding, and global accessibility behavior only.

Root `DESIGN.md` is the human-readable authority. The product font is
`"Noto Sans Thai", "Noto Sans", system-ui, sans-serif`; Atkinson Hyperlegible is
reserved for an explicit accessibility or Latin-only transcript context.
Motion uses 100 ms selection, 160 ms menu/popover, 220 ms panel, and 0 ms pane
resize timing, with effectively instant reduced motion.

The geometry contract is 4–6 px controls, 8 px panels, and 10–12 px maximum
workspace radii. Ordinary panels use borders rather than elevation. The only
remaining linear gradients are the reviewed line/ruler product motif, not
decorative surface treatments.

`GlassCard`, `GradientButton`, and `liquid-ui.tsx` were migrated to
`WorkspacePanel`, `PrimaryActionButton`, and `workbench-ui.tsx`. No active import
uses the misleading legacy names.

## D. Screen changes

| Screen | Final implementation |
|---|---|
| Today | Preserved the approved focused workbench: one prioritized queue, one next action per row, one prominent Start session action, status grouping inside the queue, and a quiet rail. No Kanban or landing-page split view was introduced. |
| Cases | Reduced the list to Case, Latest activity, Workflow status, and Next action. Desktop prioritizes the selected case's next action; secondary status/activity is compact or disclosed. The table begins only where its action column fits; narrower tablet widths use the compact list plus selected context. Mobile remains list to dedicated detail. |
| Transcript | Keeps lines directly editable and selected with `aria-selected`. Desktop uses an approximately 65/35 editor/inspector split and the editor remains dominant. Tablet portrait switches Audio/QA without narrowing the transcript. Tablet/desktop inspector can collapse; mobile uses the compact sticky player plus fixed, safe-area-aware Save/QA and canonical navigation layers with secondary information disclosed progressively. Secondary line actions remain in overflow. |
| Findings | Presents five level-1 groups: Language sample, Lexical use, Interaction, Speech / intelligibility, and Data quality. Feature detail is level 2; method, reference, provenance, limitations, and clinical caution are level 3 disclosures. Stale and regeneration behavior is unchanged. |
| Settings | `/settings` remains canonical. Desktop uses a category rail and mobile uses a category chooser/drill-down. Shared categories are Account, Organization, Accessibility & Display, Notifications, Privacy & Security, Export, and Help. Organization admins additionally receive Team, Invitations, Audit, Privacy Operations, and Integration Status. Therapists receive no admin navigation, placeholder, control, or admin fetch. Legacy `profile` and `credentials` links normalize to Account and Privacy & Security. |

Settings lifecycle data now fails closed. A malformed or failed admin response
clears memberships, invitations, and readiness and renders explicit
empty/unavailable states. Direct links to every admin category are resolved
against the confirmed identity; unauthorized roles are safely redirected to
`/settings?section=account&notice=not-authorized` without mounting the admin
controller or fetching admin data. Backend organization-admin and audit guards
remain authoritative and unchanged.

## E. Responsive evidence and fidelity ledger

Concept source and captures are under
`docs/frontend/final-polish-concepts/`. Final implementation captures are paired
under `docs/frontend/final-remediation-screenshots/`: `*-viewport-WxH.png` is
the fidelity source and `*-fullpage-WxH.png` is the overflow/workflow-length
source. All affected responsive suites assert that document width does not
exceed viewport width. The shared capture helper clears focus, disables smooth
scrolling, resets both document scroll roots, and waits for `scrollY === 0`
before recording first-viewport evidence.

### Required viewport matrix

| Viewport | Evidence reviewed | Result |
|---:|---|---|
| 390×844 | Today, Cases/list/detail, Transcript, Findings, therapist Settings, admin Settings | Single-column hierarchy is preserved; Settings uses the mobile chooser; Transcript sticky audio plus fixed action/navigation layers reserve content and safe-area space; the first utterance and primary actions remain visible; no horizontal overflow. |
| 768×1024 | Today, Cases/list/detail, Transcript, Findings, therapist Settings, admin Settings | Compact shell plus deliberate content hierarchy; Transcript switches Audio/QA rather than squeezing; Settings uses a readable 220 px rail; no clipping or overflow. |
| 1024×1366 | Today, Cases/list/detail, Transcript, Findings, therapist Settings, admin Settings | Transcript editor remains primary; Cases avoids the too-narrow table; Settings care-team fields stack at the available content width. A visual review found and fixed overlapping admin controls, then a geometry assertion was added. |
| 1280×800 | Today, Cases/list/detail, Transcript, Findings, therapist Settings, admin Settings | Desktop workbench hierarchy and primary actions remain above secondary context; Settings care-team fields use a clean two-column row without collision; no horizontal overflow. |
| 1440×900 | Today, Cases/list/detail, Transcript, Findings, therapist Settings, admin Settings | Full navigation and structured rails are visible; spacing, typography, hairlines, 5–10 px radii, and restrained teal match the concepts; inspector and action columns remain unclipped. |

### Concept-to-implementation ledger

| Surface | Hierarchy and primary actions | Spacing, typography, color, border/radius | Responsive and overflow | Inspector / intentional deviation |
|---|---|---|---|---|
| Today | Matches the focused queue concept; Start session remains the dominant action and each row has one next action. | Noto stack, white reading surface, dark ink, neutral hairlines, restrained teal selection. | Reviewed at all five required viewports with the existing Today matrix; no overflow. | Quiet rail retains real product runtime/safety context rather than concept placeholder copy. |
| Cases | Next action outranks secondary metadata; selected context is compact. | Table/list density, 8 px panels, moderate weights, no decorative shadow. | Compact list is used before the table action column can fit; mobile routes to detail; all five viewports pass. | Real search/filter/role controls remain because they are functional, not decorative concept content. |
| Transcript desktop | Direct editor occupies about 65%; QA/Audio is secondary and collapsible. | Editable lines use hairlines and a clear teal selected state; controls remain visually compact. | 1280×800 and 1440×900 pass without clipping or page overflow. | Real QA, attestation, and save gates remain more detailed than the static concept. |
| Transcript tablet portrait | Transcript remains the primary surface and Audio/QA switches views. | Same typography and row rhythm as desktop; 44 px controls on touch. | 768×1024 passes; inspector never compresses the transcript into a narrow column. | Switchable panel is used instead of simultaneous split, as approved. |
| Transcript tablet landscape | Measured editor-dominant split with collapsible inspector. | Consistent white/neutral/teal system and compact toolbar. | 1024-class evidence passes; no clipped inspector or horizontal page overflow. | Implementation uses the product's 1024×1366 required capture in addition to the 1024×768 concept. |
| Transcript mobile | Context, compact player, editable transcript, and Save/QA remain the task path. | Fixed safe-area controls, 44 px targets, restrained borders, no stacked card wall. | 390×844 proves the first utterance is visible above the action layer, action/navigation layers do not overlap, the final row scrolls clear, and overflow actions remain accessible. | QA/readiness/provenance remain disclosures rather than permanent main-scroll panels. |
| Findings | Five clinical summary groups are level 1; evidence is not exposed simultaneously. | Compact group rows, moderate title weights, semantic availability/caution states. | Reviewed at all five viewports; disclosures wrap without overflow. | Real stale/regeneration and provenance gates remain visible because they are safety behavior. |
| Settings mobile | One category and one drill-down panel at a time; no admin affordance for therapists. | 44 px chooser, 8 px reading panel, Noto stack, neutral hairlines, teal active state. | 390×844 therapist/admin captures pass; desktop/tablet rail also passes all required widths. | Admin captures intentionally show an explicit backend-unavailable state when lifecycle endpoints are unavailable; no sample lifecycle records are substituted. |

Final implementation evidence:

- `docs/frontend/final-remediation-screenshots/` — 50 exact viewport and 50
  paired full-page captures across Today, Cases/list/detail/selector,
  Transcript, Findings, Report/Reports, and therapist/admin Settings.
- `docs/frontend/accessibility-phase-screenshots/` — forced-colors and
  200%-zoom-equivalent evidence.

No material unapproved visual drift remains.

## F. Accessibility evidence

- Transcript line selection exposes `aria-selected` and keeps focus while
  scrolling the selected line into view.
- Save, job, mutation, and error status uses `aria-live`, `role=status`, or
  `role=alert` as appropriate.
- Transcript overflow closes on Escape and restores focus. No modal dialog or
  focus-trapped drawer was introduced by this pass, so a new focus-trap runtime
  path is not applicable.
- Global forced-colors rules and the Chromium forced-colors acceptance capture
  pass.
- Affected form errors are linked with `aria-describedby`.
- Transcript keyboard coverage confirms browser-default shortcuts are not
  intercepted.
- Touch controls maintain at least a 44 px hit area without visually enlarging
  desktop controls.
- The 200%-zoom-equivalent Today capture and affected responsive matrices show
  no covered content.
- Therapist/admin differences are verified at the route resolver, data-fetch
  boundary, and rendered navigation.

## G. Tests and exact commands

Commands were executed from `apps/lingualens-app` unless noted.

| Command | Fresh result |
|---|---|
| `npm run lint` | PASS; two pre-existing warnings remain in `supabase-mfa-panel.tsx` (effect dependency and raw image), plus the framework's `next lint` deprecation notice |
| `npm run typecheck` | PASS |
| `npm test` | PASS — 50 files, 395 tests |
| `npm run verify:bundle` | PASS — production build, 21 routes, all route/shared/async budgets |
| `npm run e2e:smoke` | PASS — 3/3 real/contract-faithful workflow, negative, and report-safety paths |
| `NEXT_PUBLIC_DEMO_MODE=true PLAYWRIGHT_FRONTEND_PORT=3199 PLAYWRIGHT_BACKEND_PORT=8199 npx playwright test e2e/demo-mode.smoke.spec.ts` | PASS — 2/2 explicit demo-mode paths |
| `npx playwright test e2e/today-responsive.spec.ts e2e/cases-responsive.spec.ts e2e/session-transcript-responsive.spec.ts e2e/downstream-responsive.spec.ts e2e/settings-responsive.spec.ts --workers=1` | PASS — 36/36 responsive checks and paired captures |
| `npx playwright test e2e/accessibility-acceptance.spec.ts` | PASS — 2/2 browser acceptance checks |
| `npm run bench:transcript` | PASS — 1/1 benchmark, five runs each at 100/500/1,000 lines |
| `npm test -- src/__tests__/navigation-routes.test.tsx src/__tests__/session-view.test.ts src/__tests__/settings-route-authorization.test.tsx src/__tests__/backend-capabilities.test.ts src/__tests__/remote-state.test.ts src/__tests__/runtime-settings-contract.test.ts` | PASS — 6 files, 74 tests |
| From repo root: `PYTHONPATH=apps/api .venv312/bin/python -m pytest apps/api/tests/test_runtime_settings_contract.py apps/api/tests/test_organization_admin_routes.py apps/api/tests/test_one_day_pilot.py apps/api/tests/test_report_service_v1.py apps/api/tests/test_workflow.py apps/api/tests/test_sql_repository_transactions.py -q` | PASS — 177 tests, 21 warnings |
| From repo root: `PATH="$PWD/.venv312/bin:$PATH" bash scripts/check_project.sh` | PASS — consistency, secret scan, imports, 778 Python tests (3 deselected), migration head/24 tables, clean frontend install, 395 tests and production build |

Bundle evidence:

| Route/chunk | Actual | Budget |
|---|---:|---:|
| Shared first-load JS | 103 kB | 112 kB |
| `/today` | 205 kB | 213 kB |
| `/cases` | 220 kB | 242 kB |
| `/reports` | 212 kB | 229 kB |
| `/settings` | 219 kB | 232 kB |
| `/sessions/[sessionId]` | 219 kB | 230 kB |
| Largest async client chunk | 13.4 kB gzip | 80 kB gzip |

Fresh transcript benchmark on headless Chromium 149 / Apple M2:

| Lines | Ready p95 | Keystroke p95 | Selection p95 | Filter p95 | Worst measured scroll |
|---:|---:|---:|---:|---:|---:|
| 100 | 309.62 ms | 31.8 ms | 25.1 ms | 32.5 ms | 61.10 fps |
| 500 | 203.83 ms | 31.9 ms | 31.3 ms | 31.3 ms | 61.62 fps |
| 1,000 | 289.08 ms | 16.0 ms | 27.7 ms | 35.9 ms | 61.81 fps |

The denser row layout initially exceeded the encoded keystroke budgets after the
benchmark's retired filter selector was corrected. Memoized rows plus
browser-native `content-visibility` now defer off-screen layout/paint while
retaining the complete editable and accessible DOM. The unchanged 500- and
1,000-line budgets pass; JavaScript list virtualization is not justified.

## H. Documentation updates

- Root `DESIGN.md` now defines the LinguaLens design language and anti-patterns.
- `apps/lingualens-app/DESIGN.md` points to the split executable source of truth.
- `docs/frontend/FINAL_UX_UI_POLISH_BASELINE.md` records the pre-edit freeze.
- `docs/frontend/final-polish-concepts/` records the approved concept matrix.
- `PROJECT_STATUS.md`,
  `docs/frontend/UX_UI_COMPLETION_AUDIT_2026-07-17.md`, and
  `docs/frontend/LINGUALENS_UX_UI_MODERNIZATION_REPORT.md` carry the synchronized
  2026-07-23 final-remediation evidence.
- This report is the final A–I implementation and fidelity record.

## I. Remaining intentional limitations

- Today is 205/213 kB after dynamically loading its adapter. Future client code
  must continue to remain within the encoded route budget or obtain an approved
  exception.
- Long transcripts retain the full editable/accessibility DOM and use
  browser-native off-screen layout containment; JavaScript virtualization is
  intentionally not introduced while current 100/500/1,000-line measurements
  remain within budget.
- Two pre-existing non-blocking lint warnings remain in the Supabase MFA panel.
- One repository-gate attempt hit a non-deterministic native
  `numba`/`librosa.pyin` segmentation fault. The isolated test passed 3/3, the
  adjacent scope passed 43/43, and both the exact 778-test scope and full
  repository wrapper passed on rerun; the native audio/ML runtime remains a
  monitoring item outside this visual-polish change.
- A clean install reports 13 dependency advisories (4 moderate, 8 high, 1
  critical); public production launch remains blocked until dependency audit
  policy passes.
- Admin, storage, provider, PDF, integration, and AI-support availability stays
  governed by backend capability and identity state. The UI does not claim an
  unavailable integration is operational and does not substitute sample admin
  lifecycle data.
- Experimental audio remains explicitly experimental. Production identity,
  managed private storage, durable workers, vendor governance, legal/privacy
  approval, and Thai clinical validation remain outside this visual-polish
  completion claim.
- LinguaLens remains decision-support only, not diagnostic. Therapist review,
  transcript attestation, report validation, and sign-off gates remain intact.

## Final status

**FINAL UX/UI POLISH: COMPLETE**
