# Settings and Intake verification ledger — 2026-07-19

## Settings overflow

| Run | Change | Result | Conclusion |
|---|---|---|---|
| Settings responsive matrix | None | Failed at 390×844, 1024×1366, and 1280×800; the care-team case selector expanded to 423 px for long benchmark identifiers | Native select intrinsic width widened the admin workspace |
| Settings responsive matrix | Constrained the case selector with `w-full min-w-0 max-w-full` and a bounded responsive label | Passed 5/5 exact viewports | The selector boundary was the fail path; therapist/admin screenshots were recaptured |

## Intake cold lazy-load timeout

| Run | Change | Result | Conclusion |
|---|---|---|---|
| Full frontend suite | None | First Intake characterization timed out before `Session Intake` appeared; later Intake tests passed | Failure occurred at the cold lazy component boundary, not workflow state |
| Isolated Intake file, three runs | None | Passed 7/7 each run | Warm/low-load imports completed inside Testing Library’s one-second default |
| Later full frontend suite | None | First Intake characterization failed again while the remaining 376 tests passed | Reproduction established a load-sensitive cold-import timeout |
| Full frontend suite | First cold-view query allowed up to five seconds; production loading unchanged | Passed 49 files / 377 tests; first Intake test required 3.085 seconds | The one-second test query was narrower than the measured cold lazy-load behavior |

No production authentication, authorization, workflow, or lazy-loading behavior was changed during the Intake investigation.

## Accessibility and demo-mode rerun

| Run | Change / environment | Result | Conclusion |
|---|---|---|---|
| Accessibility acceptance | Changed only the transcript-line fixture locator from a fuzzy accessible-name match to `exact: true` | Passed 2/2, including 200% reflow and forced-colors selected-line focus | `Transcript line 1` had also matched lines 10–19; production transcript behavior was unchanged |
| Demo smoke without `NEXT_PUBLIC_DEMO_MODE=true` | None | Safe 404 | The server-side demo gate fails closed as designed |
| Explicit demo smoke | Enabled `NEXT_PUBLIC_DEMO_MODE=true` in the isolated test server environment | Passed 2/2 after authorized copy correction | Sample data remains isolated and visibly labeled; rendered Features/Report copy is descriptive and non-normative; no production authorization guard changed |
