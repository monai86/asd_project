# Navigation and demo-gating debug ledger — 2026-07-16

## Intent

Consolidate desktop/mobile navigation around the canonical Today, Cases,
Session, Reports, and Settings routes; redirect `/` to `/today`; and make the
presentation-only `/demo` tree unavailable unless explicitly enabled.

## Breadcrumbs

| Run | Change or experiment | Result | Evidence / conclusion |
|---|---|---|---|
| 1 | Added canonical navigation and root-route assertions before production edits | 5/5 failed | Desktop/mobile still exposed Home, had no Session item, and `/` rendered the old dashboard. The intended behavior was not already present. |
| 2 | Introduced one shared navigation source, routed the brand to Today, passed an explicit active session ID, and redirected `/` | 5/5 passed | Both navigation surfaces now consume the same route set and root redirect behavior is deterministic. |
| 3 | Added strict demo flag, not-found, and sample-data-banner tests before the adapter existed | Suite failed at missing module | Demo exposure had no explicit environment boundary. |
| 4 | Added strict `NEXT_PUBLIC_DEMO_MODE === "true"` parsing and the server layout guard | 12/12 navigation/demo tests passed | Missing, false, numeric, and case-variant values fail closed; enabled mode retains an explicit sample-data notice. |
| 5 | Ran TypeScript after the route model change | 7 type errors | Old `Home`/`Sessions` test call sites and a weak environment type were the complete compile breakage set. |
| 6 | Updated affected characterization harnesses to the canonical route model | Typecheck passed; 85/85 affected tests passed | The navigation change compiles and preserves the affected shell, page, intake, and design-system behavior. |
| 7 | Ran the full frontend suite and lint | 327/331 passed; four failures expected old `Sessions` shell label; lint exited 0 with two baseline warnings | The only full-suite regression was a stale test assertion in the canonical Session page harness, not a runtime behavior failure. |
| 8 | Updated the canonical Session shell assertion and reran all frontend tests | 44 files, 331/331 tests passed | No frontend test regression remains. |
| 9 | Built the optimized Next.js app | Build and type/lint validation passed; 21 routes generated | Route sizes remained within the recorded budgets (`/today` 199 kB, `/sessions/[sessionId]` 253 kB, `/settings` 216 kB first-load JS). Only the two baseline MFA lint warnings remain. |
| 10 | Started the production build and queried canonical/disabled routes | `/` = 307 to `/today`; `/demo/dashboard` = 404; `/today` = 200 | The framework behavior matches the unit contract in a production build, not only under mocks. |
| 11 | Final verification after legacy-nav removal, canonical brand links, and unsafe-session-ID cases | 44 files, 336/336 tests; typecheck pass; lint exit 0 with two baseline warnings; build pass | Fresh evidence covers the final code, including strict Session-ID fallback and the single navigation source. Final first-load sizes: `/today` 199 kB, `/sessions/[sessionId]` 252 kB, `/settings` 216 kB. |
| 12 | Queried the freshly rebuilt production server | `/` = 307 to `/today`; `/demo/dashboard` = 404; `/today` = 200 | Final runtime HTTP behavior remains correct after the last production edits. |
| 13 | Inspected Today screenshots at all five required viewports | No overflow or page errors, but 1280/1440 primary workbench widths collapsed to 326/443 px and duplicate contextual sections appeared across breakpoints | DOM overflow checks alone were insufficient; the rendered layout contradicted the approved focused-workbench contract. |
| 14 | Added a real-backend Playwright width regression | 0/2 passed; required widths were at least 506/570 px | The desktop collapse reproduced deterministically against the contract-faithful local API environment. |
| 15 | Removed only the parent grid columns at runtime as a differential | Primary width changed from 326→638 px at 1280 and 443→755 px at 1440 | This disproved shell max-width, sidebar, and inner-card hypotheses and confirmed the hidden fallback column was reserving space. |
| 16 | Removed the empty outer `xl` column | 2/2 real-backend desktop width checks passed | The primary queue is again dominant beside the contextual rail. |
| 17 | Added five-viewport focused-action/context assertions | 2 width checks passed; 5/5 new checks failed because `Start session` did not exist | The approved primary action and duplicate-surface cleanup were not yet implemented. |
| 18 | Canonicalized the primary action and removed duplicate mobile/desktop queue/context blocks | 7/7 real-backend responsive checks passed; 73/73 affected component tests and typecheck passed | Every required viewport has one visible Start session action, one safety surface, one Quick Actions surface, no duplicate mobile agenda/results, no overflow, and a dominant desktop queue. |
| 19 | Rebuilt, recaptured, and visually inspected all five Today screenshots plus disabled demo | Build passed; all five routes returned 200 with zero page errors/overflow and one visible navigation; demo returned 404 | The corrected screenshots show full-width desktop queue rows, a quiet rail, and non-duplicated mobile/tablet content. |
| 20 | Final frontend phase verification | 44 files, 336/336 tests; typecheck pass; lint exit 0 with the two baseline warnings | The final navigation, demo boundary, and focused Today changes introduce no frontend unit/component regression. The production build and 7/7 real-backend responsive checks are recorded above. |
| 21 | Counted runtime-settings traffic during real-backend Cases navigation | Initial run emitted duplicate GETs; single-flight regression failed before implementation; final browser run observed exactly 1 GET | Root bridge, AppShell, and nested shell consumers now share one retry-safe bootstrap request instead of issuing independent `/settings` calls. |

## Hypothesis audit

- Confirmed: duplicated Home/Today navigation came from separate hard-coded
  desktop and mobile arrays.
- Confirmed: no active-session navigation existed; the ID prop was ignored by
  both previous components.
- Confirmed: the demo layout mounted unconditionally and had no environment
  decision point.
- Falsified: the root route did not contain an auth-aware redirect waiting to be
  preserved; it directly rendered the same work queue as `/today`. Redirecting
  to `/today` preserves the existing AppShell runtime/auth gate there.
