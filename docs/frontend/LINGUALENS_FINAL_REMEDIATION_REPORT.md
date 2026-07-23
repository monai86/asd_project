# LinguaLens final UI remediation report

Date: 2026-07-23
Canonical frontend: `apps/lingualens-app/`
Canonical API: `apps/api/`
Status scope: final UI remediation and Airtable-inspired design alignment

## A. Evidence-first issue matrix

The baseline classification was recorded before production UI edits in
`docs/frontend/FINAL_UI_REMEDIATION_AUDIT.md`. The table below records the final
state; it does not retroactively relabel the baseline evidence.

| ID | Reported issue | Verified state | Fix | Final evidence |
|---|---|---|---|---|
| A | Named `DESIGN.md` authority omitted from review archive | Confirmed | Added root `DESIGN.md` to the canonical release scope and retained the app document as implementation detail | `scripts/release_scope.py`; `tests/test_release_scope.py`; repository gate 778/778 |
| B | Astryx competed with LinguaLens/Tailwind | Confirmed | Removed packages, lock entries, CSS imports, Theme/Link providers, wrapper consumers and conflicting instructions | dependency/import scans; `final-ui-remediation-contract.test.tsx`; frontend 395/395 |
| C | Amber `accent-subtle` carried selected-state semantics | Confirmed | Changed it to teal `#4f9fa5`; kept amber only in warning roles | `tokens.css`; selected/warning/error/success contract assertions; responsive captures |
| D | Dead primitives and unsupported percentages remained | Confirmed | Removed six dead exports and the hard-coded Report progress summary | source scan; Report tests; `final-ui-remediation-contract.test.tsx` |
| E | Transcript first-viewport fidelity was materially behind concepts | Confirmed | Compressed context/status/filter chrome, preserved direct editing, made editor dominant, retained switchable/collapsible inspector, fixed the mobile Save/QA layer above fixed navigation, and moved secondary row actions to overflow | five-viewport ledger, paired captures, responsive 36/36, accessibility 2/2 |
| F | Exact-size filenames contained full-page images | Confirmed | Split all evidence into `viewport` and `fullpage` files | 50 exact viewport PNGs plus 50 full-page PNGs; `sips` dimension audit |
| G | Airtable alignment was asserted but not systematic | Partially confirmed | Added principle/screen matrices, corrected confirmed gaps, and replaced Today card-per-item anatomy with one hairline-divided priority queue | `AIRTABLE_DESIGN_ALIGNMENT.md`; concept-to-implementation review; Today density regression |
| H | Cases might still be card-heavy | Already fixed | Preserved the structured list/master-detail architecture; only recaptured evidence | Cases source, tests and paired captures |
| I | Findings delayed the five clinical groups | Partially confirmed | Moved the five groups first, reduced workflow state to a compact strip and placed provenance after | Findings tests and five-viewport captures |
| J | Mobile Settings lacked category-list drill-down | Partially confirmed | Added category index → selected category behavior while preserving `/settings` and server role resolution | Settings route/access tests and therapist/admin captures |
| K | Generic safety copy repeated simultaneously | Partially confirmed | Removed only verified duplicates; retained global, contextual and action-blocking boundaries | copy scan, workflow tests and reviewed captures |

## B. `DESIGN.md` authority

`DESIGN.md` at repository root is the single human-readable product authority.
It defines visual character, screen contracts, accessibility, motion, clinical
safety and authorization boundaries. It is included in source-review packaging.

`apps/lingualens-app/DESIGN.md` is an implementation contract. It explicitly
defers to root `DESIGN.md` and documents frontend architecture without defining
a second palette or product language. Executable responsibilities are split:

- `src/design-system/tokens.css` — semantic tokens;
- `src/design-system/typography.css` — type hierarchy;
- `src/design-system/components.css` — workbench/component behavior;
- `src/styles/globals.css` — imports, reset, body defaults and global
  accessibility behavior.

The unified font value is identical in root authority, app contract and tokens:
`"Noto Sans Thai", "Noto Sans", system-ui, sans-serif`. Atkinson
Hyperlegible remains optional only for an explicit accessibility mode or a
verified Latin-only transcript context.

## C. Astryx decision

**Removed.**

Astryx supplied a global reset/theme and generic layout wrappers but no unique
workflow or accessibility behavior. It overlapped with Tailwind and the
LinguaLens semantic system, and its agent rules conflicted with repository
conventions. Removing it leaves one implementation foundation:

`LinguaLens semantic design system + Tailwind + focused product primitives`.

No production import, package dependency, theme wrapper, CSS import or active
agent instruction remains.

## D. Semantic token audit

