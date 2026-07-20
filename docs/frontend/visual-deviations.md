# Final visual verification and intentional deviations

Date: 2026-07-17

The implementation was reviewed against the approved focused-workbench direction,
responsive Session contract, design-system contract, and the canonical route and
authorization decisions. The concepts are directional layout references rather
than pixel-identical production comps, so comparison is based on hierarchy,
workflow emphasis, responsive behavior, interaction safety, and data provenance.

## Exact verification viewports

- 390 × 844
- 768 × 1024
- 1024 × 1366
- 1280 × 800
- 1440 × 900

## Evidence matrix

| Canonical screen | Evidence directory | State verified |
|---|---|---|
| Today | `docs/frontend/navigation-phase-screenshots/` | Refreshed backend-confirmed focused queue and quiet contextual rail at all five exact viewports |
| Cases | `docs/frontend/cases-phase-screenshots/` | Backend case list, responsive table/cards, no admin-only clinician filter for therapists |
| Case Detail | `docs/frontend/cases-phase-screenshots/` | Safe case summary and canonical Session links |
| Session Intake | `docs/frontend/session-intake-phase-screenshots/` | Backend-confirmed session context and four-step intake |
| Session Transcript | `docs/frontend/session-transcript-phase-screenshots/` | Direct editing, selected-line state, dominant editor, collapsible Audio/QA inspector |
| Session Findings | `docs/frontend/downstream-phase-screenshots/` | Backend-generated findings with provenance and decision-support boundary |
| Session Report | `docs/frontend/downstream-phase-screenshots/` | Signed immutable backend report, provenance, gated export |
| Reports | `docs/frontend/downstream-phase-screenshots/` | Backend report library grouped by workflow status |
| Therapist Settings | `docs/frontend/settings-phase-screenshots/` | Profile, organization/sample mode, credentials, accessibility/display, and fail-closed owned privacy-request status; no admin navigation, controls, or data |
| Organization-admin Settings | `docs/frontend/settings-phase-screenshots/` | Role-gated Team administration and backend readiness data inside `/settings` |
| Explicit demo Features and Report | `docs/frontend/navigation-phase-screenshots/` | Descriptive, non-normative sample copy with a persistent demo notice and explicit non-diagnostic boundary at 1280×800 |

Every matrix suite also asserts that document width does not exceed viewport
width. The real-backend downstream suite asserts the clinical gates and records
no page errors.

## Intentional deviations from the directional concepts

1. Today uses the approved focused workbench rather than a full Kanban board.
   Status grouping appears only within the prioritized queue. Cases and Session
   use split-view behavior at wider breakpoints; Today does not.
2. The Transcript inspector is collapsible and switches between Audio and QA on
   tablet. This is an approved usability refinement that keeps the editable
   transcript dominant (at least 60% on desktop) and prevents narrow iPad
   portrait editing.
3. Mobile Transcript uses sticky audio and action surfaces with safe-area-aware
   spacing. Extra bottom content padding is intentional so controls never cover
   transcript lines.
4. Transcript rows remain directly editable. Secondary row operations live in
   an overflow menu, while selected rows retain explicit visual and
   `aria-selected` state.
5. Organization administration is not a top-level visual destination. It is an
   admin-only scope inside canonical `/settings`; therapists receive the quieter
   profile/preferences screen and cannot see disabled admin affordances.
6. Backend, local-draft, unavailable, and signed/stale states add provenance and
   safety messaging beyond the visual concepts. These additions are intentional
   because the implementation contract requires the UI to distinguish real
   remote state from sample or unavailable state and to block unsafe workflow
   advancement.
7. Noto Sans Thai / Noto Sans replaces any concept typography that would mix
   Thai and Latin metrics. Atkinson Hyperlegible is reserved for a future
   explicit accessibility or Latin-only transcript context.

## Defect found during final comparison

The first admin Settings capture at 768 × 1024 exposed horizontal overflow: two
four-column administration forms activated at the tablet breakpoint despite the
persistent sidebar reducing usable width. The forms now stack in portrait and
switch to constrained columns only at the larger breakpoint. A later
requirements audit also exposed intrinsic-width overflow when the native
care-team case selector contained long benchmark identifiers. The selector is
now constrained at its component boundary. The complete therapist/admin
five-viewport matrix was recaptured and passed after both corrections.

No other unapproved visual deviations remain in the verified canonical matrix.
