# LinguaLens UX/UI Baseline Audit

Date: 2026-07-13  
Product version: v1.6.3  
Canonical frontend: `apps/lingualens-app/`  
Canonical API: `apps/api/`

## Audit boundary

This document records the frontend state before the UX/UI modernization. No production UI code was changed while producing it. The existing dirty worktree is intentional work-in-progress and is the baseline to preserve and build on.

The current tracked worktree was backed up before audit work to:

```text
/tmp/lingualens-pre-modernization-worktree-2026-07-13.patch
```

The patch is 2.1 MB and was produced with `git diff --binary HEAD`. Git patches do not include untracked files; the untracked frontend files are listed separately below.

## 1. Current changed-file inventory

The repository was on `main`, one commit ahead of `origin/main`, with a broad pre-existing dirty worktree. The tracked frontend work-in-progress comprises:

- `apps/lingualens-app/package.json`
- `apps/lingualens-app/package-lock.json`
- `apps/lingualens-app/src/__tests__/api-auth.test.ts`
- `apps/lingualens-app/src/app/login/page.tsx`
- `apps/lingualens-app/src/components/action-button.tsx`
- `apps/lingualens-app/src/components/active-organization-summary.tsx`
- `apps/lingualens-app/src/components/app-shell.tsx`
- `apps/lingualens-app/src/components/audio-upload-confirm-panel.tsx`
- `apps/lingualens-app/src/components/bottom-nav.tsx`
- `apps/lingualens-app/src/components/browser-audio-recorder.tsx`
- `apps/lingualens-app/src/components/cases-workspace-client.tsx`
- `apps/lingualens-app/src/components/data-table.tsx`
- `apps/lingualens-app/src/components/empty-state.tsx`
- `apps/lingualens-app/src/components/liquid-ui.tsx`
- `apps/lingualens-app/src/components/mobile-header.tsx`
- `apps/lingualens-app/src/components/mock-login-form-client.tsx`
- `apps/lingualens-app/src/components/page-header.tsx`
- `apps/lingualens-app/src/components/pipeline-progress-bar.tsx`
- `apps/lingualens-app/src/components/report-summary-client.tsx`
- `apps/lingualens-app/src/components/reports-workspace-client.tsx`
- `apps/lingualens-app/src/components/right-rail.tsx`
- `apps/lingualens-app/src/components/safety-notice.tsx`
- `apps/lingualens-app/src/components/session-workspace-client.tsx`
- `apps/lingualens-app/src/components/settings-workspace-client.tsx`
- `apps/lingualens-app/src/components/sidebar.tsx`
- `apps/lingualens-app/src/components/stat-card.tsx`
- `apps/lingualens-app/src/components/supabase-login-form-client.tsx`
- `apps/lingualens-app/src/components/supabase-workspace-access-gate.tsx`
- `apps/lingualens-app/src/components/topbar.tsx`
- `apps/lingualens-app/src/components/transcript-editor-panel.tsx`
- `apps/lingualens-app/src/components/transcription-job-status-panel.tsx`
- `apps/lingualens-app/src/components/work-queue-dashboard.tsx`
- `apps/lingualens-app/src/components/workflow-stepper.tsx`
- `apps/lingualens-app/src/components/workspace-access-gate.tsx`
- `apps/lingualens-app/src/lib/api.ts`
- `apps/lingualens-app/src/styles/globals.css`

Untracked frontend work-in-progress:

- `apps/lingualens-app/.claude/`
- `apps/lingualens-app/DESIGN.md`
- `apps/lingualens-app/open-next.config.ts`
- `apps/lingualens-app/src/app/demo/`
- `apps/lingualens-app/src/components/demo-shell.tsx`
- `apps/lingualens-app/wrangler.jsonc`

The tracked frontend diff contains about 12,300 additions and 6,900 removals, almost entirely because of the lockfile. The source changes are primarily a visual-token normalization pass, authentication/runtime work, and deployment preparation. They do not yet implement the requested route consolidation or feature-oriented architecture.

### Existing work that aligns with modernization

- The live CSS moves toward calmer white reading surfaces, teal accent usage, restrained radii, reduced shadows, and shared `workspace-panel`, `reading-surface`, and `control-strip` primitives.
- The shell has a skip link, mobile bottom navigation, responsive content gutters, and reduced-motion handling.
- Workflow safety messages, consent gates, report locks, and experimental-audio labels are explicit.
- Runtime authentication and organization context are being strengthened.
- The frontend builds and its unit/component suite passes after installing the committed dependencies.

