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
