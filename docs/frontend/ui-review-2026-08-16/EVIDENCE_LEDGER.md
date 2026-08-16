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