### Existing work that conflicts with or blocks modernization

- Navigation still exposes both Home and Today.
- Legacy routes still mount workflow implementations instead of compatibility redirects.
- The same monolithic components remain the primary implementation surface.
- Direct data access remains in visual components.
- Backend failure can still retain or initialize fallback/sample records.
- Demo routes are untracked but publicly routable and are not protected by an environment flag.
- `DESIGN.md` describes an Airtable-derived editorial system and Haas typography while the live app uses clinical teal tokens and Atkinson Hyperlegible.
- The current smoke test encodes the old standalone route sequence and fails before reaching transcript review.

These conflicts are understood well enough to document, but production replacements still require the approved design and implementation plan. No conflicting work has been replaced.

## 2. Current route map

| Route | Current implementation | Backend/data mode | Audit result |
|---|---|---|---|
| `/` | Renders `WorkQueueDashboard active="Home"` | Static local work-queue data | Duplicates `/today`; does not redirect |
| `/today` | Renders the same `WorkQueueDashboard` | Static local/demo fallback data | Canonical candidate, but duplicated |
| `/cases` | `CasesWorkspaceClient` | Backend list with preinitialized fallback cases | Canonical route, silent fallback risk |
| `/cases/[caseId]` | Same `CasesWorkspaceClient` with ID | Backend detail plus fallback substitution | Canonical route, mixed responsibilities |
| `/sessions/[sessionId]` | `SessionWorkspaceClient` with `view` query | Backend plus session-storage workflow state | Canonical route exists but views are not validated |
| `/record` | Mounts `SessionWorkspaceClient view="record"` | Backend/local workflow | Competing workflow route |
| `/review-transcript` | Mounts `SessionWorkspaceClient view="transcript"` | Backend/local workflow | Competing workflow route |
| `/transcript` | Re-exports `/review-transcript` | Same as above | Alias, not a safe redirect |
| `/results` | Mounts `SessionWorkspaceClient view="results"` | Backend/local workflow | Competing pre-report workflow route |
| `/report-summary` | Mounts `ReportSummaryClient` | Backend/local workflow | Independent report editor |
| `/reports` | `ReportsWorkspaceClient` | Backend list | Library plus duplicated detail/progress behavior |
| `/settings` | `SettingsWorkspaceClient` with query-selected scope | Backend plus fallback membership/invitation state | Admin controls visible by UI scope toggle rather than role-only navigation |
| `/login` | Runtime-dependent login surface | Runtime settings | Canonical route |
| `/demo/*` | Separate `DemoShell` and static sample screens | Static sample data | Not environment-gated; excluded from main nav but directly reachable |

The production build currently emits 20 application routes, including seven `/demo/*` routes and all five competing workflow routes.

## 3. Current navigation structure

Desktop sidebar and mobile bottom navigation both contain:

1. Home → `/`
2. Today → `/today`
3. Cases → `/cases`
4. Reports → `/reports`
5. Settings → `/settings`

There is no canonical Session navigation item. `ShellActive` overloads `"Sessions"` to highlight Today, which obscures the difference between the work queue and an active session. The Settings page exposes a Therapist/Admin scope switch directly; ordinary therapist visibility is not derived solely from the role system.

## 4. Duplicate and competing workflows

The brief's duplication claims are confirmed.

- `/` and `/today` render the same component with only a different active-navigation value.
- `/record`, `/review-transcript`, `/results`, and `/sessions/[sessionId]` all mount `SessionWorkspaceClient` with different `view` inputs.
- `/transcript` re-exports the review page rather than performing an identifier-aware redirect.
- `/report-summary` mounts a separate 702-line report client instead of a shared Session Report view.
- The work queue repeats safety, quick actions, session summaries, and recent-result content on mobile, producing a very long first-task path.
- Existing unit tests explicitly preserve the old Home → Paste → Review → Results → Report Summary route sequence, so route consolidation requires coordinated test replacement rather than code-only redirects.

## 5. Component line-count inventory

Files above the modernization guidance are:

