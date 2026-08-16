# UI/UX Final Design Review — Evidence Ledger

Date: 2026-08-16
Scope: The 5 product surfaces (Today / Cases / Session / Reports / Settings) × 2 viewports (mobile 390×844, desktop 1440×900)
Method: Automated Playwright audit (`apps/lingualens-app/e2e/ui-design-audit.spec.ts`, run as `npm run audit:ui`; the original one-off `review-audit.tmp.mjs` has been superseded) against the running app, applying the 99 UX guidelines of `ui-ux-pro-max` (priority 1–10), plus manual review of screenshots.

## Audit battery

Per surface × viewport the script measured:

| Check | Guideline | Result after fixes |
|---|---|---|
| Touch target size ≥40px | Touch & Interaction (priority 2) | 1 flag only (sr-only skip link, intentional) |
| Text <12px | Typography (priority 6) | **0 across all 10 runs** |
| Heading level skip | Accessibility (priority 1) | **0 across all 10 runs** |
| Multiple h1 | Accessibility | 0 |
| Icon-only buttons without label | Accessibility | 0 |
| Empty links | Accessibility | 0 |
| Missing / decorative alt | Accessibility | 0 |
| Horizontal overflow | Layout & Responsive (priority 5) | false on all 10 runs |
| Line-height <1.35× font | Typography | 0 genuine (see accepted items) |
| Contrast <4.5:1 | Accessibility | 0 genuine (all flagged samples are walk-up artifacts landing on the mobile drawer scrim `bg-black/40`) |

## Automated scan results (after fixes)

All 10 runs (5 surfaces × 2 viewports) report: **headingSkips 0, multipleH1 0, iconOnlyButtons 0, missingAlt 0, decorativeAlt 0, overflow false, smallText 0**. Touch targets: 1 residual per run (the sr-only "Skip to main content" link, which is intentionally 1px until focused).

Raw data: `docs/frontend/ui-review-2026-08-16/findings.json`
Screenshots: `docs/frontend/ui-review-2026-08-16/screenshots/` (10 images)

## Findings fixed during this review

1. **Sidebar nav links 36px → 44px** (`sidebar.tsx`)
   - Nav links, "New session" CTA, and "Log out" all got `min-h-11` (44px) — the previous `py-2` gave ~36px.
2. **Sidebar safety footnote 11px → 12px** (`sidebar.tsx`)
   - "Decision-support research prototype. Therapist review required." was the last sub-12px text on the surface.
3. **Case-detail heading skip h1→h3** (`case-detail.tsx`, `pipeline-progress-bar.tsx`)
   - "Caregiver Consent Verification Required" and "Pipeline Status" were h3 directly after the h1 PageHeader → both now h2.
4. **Mobile menu toggle 32px → 44px** (`app-shell.tsx`)
   - The hamburger button was `p-1.5` (32px) → `h-11 w-11`.
5. **Mobile case-row action button 36px → 44px** (`case-list.tsx`)
   - "Continue workflow" was `min-h-9` → `min-h-11`.
6. **Mobile case-row name link 24px → 44px** (`case-list.tsx`)
   - The case-label link got `min-h-11 min-w-11` so short names still have a real tap target.
7. **Desktop table case-name link 17px → ≥24px** (`case-list.tsx`)
   - The Airtable-style row is clickable for selection, so the name link only needed AA minimum height (`min-h-6 py-0.5`).
8. **Bottom-nav labels 11px → 12px** (`bottom-nav.tsx`)
   - The 5 tab labels were `text-[11px]` → `text-xs` (the last mobile small-text source).
9. **Step-rail numbers 11px → 12px** (`session-context-header.tsx`)
   - The 24px circle step indicators held `text-[11px]` → `text-xs`.
10. **Today group eyebrows 10px → 12px** (`today-workbench-view.tsx`)
    - "Needs action" / "Ready for review" / "Ready for sign-off" were `text-[10px]` on mobile → `text-xs`.

## Accepted as intentional (not bugs)

