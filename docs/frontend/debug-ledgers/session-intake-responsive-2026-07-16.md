# Session context and Intake responsive debugging ledger — 2026-07-16

## Intent

Add persistent, non-fabricated clinical context to the canonical Session
workspace and establish the approved responsive Intake contract without
replacing the preserved workflow orchestration.

## Experiments and breadcrumbs

1. **Characterize shared context**
   - The initial characterization failed because Session views had independent
     headings and no semantic persisted-context region or canonical view nav.
   - A shared header now owns Case, Session, Source, Consent, Status, Data mode,
     and the four validated Session view links.
   - Report's separate loader cannot currently recover consent and source, so it
     renders `Unavailable` rather than fabricating values.

2. **Preserve existing language and identity behavior**
   - Integrating the header initially broke the established `Session Results`
     assertion and duplicated the report identity label.
   - The public results title was retained, the redundant report identity strip
     was removed, and canonical routing continues to use `view=findings`.

3. **Reproduce phone overflow and view clipping**
   - The first 390 px run measured a 422 px document width. Bounds identified
     the Intake primary grid item's intrinsic minimum width as the source.
   - `min-w-0` restored containment. Visual inspection then showed the scrollable
     tab row cropping Report even though document overflow was zero.
   - A four-column phone layout now keeps every view fully visible while
     preserving a 44 px target; tablet and desktop retain the roomier flex row.

4. **Reproduce duplicate identity hydration**
   - A real-backend request counter failed with two GETs for the same Session.
   - Logs showed the duplicate cascade also reached Case, audio-list, and
     ML-review endpoints.
   - React development Strict Mode replayed the identity effect before its first
     asynchronous boundary. Deferring the request by one microtask lets replay
     cleanup cancel the discarded run before any network call begins.
   - The same request-count assertion now passes with one Session GET, and the
     related clinical-workflow reads occur once.

5. **Phase gate**
   - Focused component/integration tests: 69/69 passed.
   - Full frontend suite: 46 files, 349/349 passed.
   - Typecheck: passed.
   - Changed-scope lint: no issues.
   - Production build: passed; Session first-load JavaScript is 253 kB.
   - Real-backend responsive suite: 5/5 passed at all exact required viewports.
   - All five full-page screenshots were regenerated and reviewed.

## Remaining falsification targets

- If the Report loader gains persisted source and consent provenance, the
  shared context should display those backend values; until then,
  `Unavailable` is the safe contract.
- Development-server runtime-settings traffic remains noisier than the
  one-request Cases navigation regression and should be rechecked against a
  production server before assigning a product performance defect.