| File | Lines | Primary responsibilities currently combined |
|---|---:|---|
| `session-workspace-client.tsx` | 2,918 | Intake, upload, recording, transcript persistence, QA, attestation, feature extraction, findings, report generation, navigation, local fallback, and layout |
| `cases-workspace-client.tsx` | 1,181 | List, filters, detail, consent mutation, goals, timeline, care-team administration, fallback mapping, and responsive rendering |
| `settings-workspace-client.tsx` | 810 | Therapist settings, admin lifecycle, invitations, membership mutation, readiness, local mock-session preparation, and fallback data |
| `report-summary-client.tsx` | 702 | Report loading, editing, safety, generation, sign-off, exports, case/session lookup, and presentation |
| `transcript-editor-panel.tsx` | 638 | Playback visualization, filters, row editing, line actions, QA, attestation controls, export, and responsive layout |
| `browser-audio-recorder.tsx` | 401 | Media capture lifecycle, playback, timer/state, and UI |
| `reports-workspace-client.tsx` | 330 | Report fetching, filtering, selection, progress projection, library, and detail presentation |
| `work-queue-dashboard.tsx` | 319 | Queue, agenda, metrics, recent cases/uploads/results, safety, and repeated quick actions |
| `liquid-ui.tsx` | 293 | Unrelated reusable visual primitives and branded cards |

The 2,344-line `pages.test.tsx` also couples many routes and workflows into one test module, making route migration harder to reason about.

## 6. Direct API/data-call inventory

Presentational and workspace components import the shared transport/workflow layer directly:

| Component | Direct dependencies/calls | Consequence |
|---|---|---|
| `session-workspace-client.tsx` | `apiGet`, `apiBlob`, `apiRequest`, 30+ workflow service functions, experimental transcription service | UI, orchestration, persistence, routing, and transport are inseparable |
| `cases-workspace-client.tsx` | Case list/detail, timeline, goals, membership, care-team assignment, consent mutations | List/detail visuals own remote-state and mutations |
| `settings-workspace-client.tsx` | Readiness, invitation, membership list/revoke/accept | Therapist/admin visuals own lifecycle orchestration |
| `report-summary-client.tsx` | Report generate/get/update/finalize/export and case/session/transcript lookups | Independent report editor duplicates session report orchestration |
| `reports-workspace-client.tsx` | `listBackendReports` | Library owns remote fetch and status projection |
| `backend-availability-banner.tsx` | `checkBackendAvailability` | A visual banner performs capability probing |
| `use-runtime-settings.ts` | `getRuntimeSettings` | Errors collapse to `null`, losing explicit unavailable/error state |

There is no explicit frontend `BackendCapabilities` model. Runtime settings expose backend configuration, but screen behavior is driven through broad availability booleans and caught exceptions.

## 7. Backend fallback behavior

The brief's silent-fallback concern is confirmed and is the highest-risk UX issue found.

- Cases initialize state from `fallbackCases` before the backend request resolves. On request failure, the component marks the backend unavailable but retains those records.
- Case detail falls back to a matching demo case or the first demo case when the requested ID cannot be resolved. This can display an unrelated sample record for an identifier-bearing route.
- Settings initializes local memberships and invitations before backend confirmation and retains them when lifecycle loading fails.
- Today is wholly populated from local mock data and labels it as local/non-identifying fallback, but it is still the ordinary `/today` product route rather than explicit demo mode.
- Session audio/transcription catches backend failures and has explicit frontend-mock fallback branches. The UI labels experimental/local behavior, but the data mode is not modeled consistently across the full page.
- `useRuntimeSettings` maps both loading and failure to `null`, so callers cannot distinguish remote states.

The current banners reduce ambiguity but do not satisfy the required explicit `backend | sample | local draft | unavailable` model. The safer, smaller architectural alternative is to introduce one capability/data-mode adapter and migrate screens to it before visual redesign, rather than adding more page-specific booleans.

## 8. Screenshot evidence

Forty full-page screenshots were captured from the untouched app across eight representative routes and all required viewports:

```text
docs/frontend/baseline-screenshots/{today,cases,case-detail,session-intake,session-transcript,reports,settings,login}-{viewport}.png
```

Required viewports:

- `390x844`
- `768x1024`
- `1024x1366`
- `1280x800`
- `1440x900`

Representative evidence:

- `baseline-screenshots/today-390x844.png`
- `baseline-screenshots/today-1440x900.png`
- `baseline-screenshots/cases-390x844.png`
- `baseline-screenshots/session-transcript-768x1024.png`
- `baseline-screenshots/session-transcript-1440x900.png`

Automated document-width checks found no page-level horizontal overflow in any of the 40 captures. That is necessary but insufficient: the screenshots still show weak tablet composition, long mobile task paths, repeated content, and desktop space imbalance.