- **`tightLineHeight` flags (thousands)**: mostly `text-xs` (12px) rows at 1.33 line ratio — the Airtable-style compact list density from Phase 3/5, within Tailwind's default `leading-4` (16px). Also display headings using `leading-tight` (h1 30px/37.5px = 1.25), a deliberate display typography choice per the design system. No body text below 1.4 ratio.
- **`lowContrast` flags**: every flagged sample computes against `bg: #000000`, which is the mobile drawer scrim (`bg-black/40`). The walk-up algorithm stops at the scrim's composited black instead of the light surface behind it. Manual verification on screenshots confirms token-based text (slate/teal on white/light gray) meets contrast.
- **`emptyLinks` on cases (mobile)**: one demo case (`case_04c5db2ac2`) whose `child_code` is whitespace-only and `nickname` is null — a data artifact of the throwaway demo DB, not a UI defect. All other ~950 rows render real labels.
- **The one residual touch target per run**: sr-only skip link, correctly 1px until keyboard focus.

## Non-flagged re-confirmation (manual screenshot review)

- Single primary CTA per screen (Today → Start a session; intake → step-continue; report → Save draft) — Guidelines "primary-action" / "one primary action per page".
- Bottom nav ≤5 items, icon+label, active state teal — "bottom-nav-limit", "nav-label-icon", "nav-state-active".
- Safety wording preserved verbatim (Clinical Safety box, findings/report disclaimers, consent gates) — handoff constraint.
- No emoji-as-icon; lucide icons only — "no-emoji-icons".
- Skeletons replace text loading states; empty states carry a next action — "loading-states", "empty-states".

## Verification