| Token/family | Final value | Intended and verified semantic |
|---|---:|---|
| `accent` | `#08747d` | Primary action and active interaction |
| `accent-strong` | `#074f56` | Strong teal text/hover emphasis |
| `accent-soft` | `#e2f2f3` | Pale selected/active surface |
| `accent-subtle` | `#4f9fa5` | Teal selected/current border; no warning meaning |
| `warning-*` | amber (`#fffbeb`, `#f59e0b`, `#92400e`) | Caution, review required and stale preconditions |
| `danger-*` | red (`#fef2f2`, `#f87171`, `#b91c1c`) | Error, destructive and blocking state |
| `success-*` | green (`#ecfdf5`, `#10b981`, `#047857`) | Attested/current/success state |
| `info-*` | indigo (`#eef2ff`, `#818cf8`, `#4f46e5`) | Neutral informational/processing state |

State remains communicated through text, role and icons in addition to color.
Forced-colors rules preserve selected/focus/control boundaries.

## E. Dead component cleanup

Removed as unused or misleading:

- `AppHeader`
- `QuickActionCard`
- `SessionCard`
- `ResultMetricCard`
- `SmallListRow`
- `PrimaryActionRow`
- `ProgressSummaryCard`

The last component was active but displayed hard-coded Language, Fluency,
Listening and Pronunciation percentages plus an unsupported trend. No backend
provenance supported those conclusions. Appropriate shared primitives such as
`WorkspacePanel`, `PrimaryActionButton`, `SafetyNote` and `WorkflowStep` remain.

## F. Transcript fidelity

| Viewport | Final implementation | Fidelity result |
|---:|---|---|
| 390×844 | Compact organization/session context, sticky audio, compact filter, directly editable selected row, fixed Save/QA layer and fixed canonical navigation | Aligned; the first utterance remains visible above non-overlapping safe-area layers, while controls retain 44px targets and timestamp/speaker editing |
| 768×1024 | Full-width editor with Audio/QA switching rather than a squeezed split | Aligned; no horizontal overflow or covered content |
| 1024×1366 | Editor-dominant approximately 65/35 split with collapsible inspector | Aligned; inspector remains unclipped and focus restoration is covered |
| 1280×800 | Direct rows appear in the first viewport; editor remains above 60% width | Aligned; backend status/provenance stays discoverable but compact |
| 1440×900 | Compact context/tabs followed immediately by editor/inspector workbench | Aligned; full-page capture contains all four sample rows and downstream controls |

The final 100/500/1,000-line benchmark initially revealed a real regression
after its retired filter-button selector was corrected: dense off-screen rows
caused keystroke p95 of 79.2 ms at 500 lines and 136.9 ms at 1,000 lines.
Budgets were not raised. Memoized rows and browser-native
`content-visibility: auto` now defer off-screen layout/paint while keeping every
row in the editable DOM and accessibility tree. Fresh p95 is 31.9 ms at 500
lines and 16.0 ms at 1,000 lines; worst sampled scrolling is 61.62 and 61.81
fps respectively.

## G. Airtable-inspired alignment matrix

The independent Airtable design analysis is visual/interaction inspiration,
not product ownership, a dependency or branding.

| Principle | Final state | LinguaLens implementation |
|---|---|---|
| Canvas | Aligned | True/near-white work surfaces on cool-neutral chrome |
| Typography | Aligned | Unified Noto Thai/Latin stack, moderate hierarchy, no dashboard-scale display type |
| Borders | Aligned | Neutral 1px hairlines carry ordinary separation |
| Geometry | Aligned | 6px controls, 8px panels and 10px shell radius; pills reserved for status |
| Density | Aligned | Queue, lists, editable rows and progressive disclosure precede analytics/chrome |
| Actions | Aligned | One dominant action; restrained secondary and contextual actions |
| Navigation | Aligned | Quiet five-destination shell with precise selection |
| Tables/lists | Aligned | Today, Cases and Transcript use structured row anatomy rather than card grids |
| Inspectors | Aligned | Transcript Audio/QA is contextual, collapsible and width-safe |
| Elevation | Aligned | Ordinary panels are border-led; shadows are limited to temporary layers |

Intentional deviations are limited to authenticated organization/user context,
touch-sized editable transcript controls, safety-relevant provenance, and the
canonical “Session Results” wording. None changes information architecture,
weakens authorization or makes a clinical claim.

## H. Screenshot methodology

Final evidence lives in `docs/frontend/final-remediation-screenshots/`.

- `*-viewport-WxH.png` is used for concept fidelity.
- `*-fullpage-WxH.png` is used for total workflow length and overflow.
- Before viewport capture, the shared helper clears focus, disables smooth
  scrolling, resets both document scroll roots and waits for `scrollY === 0`;
  this prevents a previously focused control from falsifying first-viewport
  evidence.
- All viewport PNGs were verified at exactly 390×844, 768×1024, 1024×1366,
  1280×800 and 1440×900.
- The unified responsive run generated 50 viewport and 50 full-page images for
  Today, Cases/list/detail/selector, Transcript, Findings, Report/Reports and
  therapist/admin Settings.