## 9. Responsive defects

### Mobile, 390x844

- Today is a very long feed and repeats Safety, Quick Actions, Start Recording, Today's Sessions, and recent-result concepts. The primary queue is visible, but repeated secondary content increases task time.
- The bottom navigation meets the basic structure requirement, but still includes both Home and Today.
- Cases correctly switches away from a desktop table, but fallback/error state is followed by several zero-value overview sections that add noise instead of a single recovery action.
- The session transcript is readable as a vertical flow, but it lacks the requested compact sticky audio player and sticky save/review action bar.

### Tablet portrait, 768x1024

- The sidebar collapses to icons, but Session Transcript remains a single stacked column.
- Audio, transcript, QA, and actions do not form the required primary/secondary two-pane workspace.
- The breakpoint jumps to desktop transcript columns only at `lg` (1024 px), so iPad portrait receives enlarged mobile composition rather than an intentional tablet layout.

### Tablet landscape / small desktop, 1024x1366

- Transcript rows activate a five-column grid with a minimum 22 rem utterance column at the same breakpoint where the compact sidebar is still present. This is a desktop grid threshold, not a dedicated small-desktop composition.
- Inspector behavior is embedded below or beside content rather than consistently collapsible.

### Desktop, 1280x800 and 1440x900

- Today uses only part of the available workspace while its content continues far below the fold; large blank regions appear beside narrow stacked cards.
- The right rail is useful, but repeated Safety and Quick Actions sections remain in the main column lower down.
- Transcript content is readable and has no horizontal overflow, but it lacks the persistent session context header and contextual inspector described in the target workbench.

## 10. Accessibility defects

Confirmed strengths:

- Skip link and semantic navigation labels exist.
- Global `:focus-visible` styling exists.
- Reduced-motion preferences are honored globally.
- Major async workflow status regions use `role="status"`, `role="alert"`, and `aria-live` in several paths.
- Many interactive controls use 44 px minimum heights.

Defects or unproven requirements:

- No automated WCAG/axe suite is configured.
- No current Playwright coverage verifies keyboard order, focus restoration, dialog/drawer trapping, 200% zoom, safe-area overlap, or per-control 44 px geometry.
- Admin scope is exposed as a general settings toggle rather than confirmed role-derived access.
- The transcript's less-common line actions remain visible in row content rather than an accessible overflow interaction on mobile.
- The existing lint run reports a missing `useEffect` dependency in `supabase-mfa-panel.tsx`, which can produce stale focus/data behavior, and an unoptimized `<img>` warning.
- The mobile menu button is visible in screenshots, but menu focus behavior and disclosure semantics are not covered by the current smoke suite.

## 11. Design-system inconsistencies

- Live tokens in `src/styles/globals.css` define a calm teal clinical palette, Atkinson Hyperlegible-first typography, small-to-medium radii, and shared clinical surfaces.
- `apps/lingualens-app/DESIGN.md` is named `Airtable-design-analysis`, specifies Haas typography, near-black primary buttons, coral/forest/peach signature cards, and marketing-page components. It is not an authoritative description of the rendered product.
- Legacy component names such as `GlassCard`, `GradientButton`, and `liquid-ui.tsx` remain even after CSS changes remove most glass/gradient styling.
- Tokens exist only in `globals.css`; there is no feature-facing design-system directory or explicit typography scale for transcript text, timestamps, metadata, tables, and mobile controls.
- Status colors are implemented through a mix of tokens and raw Tailwind colors.

The existing CSS normalization should be preserved. The modernization should document it as the seed of the new design system rather than discard it.

## 12. Baseline verification ledger

| Run | Command | Result | What it proves or rules out |
|---|---|---|---|
| 1 | `npm test`, `npm run typecheck`, `npm run lint`, `npm run build` | All exit 127 | Local frontend dependencies were absent; no code conclusion possible |
| 2 | `npm install` | Exit 0; 839 packages installed | Committed frontend toolchain is runnable |
| 3 | `npm test` | 24 files, 176 tests passed | Existing unit/component behavior is green, including tests for the old route flow |
| 4 | `npm run typecheck` | Exit 0 | Current TypeScript program typechecks |
| 5 | `npm run lint` | Exit 0 with 2 warnings | No lint errors; MFA dependency and image warnings remain; `next lint` is deprecated |
| 6 | `npm run build` | Exit 0 | Next.js 15.5.20 production build succeeds and exposes the duplicate/legacy/demo route set |
| 7 | `npm run e2e:smoke` in sandbox | Exit 1 before tests | Sandbox prevented localhost bind; not an app failure |
| 8 | `npm run e2e:smoke` with localhost permission | 3/3 failed | Deterministic save-transition failure: URL remains `/record?mode=paste` instead of navigating to `/review-transcript?...` |
| 9 | 40-route/viewport screenshot capture | Exit 0 | Required baseline visual evidence exists; document-width overflow is false in all captures |

