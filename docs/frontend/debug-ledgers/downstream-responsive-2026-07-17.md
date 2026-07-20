# Downstream workspaces responsive and integrity ledger — 2026-07-17

## Scope

Findings, Report, and Reports Library were modernized without changing the
canonical `/sessions/{sessionId}?view=findings|report` contract or weakening
transcript, stale-state, sign-off, export, provenance, or tenant gates.

## Evidence ledger

| Check | Observation | Resolution / evidence |
|---|---|---|
| Existing Findings hierarchy | The desktop capture exposed two `Session Results` regions and a legacy `SessionResultsPreview` with percentage-oriented summaries and a second report-generation path. | Added a failing characterization assertion, removed only the duplicate preview, and updated old route tests to the approved provenance/readiness contract. |
| Findings currentness | Non-completed analysis states could not be allowed to leak prior feature or ML values. | Only `analysisStatus === "completed"` renders current findings; stale and other non-current states sanitize derived values and gate reporting. |
| Report integrity | A persisted signed snapshot must not be trusted before its backend-compatible SHA-256 hash is verified. | Signed content and metadata stay hidden while checking and fail closed on mismatch. Sign/export/share/revision actions are blocked until verification succeeds. |
| Signed revision | Mutable signed metadata or a double-click could create an unsafe revision path. | Revision uses the verified immutable snapshot, strips the prior sign-off/export block, synchronously guards duplicate submission, and updates the canonical `report_id`. |
| Mobile Report overflow | The 390 px real-browser run measured a 640 px document. | Added `min-width: 0` containment and wrapping for report provenance values. |
| Mobile Reports overflow | The 390 px real-browser run measured a 439 px document. | Added `min-width: 0` containment to library groups/rows and breakable identifiers/details. |
| Reproducibility | Fixed in-memory identifiers disappeared whenever the API restarted. | The Playwright spec now seeds a non-identifying case, session, transcript, QA, attestation, features, ML review, draft, and signed report through the real API before assertions. |
| Browser harness | A manual backend was reused with CORS for the wrong frontend origin, producing the fail-closed runtime-verification screen. | Removed the conflicting process and used Playwright's configured port 3100 frontend plus contract-faithful memory API with matching CORS. |
| Session bundle | The first downstream build measured 258 kB First Load JS against the approved 230 kB cap. | Query-selected Session workflow/report modules and mutually exclusive view renderers are dynamically loaded. Final Session First Load JS is 200 kB. |
| Lazy chunks | A first parser version incorrectly applied the 80 kB lazy-chunk cap to a 167.2 kB global layout entry chunk. | The verifier now applies route/shared budgets to entry chunks and the lazy-chunk cap only to Webpack async client chunks. Largest new lazy chunk is 13.2 kB gzip. |

## Final verification

- Full frontend: 47 files, 363 tests passed.
- TypeScript: `npm run typecheck` passed.
- Changed-scope lint: passed with no warnings or errors.
- Bundle enforcement: `npm run verify:bundle` passed.
- Bundle measurements: shared 102/112 kB; Today 199/213 kB; Cases
  227/242 kB; Reports 212/229 kB; Settings 216/232 kB; Session 200/230
  kB; largest async client chunk 13.2/80 kB gzip.
- Production build: passed. The two pre-existing `supabase-mfa-panel.tsx`
  warnings remain unchanged.
- Real-backend Playwright: 3/3 passed at `390x844`, `768x1024`, and
  `1440x900`, with no page errors or horizontal document overflow.
- Nine refreshed screenshots:
  `docs/frontend/downstream-phase-screenshots/`.
- `git diff --check`: passed.

The all-screen five-viewport modernization comparison and intentional-deviation
record remain a later final-phase deliverable; this ledger closes only the
downstream workspace slice.