- Unit suite: **493/493 pass** (affected tests: cases-responsive, today-workbench, session-context-header, pipeline-progress-bar)
- TypeScript: clean (`tsc --noEmit`)
- Prior phases verified e2e 50/50 on a fresh backend (unchanged by this review's UI-only edits; the changed components are all covered by the unit suite above).

## Follow-up: /demo routes decision (2026-08-16, after the ledger above was written)

**Decision: keep the demo workspace gated, remove the `/demo/session` prototype leak.**

Audit findings:

- The `/demo/*` workspace (dashboard, upload, transcript, features, report, parent) is a deliberate, tested artifact: it renders only when `NEXT_PUBLIC_DEMO_MODE=true` (off by default — the routes 404 in production), carries a persistent `role="status"` "Sample data demonstration" banner, uses non-normative Thai sample copy, and is covered by `src/__tests__/demo-mode.test.tsx` plus `e2e/demo-mode.smoke.spec.ts` (run under `playwright.demo.config.ts` with its own server, asserting zero links into `/sessions/` or `/cases/`). It does not belong in the therapist surface and already cannot appear there without an explicit opt-in flag.
- `/demo/session` was the one route that broke the boundary: it mounted the **real** `AppShell` + `SessionChatWorkspace` with a fake `demo-001` session id and **fabricated clinical findings** (`riskCue: "moderate_receptive_delay"`, TalkBank scores), using hardcoded `#10a37f` green (banned by DESIGN.md) and emoji. It was orphaned (not in `DemoShell` nav), covered by no test, and `SessionChatWorkspace` was dead code used by nothing else in the app.

Actions:

- **Removed** `/demo/session` plus the now-dead chat-workspace subtree: `session-chat-workspace.tsx`, `session-chat-stream.tsx`, `session-input-bar.tsx`, `clinical-evidence-drawer.tsx`, and their unit tests (`evidence-drawer.test.tsx`, `session-input-bar.test.tsx`). The fabrication of clinical scores no longer ships anywhere.
- **Kept** the six gated demo pages behind the existing env flag — they are the intended sales/demo artifact with a persistent sample-data notice, and removing them would delete tested, documented functionality.
- **Fixed sub-12px text** the audit had flagged in the three named demo pages (transcript/features/report): 10–11px labels → `text-xs` so the demo workspace meets the same typography bar when demo mode is on.

Verification of this follow-up: unit **485/485** (8 tests removed with the deleted test files), `tsc --noEmit` clean, eslint clean, demo e2e **2/2** on a fresh demo server, environment restored (web 3100 → API 8000).

## Follow-up: manual mobile pass + repeatable audit gate (2026-08-16)

### Manual pass (real phone-sized viewport, 200% zoom, forced colors)

Beyond the DOM audit, a scripted Playwright pass (`manual-a11y-pass.tmp.mjs`, since removed) exercised all five surfaces at a 390×844 phone viewport with 200% page zoom and forced colors, checking what the DOM audit cannot see: clipped/truncated text, overlapping elements, clipped interactive controls, and focus-ring visibility.

- **Root-caused and fixed a real layout bug**: `Tailwind Preflight`'s author-origin `section { display: block }` overrides the UA rule that hides non-summary content in a closed `<details>`, so the transcript "Report readiness" accordion leaked its checklist *under the fixed bottom nav* on phones. Added a global rule restoring native closed-`<details>` behavior in `src/styles/globals.css`:
  `details:not([open]) > :not(summary) { display: none; }`.
- **Verified as false positives**: all focus findings (the global 3px teal `:focus-visible` ring renders on real Tab navigation; the probe's programmatic `.focus()` never triggers `:focus-visible`), and all text-clipping flags (intentional single-line truncation of long auto-generated e2e case/report names — compact-list design).
- Unit suite **485/485** pass with the fix; e2e smoke-flow buttons (attest, extract, generate-report) all live outside the now-collapsed details, so the fix is safe for the workflow.

### Repeatable audit gate

The one-off `review-audit.tmp.mjs` is superseded by a repeatable Playwright spec that **fails CI** on the four hard gates — heading skips, sub-12px text, icon-only buttons, horizontal overflow — across the five surfaces at mobile and desktop:

- `apps/lingualens-app/e2e/support/ui-audit-battery.ts` — self-contained battery (serializable into `page.evaluate`).
- `apps/lingualens-app/e2e/ui-design-audit.spec.ts` — self-bootstraps a full session via the API (seeded case → session → manual transcript → QA → attestation → features → report draft), walks 9 surface URLs × 2 viewports, asserts the four gates are clean, writes `findings.json` + screenshots to `test-results/ui-design-audit/`.
- `npm run audit:ui` runs it; CI job `ui-design-audit` in `.github/workflows/deploy.yml` installs Playwright chromium and runs it on every PR/push.

Remaining categories (touch targets, contrast, tight line height, empty links, alt, multiple h1) stay advisory — recorded as evidence, not gates, matching the documented false-positive analysis above.

## Follow-up: touch-target hard gate, benchmark CI, DESIGN.md sync, analysis adapter (2026-08-16)

### Touch targets are now a hard gate

`touchTargets` joined `headingSkips` / `smallText` / `iconOnlyButtons` / `overflow` in `UI_AUDIT_HARD_GATES`. The battery measures each interactive element's effective hit area: sr-only skip links (visually hidden until keyboard focus) are excluded, and inputs inside a wrapping `<label>` are measured by the label's rect since the whole label toggles the control. Enabling the gate immediately caught two real violations:

- Desktop case-name links in the Cases table were only 24px tall (`min-h-6`) — raised to a 44px hit area (`min-h-11`), matching the mobile list. This only surfaced in the full suite (the standalone audit seeded a single case whose row state differed), proving the value of running the gate against realistic data volume.
- Breadcrumb links (Cases → case → session step) were 20px tall — they now carry invisible padding (`py-3 -my-3 px-1.5 -mx-1.5`) for a 44px hit area without changing visual rhythm.
- Report checkbox labels (fallback + sign-off confirmation) got `min-h-11` so their wrapping-label hit area is tappable.

### Transcript benchmark now runs in CI (informational)

New `therapist-benchmark` job in `deploy.yml`: Python deps, Node 22, Playwright chromium, then `npm run bench:transcript` (production build + fresh memory backend, 100/500/1,000 lines with hard budget assertions: keystroke p95 ≤ 50/100ms, scroll ≥ 50/45fps). It is `continue-on-error: true` because the budgets are calibrated on Apple M2 reference hardware and a shared GitHub runner is slower and noisier — it uploads `transcript-benchmark-latest.json` as an artifact so the baseline can be re-baselined before promoting it to a blocking gate. Verified locally on this M2: 1/1 pass with substantial margin.

### DESIGN.md synced with the shipped redesign

Both `DESIGN.md` (root, product authority) and `apps/lingualens-app/DESIGN.md` (executable contract) gained the post-redesign sections that were missing: the Notion-style shell (264px sidebar + drawer + five-item bottom nav + one-line top bar), breadcrumbs with 44px hit areas, the consistent `PageHeader` rhythm, the guided four-step Session Intake with a quiet step rail, the source-path-aware `PipelineProgressBar`, the calm Reports library (status metrics + grouped `DataTable`/compact list), and the shared skeleton / empty-state / inline-blocked-reason states.

### Analysis adapter boundary

New `services/adapters/analysis-adapter.ts` now owns the model-informed decision-support and evidence-review transport (ML readiness, ML decision support generate/load, cues acknowledgement, profile evidence review) plus its backend-shape normalization — the transport boundary DESIGN.md already required. `session-workspace-model.tsx` (the Session controller) imports from the adapter; `lib/workflow.ts` re-exports it only for backward compatibility (existing tests unchanged). New `analysis-adapter.test.ts` (5 tests) covers normalization, the defensive empty result, acknowledgement mapping, readiness mapping, and the review-state PATCH. Unit suite grew 485 → 490.

### Verification

Full e2e suite **52/52** on freshly spawned servers (touch-target gate included), unit **490/490**, `tsc` + eslint clean. Environment restored (web 3100 → API 8000).

---

## Follow-up: full therapist e2e suite in CI (2026-08-16)

The one-off local e2e runs are now a CI gate too. Until this point only the `ui-design-audit` spec ran in CI; the full Playwright suite (52 tests across 10 spec files: workflow smoke, responsive contracts for all five surfaces, accessibility acceptance, audit) only ran locally. That was the largest verification gap — a workflow regression (e.g. a consent gate, transcript flow, or attestation break) would not be caught until a manual local run.

- New `therapist-e2e` job in `.github/workflows/deploy.yml`, mirroring the proven `ui-design-audit` recipe: Python 3.12 + API deps (Playwright spawns its own memory-repo backend with CORS via `webServer`), Node 22 + `npm ci`, Playwright chromium, then `npx playwright test` — the config's `webServer` starts a fresh memory backend on 8000 and the Next dev server on 3100 per run, exactly as CI needs. A second step runs the gated demo workspace smoke (`npx playwright test -c playwright.demo.config.ts`, its own dedicated servers) so demo coverage is preserved.
- The suite is fully self-bootstrapping: every spec seeds from the memory repo's `case_demo_001` or creates its own records through the API (case → session → transcript → QA → attest → features → report draft), with no hardcoded local IDs or external dependencies. Verified locally on freshly spawned servers: **52/52** main suite + **2/2** demo smoke.
- Housekeeping: `apps/lingualens-app/test-results/.last-run.json` was accidentally committed (Playwright rewrites it every run); now untracked and `test-results/` + `playwright-report/` gitignored.

## Follow-up: feature-extraction into the adapter, blocking benchmark gate, practice dashboard (2026-08-16)

### Analysis adapter now owns feature-extraction transport too

`lib/workflow.ts` shrank another ~60 lines: `getBackendSessionFeatures`, `getBackendFeatureDefinitions`, and `runBackendAnalysis` (the extraction POST that folds QA + features into the workflow summary via the `summarizeAnalysis` domain helper) moved into `services/adapters/analysis-adapter.ts`. The unexported `BackendQa` / `BackendFeatures` / `BackendFeatureDefinition` wire types are now exported from `workflow.ts`; `workflow.ts` re-exports the moved functions for backward compatibility; `session-workflow-service.ts` and `session-workspace-model.tsx` import the transport directly from the adapter per DESIGN.md. Adapter tests grew 5 → 9 (session-features GET, definitions mapping, both extraction paths). Unit suite 490 → 494.

### Benchmark CI job promoted to a blocking baseline gate

Two fresh production-build benchmark runs were captured (keystroke p95 26–39 ms, scroll ~61 fps on this M2) and committed as `benchmarks/results/transcript-benchmark-reference.json` (worst of the two runs per metric). New `scripts/check-benchmark-baseline.mjs` (`npm run bench:check`) compares the latest run against the reference with a 2× latency tolerance plus absolute scroll-fps floors (45 fps @ 500 lines, 40 fps @ 1,000 lines) — a real regression exceeds even the tolerant band while shared-runner noise does not. The `therapist-benchmark` CI job is now blocking: `continue-on-error` removed, and `npm run bench:check` runs right after the benchmark. `benchmarks/README.md` documents the gate and the recalibration procedure.

### New product surface: Practice dashboard (`/dashboard`)

- **Backend**: `GET /api/v1/dashboard/summary` (`apps/api/app/api/v1/routes/dashboard.py`) aggregates the org-scoped pipeline — cases total + consent counts, sessions total + stage counts (transcript / features / ML review / report), report sign-off counts, and the 10 most recent sessions — as a single read-only payload. Three API tests cover the seeded case, a full-pipeline session, and org scoping.
- **Frontend**: `src/app/dashboard/page.tsx` (server component, `force-dynamic`) + `src/features/dashboard/components/practice-dashboard-view.tsx` — calm stat cards, consent breakdown, pipeline progress, report sign-off, and a recent-sessions list (desktop table / mobile stacked cards, no horizontal overflow). Data flow via `getDashboardSummary()` in `workflow.ts`. Sidebar-only nav item (bottom nav stays at 5 items; `forBottomNav` filter added to `getWorkbenchNavigation`). Unit tests: 4 (stats, session deep-links, empty state, unavailable fallback).
- **Server-render fix**: the dashboard is the first server component to fetch the API, which exposed a latent bug — `isSupabaseRuntimeContext()` called client-only storage loaders from the server (Next blocked the import). It now returns false server-side until runtime settings resolve the auth mode. `docs/frontend` screenshots re-captured on the e2e runs.

### Verification

Full e2e suite **52/52** (audit now covers 10 surfaces incl. the dashboard at both viewports — the mobile gate caught and fixed the min-width recent-sessions table), unit **498/498**, `tsc` + eslint clean, API tests green. Environment restored (web 3100 → API 8000, API started with CORS for the preview origin; run doc updated with the verified launchd recipe).

## Follow-up: root `/` now lands on the practice dashboard (2026-08-16)

The identifier-less root route redirects to `/dashboard` instead of `/today`, so opening the app (or clicking the LinguaLens brand on mobile) lands on the practice overview. Post-login destinations follow: mock login (`/dashboard?role=...`) and supabase login (`/dashboard`) for therapist/supervisor roles; org-admin still goes to `/settings?scope=admin`. Today remains a distinct nav item (bottom-nav primary, work queue), Dashboard is sidebar-only — its `aria-current="page"` is set when the route is active. Tests updated (root-redirect assertion now `/dashboard`, login hrefs, dashboard session-list duplicates due to the desktop table + mobile cards).

## Follow-up: session-level feature trends on the dashboard (2026-08-16)

`/dashboard` now plots one language-sample feature across a case's sessions over time — the longitudinal progress view the aggregate stats could not show.

- **Backend**: `GET /api/v1/dashboard/summary` gains `feature_trends` — a `features` catalogue (MLU words, NDW, Type–Token Ratio, total words, unintelligible ratio) plus per-case series of `{session_id, session_date, values}` sorted by date, built only from sessions with a persisted `FeatureSet`. Alias mapping normalizes extractor naming: the API provider's long names (`mean_length_of_utterance_words`, `number_of_different_words`, `type_token_ratio`) and the root extractor's short names (`mluw`, `ndw`, `ttr`) resolve to the same canonical keys; string/`None` values (e.g. morpheme-MLU `"not_available"`) are excluded. New API test seeds two feature sets with mixed naming and asserts the series, ordering, canonical keys, and label fallback.
- **Frontend**: new `language-progress-chart.tsx` — an accessible SVG line chart (dots + polyline only; no SVG text, labels are real DOM text so the touch/typography audit gates stay green) with labeled `Feature`/`Case` selects, a visible date/value table as the data alternative (WCAG chart → table), single-point hint, and per-case/feature empty states. `DashboardSummary` type extended; section mounted in `PracticeDashboardView` under "Language progress". Unit tests: 5 (default series renders, feature switch re-plots, case switch, no-data empty state, session-empty state) — suite 498 → 500.
- **Verified live**: on the real API the C-PROGRESS case renders a 2-point MLU trend (1.67 → 4.0) with chart + table; feature selector exposes all 5 metrics.

## Follow-up: reference bands, deep-linked trends, CaseDetail, report trends (2026-08-16)

Four follow-ups from the trend chart, all landed:

1. **Reference-band overlay** — `feature_trends.cases[].reference` now carries the typical-development (TD) IQR band (q1/median/q3, age band + task) computed from the reference-evidence artifact via a new `ReferenceEvidenceProvider.td_reference_band()` (maps canonical cell columns to trend keys; NDW has no cell stats and is omitted). The chart shades the IQR band and draws a dashed median line with a caption ("Reference band (typical development, 60-71 months, toyplay): median 2 · IQR 1–3"). Degrades to no-band when the artifact is absent (dev default) — verified by a test that seeds a minimal artifact through the env var.
2. **Deep-linked points** — every chart dot has a 44px invisible hit-area anchor (focusable ring for keyboard) and every date cell is a link, both to `/sessions/{id}?case_id={case}`. New `GET /cases/{id}/feature-trend` (org-scoped, 404 for other orgs) powers CaseDetail.
3. **CaseDetail trend** — "Language progress" card added; the workspace hook fetches the per-case trend with a shape-validated fallback to empty so strict mocks / transient failures never take detail down (6 case-detail unit suites untouched and passing).
4. **Report full-series progress** — `report_service.previous_session_feature_sets()` returns every prior non-stale feature set (oldest first; the singular helper is preserved for compatibility); `draft_report` concatenates all of them into `previous_features` and the template provider now emits first→last trajectory lines ("mean_length_of_utterance_words: 2.4 → 3.1 across 3 reviewed sessions (descriptive trend).") alongside the preserved per-session delta lines when ≥2 prior sessions exist.

Verification: API 354/354 (new: TD band attach, no-artifact degrade, per-case endpoint, org 404, multi-session report trend), unit 502/502, tsc + eslint clean, e2e **52/52** (audit covers the new chart/banners at both viewports). Live: dashboard overlays + date links carry case context; CaseDetail renders the single-session hint.

## Follow-up: report Progress section now carries the reference band (2026-08-16)

The generated report's `## Progress Comparison` section now includes the same
longitudinal context as the dashboard trend chart. `draft_report` computes the
typical-development band once per draft via `ReferenceEvidenceProvider.td_reference_band()`
(mapped canonical→runtime feature names) and passes it through the new
`ReportGenerationInput.reference_band` field. The template provider adds a
`## Reference Comparison` block that compares each tracked feature's latest
value against the TD IQR — `mean_length_of_utterance_words: latest 2.5 is
within the typical-development reference IQR (1–3, median 2) for ages 60-71
months (toyplay).` — with a descriptive-data disclaimer. The block is
independent of prior sessions (works for a first-session draft) and degrades
cleanly to absent when the artifact or language/task support is missing.
Backend-only; no frontend change. API 356/356 (2 new tests: band present with
seeded artifact, omitted without), unit 502/502 untouched, e2e 52/52.

## Follow-up: AI-assisted review Progress Summary carries the reference band (2026-08-16)

The Findings-side AI-assisted review now speaks the same reference language as
the dashboard chart and the printed report. The band computation was extracted
into a shared module-level helper `runtime_td_reference_band(age_months,
session_type)` in `reference_evidence.py` (canonical cell columns → runtime
feature names, returns None to degrade silently); `report_service` delegates to
it and `ai_review_service.create_ai_review` calls it directly, so one mapping
drives all three surfaces. The AI review's "Progress Summary" assistance area
now appends a "Reference comparison:" clause to its summary and adds
"Reference band (typical development, ages 60-71 months, toyplay): ..." plus the
descriptive-data disclaimer to contributing_factors — phrased exactly like the
report's `## Reference Comparison` block, and it works even for a first-session
draft (no prior session required). Without the artifact it degrades to the
previous behavior.

Verification: 2 new workflow tests (band present with seeded artifact, omitted
without); API 335/335 across runnable suites (test_reference_evidence_provider.py
is skipped locally because numpy is not installed in this venv — pre-existing),
unit 502/502 + tsc clean (backend-only change), e2e unaffected.

## Follow-up: Findings view renders the AI-assisted Progress Summary card (2026-08-16)

The Findings view now surfaces the AI-assisted review's Progress Summary
inline, so therapists see the longitudinal context (previous-session deltas plus
the typical-development reference band when available) without opening a
report. The frontend previously never consumed the `/ai-review` endpoints; new
`AiReview`/`AiAssistanceArea` types and `getAiReview`/`generateAiReview`
adapter functions (analysis adapter, re-exported from `lib/workflow.ts`) carry
the wire shapes, hydration loads the review alongside ML decision support into
`WorkflowState.aiReview`, and a `ProgressSummaryCard` component renders the
summary + contributing factors (which include the "Reference band (typical
development, ages X months, task)" line and the descriptive-data disclaimer).
When no review exists the card offers "Generate AI-assisted review" with a
workflow-gates reason (aria-describedby) when blocked (features not extracted /
transcript not attested / stale findings). The card lives in its own component
to keep `session-findings-view.tsx` within its documented 500-line container
budget.

Verification: 3 new unit tests (card shows reference-band context, disabled
reason when features missing, enabled when gates pass); unit 505/505, tsc +
eslint clean, e2e 52/52 incl. the UI-design audit at both viewports. Live:
full-pipeline session renders the card with the "AI-assisted review" badge and
the two-session requirement message (no reference artifact in dev, so the band
degrades silently — same as dashboard/report).

## 2026-08-16 — Shared IQR classifier across evidence surfaces

Removed the third copy of below/within/above-IQR boundary logic. Added
`iqr_position(value, q1, q3)` in `reference_evidence.py` (inclusive band
boundaries: value == q1/q3 counts as within) and used it in all three places
that classify a value against the TD reference IQR: ML profile evidence
(`_associated_features`, positions `below_iqr`/`within_iqr`/`above_iqr`), the
AI-assisted Progress Summary, and the printed report's Reference Comparison
(prose below/within/above via `.replace("_iqr", "")`). One classifier, one
boundary semantics — the evidence review can never drift from the report or
Findings.

Verification: 2 new API tests (classifier boundary semantics incl. inclusive
q1/q3; end-to-end ML review with the reference provider asserts every TD
associated-feature position equals `iqr_position(observed, q1, q3)` recomputed
from the same artifact). API suites 337/337 pass (test_workflow +
test_report_service_v1 + test_dashboard_summary 106/106; full run excludes
test_reference_evidence_provider.py — numpy absent from the venv, pre-existing
env limitation). Backend-only change; frontend untouched.

Follow-up: deduplicated the reference-statistic formatter too — moved
`band_number()` (2.0 -> "2", 1.23 kept) into reference_evidence.py and removed
the identical `_band_number` copies from ai_review_service.py and
report_providers.py. Report/AI-review output strings unchanged (same rounding
semantics). 1 new unit test; suites 107/107.