### Smoke fail-path trace

Reproduction is reliable: all three smoke tests fail at the same transition. The click invokes `handleTranscriptSubmit`, which prepares and locally persists intake, then attempts backend session/transcript creation. Navigation occurs only after the backend transcript mutation succeeds. Any caught mutation failure leaves the user on `/record`, marks save failed, and suppresses navigation. The smoke logs show repeated runtime-settings traffic but no successful transcript-route transition. This is consistent with a backend mutation/auth/origin/contract issue or an unobserved UI error; the audit does not yet assign root cause.

Ranked hypotheses for the implementation/debug phase:

1. Transcript creation is rejected under the current smoke runtime/auth context, and the broad `catch` hides the actionable response.
2. The test's old route expectation is now inconsistent with intended canonical Session navigation, even though the current code still calls `/review-transcript`.
3. Runtime-settings request churn or session initialization changes the request headers before transcript mutation.
4. The save button dispatches while an intake prerequisite differs between the smoke fixture and unit mocks.

The cleanest disproof for hypothesis 1 is to capture the transcript mutation response/status and confirm whether `router.push` is reached. That instrumentation belongs to the later debugging/TDD phase, not this baseline audit.

## 13. Proposed implementation phases

The prompt's phases are sound, with one simplification: establish the shared capability/data-mode adapter and canonical session-view contract before splitting visual components. This prevents extracting monolith pieces around the wrong remote-state model.

1. **Approved design and contract** — validate canonical route/view semantics, role-aware navigation, explicit data modes, and coordinated screen concepts.
2. **Remote-state foundation** — introduce typed capabilities and `backend | sample | local draft | unavailable` adapters without visual redesign.
3. **Behavior-preserving decomposition** — split Session, Cases, Settings, Transcript, and Report orchestration behind focused hooks/services; keep safety gates intact.
4. **Route consolidation** — redirect `/` to `/today`, validate `view=intake|transcript|findings|report`, convert legacy routes to safe identifier-aware redirects, and environment-gate demos.
5. **Design-system consolidation** — promote the existing clinical tokens, document typography, remove misleading glass/liquid naming, and implement responsive shell primitives.
6. **Screen modernization** — Today, Cases, Case Detail, Session Intake, Transcript, Findings, Report, Reports Library, Settings/Admin.
7. **Remote states and safety verification** — failure, retry, stale, disabled, experimental, signed/read-only, and no-fake-success cases.
8. **Accessibility, responsive, and performance verification** — keyboard, focus, zoom, contrast, required viewports, long transcript, and rerender measurement.

Every behavior change must follow test-first red/green/refactor. Existing safety and workflow gates are constraints, not refactoring targets.

## 14. Scrutinize verdict

**Intent:** turn the current therapist frontend into a session-centered clinical workbench without changing clinical/backend contracts.

**Simpler alternative:** do not rebuild the app or replace the existing visual normalization. Preserve the current token work and backend safety logic, then migrate behavior behind one explicit capability/data-mode layer and one canonical Session route in phased slices.

**Verdict: rework before visual rollout.** The baseline is buildable and visually calmer, but route duplication, monolithic orchestration, direct data access, silent fallback behavior, ungated demos, and a failing core smoke transition make a visual-only modernization unsafe.

## 15. Post-baseline contracts phase evidence — 2026-07-13

This section appends implementation evidence; it does not alter the baseline observations above.

