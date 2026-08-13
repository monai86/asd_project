# Cases responsive debugging ledger — 2026-07-16

## Intent

Implement the approved split Cases workspace and deliberate start-session flow
without creating sessions prematurely, leaking organization-admin controls, or
introducing responsive clipping.

## Experiments and breadcrumbs

1. **Characterize legacy navigation**
   - Identifier-less entry points now converge on
     `/cases?intent=start-session`.
   - The selector keeps the primary action disabled until a consented case is
     selected and routes only after the backend returns a session identifier.

2. **Characterize role-derived controls**
   - Therapist browser state omits the clinician filter; confirmed organization
     administrators receive it.
   - Direct therapist requests to care-team and organization-membership admin
     endpoints return 403.
   - The preserved Case Detail card still renders disabled admin controls for a
     therapist. This is an unresolved UI architecture conflict, not accepted
     behavior.

3. **Reproduce mobile Case Detail overflow**
   - Playwright measured `window.innerWidth === 390` and
     `document.documentElement.scrollWidth === 545`.
   - Element bounds showed the complete primary detail column expanding to 529
     px; consent and overview cards shared that width and were symptoms.
   - The session table supplied the grid item's intrinsic minimum width even
     though the table already had an internal horizontal scroller.
   - Adding `min-w-0` to the primary grid item lets the internal table surface
     own overflow and restores a 390 px document width.

4. **Responsive and contract verification**
   - Real-backend Playwright: 10/10 passed, including the one-request runtime
     bootstrap contract.
   - Exact evidence viewports: 390x844, 768x1024, 1440x900.
   - Focused frontend tests: 83/83 passed.
   - Typecheck: passed.
   - Changed-scope lint: no issues.
   - Full frontend suite: 347/347 passed; production build passed with the two
     unchanged baseline MFA/image warnings.

5. **Runtime-settings request storm**
   - Browser logs showed each shell consumer mounting its own
     `useRuntimeSettings` request despite the confirmed-settings context.
   - A failing concurrent-hook regression reproduced duplicate bootstrap calls.
   - The hook now shares one immutable bootstrap promise, clears failed promises
     so backend recovery can retry, and retains successful settings for later
     shell consumers.
   - A real-browser request counter observes exactly one GET
     `/api/v1/settings` for `/cases`; OPTIONS preflights are intentionally not
     counted.

## Remaining falsification targets

- A therapist-visible care-team management control disproves completion of the
  approved authorization UX, even when backend requests correctly return 403.