- The primary visual hard gate compared Today, Cases, Transcript, Findings and
  Settings against approved concepts at all five viewports. Transcript was
  visually rechecked after the performance optimization and after correcting a
  completion-audit defect where the mobile action bar was technically sticky
  but initially outside the viewport. Geometry assertions now prove the first
  utterance, action layer, navigation layer and final row do not obscure one
  another; full-page evidence still renders every sample row. A final Today
  comparison also caught card-per-item density that automation had previously
  accepted: the regression failed with only two rows intersecting each desktop
  viewport, then passed after the queue became hairline-divided with at least
  three rows at 1280×800 and four at 1440×900.

## I. Tests

Commands were executed on the current worktree. Frontend commands ran from
`apps/lingualens-app` unless shown otherwise.

| Command | Fresh result |
|---|---|
| `npm run lint` | Exit 0; two preserved warnings in `supabase-mfa-panel.tsx` plus Next lint deprecation notice |
| `npm run typecheck` | PASS |
| `npm test` | PASS — 50 files, 395 tests |
| `npm run build` | PASS — Next.js 15.5.20, 21 routes |
| `npm run verify:bundle` | PASS — all shared/route/async budgets |
| `npm run e2e:smoke` | PASS — 3/3 real/contract-faithful workflow and safety paths |
| `NEXT_PUBLIC_DEMO_MODE=true npx playwright test e2e/demo-mode.smoke.spec.ts --workers=1` | PASS — 2/2 explicit sample-mode paths |
| `npx playwright test e2e/today-responsive.spec.ts e2e/cases-responsive.spec.ts e2e/session-transcript-responsive.spec.ts e2e/downstream-responsive.spec.ts e2e/settings-responsive.spec.ts --workers=1` | PASS — 36/36 and paired evidence |
| `npx playwright test e2e/accessibility-acceptance.spec.ts --workers=1` | PASS — 2/2 forced-colors/zoom/focus acceptance paths |
| `npm run bench:transcript` | PASS — 1/1; five repetitions each at 100/500/1,000 lines |
| `PYTHONPATH=apps/api .venv312/bin/python -m pytest apps/api/tests/test_runtime_settings_contract.py apps/api/tests/test_organization_admin_routes.py apps/api/tests/test_one_day_pilot.py apps/api/tests/test_report_service_v1.py apps/api/tests/test_workflow.py apps/api/tests/test_sql_repository_transactions.py -q` | PASS — 177 tests, 21 warnings |
| `PATH="$PWD/.venv312/bin:$PATH" bash scripts/check_project.sh` | PASS — consistency, secret scan, imports, 778 Python tests/3 deselected, migration head/24 tables, clean install, 395 frontend tests and build |

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

Benchmark evidence (headless Chromium 149, Apple M2, 1280×720):

| Lines | Ready p95 | Keystroke p95 | Selection p95 | Filter p95 | Worst scroll |
|---:|---:|---:|---:|---:|---:|
| 100 | 309.62 ms | 31.8 ms | 25.1 ms | 32.5 ms | 61.10 fps |
| 500 | 203.83 ms | 31.9 ms | 31.3 ms | 31.3 ms | 61.62 fps |
| 1,000 | 289.08 ms | 16.0 ms | 27.7 ms | 35.9 ms | 61.81 fps |

## J. Remaining limitations

- A clean `npm ci` reports 13 dependency advisories: 4 moderate, 8 high and 1
  critical. Public production launch remains blocked until the dependency audit
  policy passes; no force-upgrade was attempted during this UI goal.
- Full lint/build emits two pre-existing warnings in
  `src/components/supabase-mfa-panel.tsx`: one effect dependency and one raw
  image warning.
- One repository-gate attempt terminated in native
  `numba`/`librosa.pyin` code while extracting acoustic context. The isolated
  test then passed 3/3, the adjacent 43-test scope passed, the exact 778-test
  scope passed, and the complete repository wrapper passed on rerun. No
  backend/ML algorithm was changed without a reproducible root cause; this
  native-runtime observation remains explicit monitoring evidence.
- The first repository-gate attempt used system Python 3.13, which lacked
  `alembic`, after detecting an unsupported stale `.venv`. The unchanged gate
  passed when explicitly run through the verified `.venv312` Python 3.12.13
  environment. Neither virtualenv was deleted or overwritten.
- Staging and production have not been verified against live Supabase Auth/RLS,
  managed private Storage, durable workers, managed secrets, backup/restore and
  production observability.
- LinguaLens remains decision-support only. The ML evidence is public
  English-language reference evidence, not Thai clinical validation or an ASD
  diagnostic model.

These limitations do not leave a confirmed UI-remediation issue unresolved,
but they remain explicit launch and clinical-readiness constraints.

## Final status

**FINAL UI REMEDIATION: COMPLETE**