- Runtime settings/capabilities, explicit remote states, identity-safe cancellation, and Cases product/sample separation are implemented through commit `15fcc70` and its preceding reviewed checkpoints.
- The affected frontend contract suite passes 37 tests across 7 files; the full frontend suite passes 205 tests across 32 files.
- Backend runtime-settings and organization-admin authorization suites pass 37 tests with 3 existing deprecation warnings.
- Typecheck passes. Lint exits 0 with the same two baseline MFA/image warnings.
- A fresh production build passes and generates 21 application routes, including static `/cases` and dynamic `/cases/[caseId]`.
- Product Cases no longer silently substitutes sample records or converts unavailable timeline/goals responses into clinical empty states.
- Pre-existing `mock-data` imports in `stepper.tsx` and `work-queue-dashboard.tsx` remain a documented exception. A follow-up read-only call-site audit found `SessionStepper` unreachable, while `WorkQueueDashboard` serves both `/` and `/today` and mixes imported mock cases/workload with hard-coded sample rows without an explicit runtime-mode adapter. Production UI was not changed because that boundary overlaps the preserved Today WIP and the next approved decomposition phase; global product/sample isolation is not yet proven.
- After the permission profile changed, a real-component Playwright harness captured `/cases` and the missing-case state at `390x844`, `768x1024`, and `1440x900`. All 6 checks passed with no page errors or horizontal overflow, and the images were reviewed for mobile stacking, tablet rail behavior, desktop contextual layout, explicit unavailable state, and content coverage. The contracts/data-mode phase gate is complete; see `LINGUALENS_UX_UI_MODERNIZATION_REPORT.md` and `docs/frontend/contracts-phase-screenshots/`.

## 16. Pre-Task 6 worktree checkpoint — 2026-07-16

This checkpoint was recorded before editing backend or server-side Settings
authorization code. The repository remains on
`codex/lingualens-ux-modernization`, and all existing dirty-worktree changes are
intentional work-in-progress to preserve.

- Full tracked/untracked inventory: 121 `git status --short` entries, captured
  verbatim at `/tmp/lingualens-pre-task6-status-2026-07-16.txt`.
- Tracked worktree backup patch: 2.0 MB at
  `/tmp/lingualens-pre-task6-worktree-2026-07-16.patch`.
- Task 6 overlap inventory: only
  `apps/api/tests/test_organization_admin_routes.py` is already modified, with
  two intentional transcript-feature setup lines from existing stale-state WIP.
- `apps/api/app/core/security.py`,
  `apps/api/app/api/v1/routes/organization_admin.py`, and
  `apps/lingualens-app/src/app/settings/page.tsx` have no pre-existing diff.
- Existing frontend visual/token WIP, deployment/remediation work, ML artifact
  work, and unrelated API tests/services remain outside the Task 6 edit scope.

## 17. Pre-navigation/demo-gating worktree checkpoint — 2026-07-16

This checkpoint was recorded before the independent shell-navigation and
demo-gating phase. No production UI code was modified during this checkpoint.

- Full tracked/untracked inventory: 137 `git status --short` entries, captured
  verbatim at `/tmp/lingualens-pre-task7-status-2026-07-16.txt`.
- Tracked worktree backup patch: 2.1 MB at
  `/tmp/lingualens-pre-task7-worktree-2026-07-16.patch`.
- Existing `sidebar.tsx`, `bottom-nav.tsx`, and `mobile-header.tsx` diffs are
  intentional responsive-shell visual WIP and must be extended in place.
- The untracked `/demo` route tree and `demo-shell.tsx` are existing deployment
  and presentation WIP. Their intent and runtime exposure must be characterized
  before replacement or gating changes.
- The approved Settings authorization frontend changes and the uncommitted
  backend organization-admin guard remain separate from this phase.
- The broader SQL transactional-persistence refactor remains outside scope
  pending explicit user approval.

## 18. Cases responsive phase evidence — 2026-07-16

This phase extends the preserved Cases work in place. It does not replace the
existing care-team administration card because its placement conflicts with the
approved `/settings`-only administration architecture and requires explicit
user authorization before replacement.

- `/cases?intent=start-session` uses exact query validation and creates no
  backend session until the therapist deliberately selects a consented case.
- Successful creation routes to the backend-issued identifier at
  `/sessions/{sessionId}?view=intake`; all Cases session links use the canonical
  Session Workspace contract.
- Mobile and tablet render a semantic Cases list; desktop renders the case table
  and selected-case context rail. Clinician filtering is absent for therapists
  and present for confirmed organization admins.
- Case Detail exposes Overview, Goals, Sessions, Progress, and Reports. A
  `min-width: 0` constraint on the primary grid item contains the session
  table's intrinsic width inside its local horizontal scroller, resolving the
  reproduced 545 px document width at the 390 px viewport.
- The focused component suite passes 83 tests, TypeScript typecheck passes, and
  changed-scope ESLint reports no issues.
- Real-backend Playwright passes 10/10 checks across `390x844`, `768x1024`, and
  `1440x900`. Nine reviewed full-page screenshots live in
  `docs/frontend/cases-phase-screenshots/`.
- The final full frontend suite passes 347/347 tests, the production build
  succeeds, and Cases remains within its recorded 227 kB first-load JavaScript
  budget. The two pre-existing MFA/image build warnings are unchanged.
- Remaining architecture deviation: an ordinary therapist receives backend 403
  responses for care-team administration data, but the preserved Case Detail
  card still renders disabled assignment controls. This violates the approved
  rule that therapists must not see admin data or disabled admin controls. The
  proposed resolution is to leave a read-only care-team summary in Cases and
  move management to `/settings?section=team`; implementation is paused pending
  explicit authorization because replacing conflicting WIP was prohibited.
- Performance follow-up: the initial real-browser run emitted repeated
  `/settings` requests from multiple shell consumers. A shared, retry-safe
  single-flight cache now owns the immutable runtime bootstrap request. A
  real-browser request-count regression confirms one GET `/api/v1/settings`
  for a complete shell navigation (CORS preflight excluded).

## 19. Session context and Intake responsive phase evidence — 2026-07-16

This phase extends the preserved Session workspace in place. It introduces a
shared persisted-context header across Intake, Transcript, Findings, and Report
without changing the canonical `/sessions/{sessionId}?view=...` contract.

- The semantic `Session context` region shows Case, Session, Source, Consent,
  workflow Status, and an explicit Backend, Local draft, or Unavailable data
  mode. Missing values render `Unavailable`; clinical context is not invented.
- Intake, Transcript, Findings, and Report are canonical 44 px view links. At
  390 px all four links fit without clipping or a hidden horizontal-scroll
  dependency, and persisted context values wrap instead of relying on
  pointer-only title tooltips.
- The shared header is integrated into all four Session views. Existing
  user-facing `Session Results` language remains intact while Findings stays the
  canonical route value.
- A real-browser regression first observed two Session reads from React Strict
  Mode effect replay. Deferring identity hydration to the first retained
  microtask prevents the discarded replay from starting network work; Session,
  Case, audio-list, and ML-review reads now each occur once per page load.
- Focused Session tests pass 69/69, TypeScript passes, and changed-scope ESLint
  reports no issues. The full frontend suite passes 349/349 tests.
- Real-backend Playwright passes 5/5 at `390x844`, `768x1024`, `1024x1366`,
  `1280x800`, and `1440x900`, including no document overflow, fully visible
  view controls, 44 px targets, canonical links, persisted consent/data mode,
  and exactly one Session GET. Reviewed screenshots live in
  `docs/frontend/session-intake-phase-screenshots/`.
- The production build passes. `/sessions/[sessionId]` remains within the
  recorded 253 kB first-load JavaScript budget. The two pre-existing MFA/image
  warnings are unchanged.
- Runtime settings still produce additional development-server requests during
  this five-page evidence run even though the earlier single-page Cases
  regression observes one bootstrap GET. This appears isolated to dev-bundle
  lifecycle rather than Session identity hydration and remains a performance
  falsification target; it does not duplicate clinical workflow reads.

## 20. Transcript workbench responsive phase evidence — 2026-07-16

This phase extends the preserved transcript surface normalization in place. It
does not replace direct line editing, transcript safety gates, or the existing
save/QA/attestation/export callbacks.

- Desktop uses a 3:1 editor-inspector grid: the editable transcript owns 75% of
  workspace width, above the approved 60% floor. Audio and QA remain inside the
  workspace, are collapsible, and do not clip the editor.
- At 768–1023 px, Audio and QA switch through a segmented control and the
  inspector can be hidden entirely. Transcript fields remain full-width stacked
  controls rather than inheriting the desktop column minimum.
- On phones, audio and the compact review bar use safe-area-aware sticky
  positions; the workspace reserves matching bottom space, and the action row
  stays one 44 px horizontal strip with Save, QA, and Attest first.
- Transcript lines remain directly editable. Single-selection semantics expose
  `role=option` and `aria-selected`; the selected line retains the approved
  highlight. Split, merge, and delete moved into a per-line overflow menu while
  Play and Mark unclear remain immediate contextual actions.
- The line menu focuses its first item, closes on Escape, and restores focus to
  its trigger. Save state uses a named polite live region. A memoized ID-to-index
  map replaces repeated render-time line scans.
- Focused transcript/audio tests pass 14/14, TypeScript passes, and
  changed-scope ESLint reports no issues.
- Real-backend Playwright passes 5/5 at all exact required viewports. It verifies
  direct editing, `aria-selected`, overflow access, no document overflow,
  inspector switching/collapse, a measured editor width of at least 60%,
  inspector containment, and mobile sticky/padding behavior. Reviewed captures
  live in `docs/frontend/session-transcript-phase-screenshots/`.
- The final full frontend suite passes 352/352 tests and the optimized build
  succeeds. `/sessions/[sessionId]` is 254 kB first-load JavaScript, a 1 kB
  increase from the Intake checkpoint and still within the approved route
  budget. The two pre-existing MFA/image warnings are unchanged.

## 21. Findings, Report, Reports Library, and bundle-budget evidence — 2026-07-17

This phase modernizes the downstream therapist workflow while preserving the
explicit stale-state contract and the backend/server-owned workflow gates.

- Findings renders persisted transcript/feature/schema/AI provenance. Only
  `analysisStatus === "completed"` is current; stale findings hide derived
  values, explain why regeneration is required, and cannot unlock reports.
- Report is the sole editor. Never-generated, draft, stale, signed-checking,
  signed-verified, and signed-invalid states remain distinct. Signed snapshot
  content and metadata stay hidden until a backend-compatible SHA-256 check
  succeeds; sign, export, share, and revision paths fail closed otherwise.
- Reports is a grouped library for Needs review, Needs regeneration, and Signed
  reports. It displays no fabricated completion percentages and exposes one
  canonical Session Workspace link per row.
- The duplicate legacy desktop Findings preview and its second report action
  were removed after a failing characterization assertion reproduced the
  conflict. The final reviewed Findings capture has one `Session Results`
  hierarchy and one report-generation path.
- The real-browser run reproduced and fixed separate 390 px overflow defects
  in Report provenance and Reports Library rows. The Playwright evidence now
  self-seeds non-identifying workflow data through the real API, including QA,
  attestation, feature extraction, ML review, draft generation, and sign-off.
- Real-backend Playwright passes 3/3 at `390x844`, `768x1024`, and `1440x900`,
  with no page errors or horizontal overflow. Nine refreshed full-page images
  live in `docs/frontend/downstream-phase-screenshots/`.
- The first optimized build measured Session at 258 kB, exceeding the approved
  230 kB cap. Query-selected Session modules and mutually exclusive view
  renderers are now dynamically loaded. Final Session First Load JS is 200 kB.
- Automated bundle enforcement is committed as `bundle-budgets.json`,
  `scripts/check-bundle-budgets.mjs`, and `npm run verify:bundle`. The final run
  passes all route/shared budgets and measures the largest new async client
  chunk at 13.2 kB gzip against the 80 kB cap.
- The final full frontend suite passes 363/363 tests; typecheck, changed-scope
  lint, production build, and `git diff --check` pass. The two pre-existing MFA
  dependency/image warnings remain unchanged.
- Detailed falsification and remediation evidence is recorded in
  `docs/frontend/debug-ledgers/downstream-responsive-2026-07-17.md`.
- The all-screen five-viewport comparison and intentional-deviation record are
  still pending the final modernization verification phase.

## 22. Final Today/data-mode reconciliation — 2026-07-19

This checkpoint supersedes the historical Today and transcript exceptions
recorded above without rewriting the original baseline observations.

- The active `/today` route no longer imports `mock-data` or hard-codes agenda,
  upload, case, or report rows. An authenticated controller loads authorized
  Cases and Reports in parallel, validates array payloads, and derives one next
  action per case through a pure feature model.
- Pending, backend-confirmed, unavailable, empty, and retry states are explicit.
  Backend failure or a malformed payload renders no queue rows and cannot fall
  through to sample success. A recovery test proves retry after a 503 response.
- The focused queue contains the approved internal status groups, one prominent
  Start session action, one link per task row, and no legacy workflow links.
  Recent backend cases move to the quiet context rail.
- Today Playwright passes 7/7, including all five required viewports, 44 px
  primary action, one visible contextual surface, one action per queue row,
  no horizontal overflow, and refreshed overlay-free screenshots.
- The transcript exception is also superseded: Mark unclear now lives with
  split, merge, and delete inside the per-line overflow menu.
- The current frontend suite passes 48 files and 372 tests. Typecheck and lint
  pass (with the two unchanged MFA warnings), and the production bundle gate
  passes with Today at 213/213 kB and Session at 219/230 kB.
