# LinguaLens final UI remediation audit

Date: 2026-07-22
Scope: evidence-first verification before production UI remediation
Canonical frontend: `apps/lingualens-app/`

No production UI code was edited before this audit was created. The current
dirty worktree was preserved. Fresh external backups were written to:

- `/tmp/lingualens-pre-final-ui-remediation-2026-07-22.patch`
- `/tmp/lingualens-pre-final-ui-remediation-untracked-2026-07-22.tar.gz`

The Airtable reference was inspected at
`https://getdesign.md/airtable/design-md` and in the linked upstream
`design-md/airtable/DESIGN.md` on 2026-07-22. It is an independent visual
analysis, not an Airtable-owned LinguaLens dependency. The applicable
principles are its white canvas, dark ink, moderate type weights, hairline
separation, restrained elevation, compact structured information, and precise
interaction hierarchy. Airtable branding, licensed typography, marketing
bands, signature palette, and product terminology remain out of scope.

## Issue matrix

| ID | Reported issue | Evidence inspected | Current state | Fix required? |
|---|---|---|---|---|
| A | Root `DESIGN.md` may be named authoritative but absent from source-review artifacts | `rg --files -g DESIGN.md`; all references; root and app design files; `scripts/release_scope.py`; release tests | **Confirmed** — root `DESIGN.md` is authoritative and internally consistent, but `APPROVED_FILES` does not include it. The archive includes `apps/` and therefore the implementation document, while omitting the named global authority. | Yes — add root `DESIGN.md` to the canonical release allowlist and regression tests; keep the app document implementation-specific. |
| B | Astryx may be an accidental competing design system | package manifest/lockfile; active imports; providers; global CSS; `.claude/CLAUDE.md`; README; all Astryx component consumers | **Confirmed** — Astryx supplies a global reset/theme and wrapper while LinguaLens owns tokens and primitives. Only two feature components use Astryx layout/text wrappers. Its agent rule “No div” and instruction not to override `--color-*` directly conflict with the current architecture. It does not provide unique accessibility or workflow behavior. | Yes — remove dependencies, reset/theme imports, provider wrapper, the two wrapper usages, obsolete README guidance, and conflicting `.claude` instructions. Preserve behavior using semantic HTML, Tailwind, and LinguaLens tokens. |
| C | `accent-subtle` may be amber despite a teal accent family | `tokens.css`; every semantic-token consumer; transcript filter, Case next-action surface, Intake selection, workflow stepper, status badge tests | **Confirmed** — `--color-accent-subtle: #b7791f` is amber and is used as the border for selected/current interaction states. Warning tokens already own amber semantics. | Yes — replace it with a coherent mid/subtle teal and add selected-navigation/transcript plus warning/error/success visual assertions. |
| D | Dead or misleading dashboard primitives may remain | every export and import in `workbench-ui.tsx`; `StatCard` consumers; report rendering; unsupported score search | **Confirmed** — `AppHeader`, `QuickActionCard`, `SessionCard`, `ResultMetricCard`, `SmallListRow`, and `PrimaryActionRow` are unused. `ProgressSummaryCard` is active in Report and renders hard-coded Language/Fluency/Listening/Pronunciation percentages and `+18%` without backend provenance. The remaining `WorkspacePanel`, `PrimaryActionButton`, `SafetyNote`, and `WorkflowStep` exports are active and appropriate. | Yes — delete dead exports and remove the unsupported progress summary from Report with regression coverage. Do not remove appropriate primitives. |
| E | Transcript implementation may materially diverge from approved desktop/tablet/mobile concepts | approved concept PNGs; current phase PNGs; source layout in `SessionContextHeader`, `SessionTranscriptView`, `TranscriptEditorPanel`, line list and review controls; responsive tests | **Confirmed** — direct editing, selected state, overflow actions, 65/35 desktop capability, inspector switching, safe-area padding and sticky controls exist. However the first task viewport remains displaced by a large page title, six-field context card, view tabs, status block, second transcript heading and permanently expanded filter pills. Mobile rows are form-card tall and expose system labels continuously; tablet portrait shows substantially less transcript than the approved switchable workbench concept. | Yes — compact the transcript-only context/workbench header, reduce permanent filter/system chrome, make line anatomy row-like while retaining editable controls and 44px touch targets, and preserve all safety/workflow gates. |
| F | Files named as exact viewport captures may actually be full-page screenshots | every responsive Playwright `screenshot` call; `sips` dimensions for concepts and implementation evidence | **Confirmed** — the Transcript 1440×900 file is 1440×2025; 390×844 is 390×3795; 768×1024 is 768×3313. Cases, Findings, Settings, Today, Intake and accessibility evidence also use `fullPage: true` as their only primary capture. | Yes — create paired `*-viewport-WxH.png` and `*-fullpage-WxH.png` outputs and use only viewport files for fidelity claims. |
| G | “Airtable inspired” may not be demonstrated systematically | upstream reference; root/app `DESIGN.md`; tokens/components/global CSS; current primary-screen concepts and captures; radius/shadow/gradient scans | **Partially confirmed** — the LinguaLens system already uses white reading surfaces, cool-neutral chrome, dark ink, hairlines, low radii, compact buttons, restrained teal and almost no ordinary shadows. Remaining conflicts are Astryx global theming, the incorrect accent token, excess bold/card anatomy in some active screens, and Transcript/Findings/Settings hierarchy gaps. | Yes — create the required alignment matrix and fix only the evidenced gaps without importing Airtable branding or marketing styling. |
| H | Cases may remain overly card-based or vertically unfocused | `CaseList`; current Cases concept and implementation capture; responsive tests | **Already fixed** — desktop/landscape uses a structured four-column list plus selected-case context; mobile uses list-to-detail; no analytics precede the task. Filters are contained and secondary metadata is quiet. Long current full-page evidence is largely accumulated backend test records plus the screenshot-methodology defect, not a card-grid architecture defect. | No production redesign. Preserve the architecture and prove it with paired screenshots. |
| I | Findings progressive disclosure may not be effective enough | `SessionFindingsView`; `FindingsFeatureGroups`; current concept/implementation captures; unit tests | **Partially confirmed** — the five required level-one groups and tertiary evidence disclosures exist. A four-card Summary grid and separate technical-provenance panel still precede the primary group list, delaying the clinical review task and making the first viewport more dashboard-like than the concept. | Yes — compress backend status/readiness into a structured summary strip and move tertiary provenance behind disclosure while keeping cautions, stale state and report gates. |
| J | Settings may not follow category-list → selected-page behavior on mobile | `SettingsNavigation`; role resolver; therapist/admin implementations; mobile concept/current capture; authorization and responsive tests | **Partially confirmed** — desktop rail, one-category rendering, deep links, fail-closed admin data and role gating are correct. Mobile currently opens a native select above the selected surface; it does not present the approved category list/drill-down landing. | Yes — preserve the desktop rail and authorization controller, but add a mobile category-list landing and selected-category back path without mounting admin data for therapists. |
| K | Safety messaging may be duplicated across simultaneous surfaces | all safety strings; Sidebar; Today rail; Cases meta; Transcript requirements; Findings/Report/Intake contextual warnings; current captures | **Partially confirmed** — action-blocking and context-specific warnings are justified. Generic decision-support copy repeats simultaneously in the persistent desktop Sidebar and Today context rail/Cases meta, while the sidebar wording is longer than the preferred global boundary. | Yes — make the persistent boundary concise and suppress only verified generic duplicates. Retain consent, ASR, stale-state, Findings interpretation, report sign-off and export warnings. |

## A. DESIGN.md authority evidence

Two design documents exist:

- `DESIGN.md` — global human-readable authority;
- `apps/lingualens-app/DESIGN.md` — implementation and architecture contract
  that explicitly defers to root `DESIGN.md`.

They are not contradictory. The defect is packaging: `scripts/release_scope.py`
approves the entire `apps/` tree but its root-file allowlist omits `DESIGN.md`.
The preferred authority model is therefore already selected and should be
repaired, not replaced.

## B. Astryx dependency evidence

Active Astryx surface area:

| Surface | Current dependency | Unique capability? | Classification |
|---|---|---|---|
| App providers | `Theme`, `neutralTheme`, `LinkProvider` | No active Astryx `Link` consumer and no workflow state | Redundant global wrapper |
| Global CSS | Astryx reset, core CSS, neutral theme | Duplicates/reset-overrides the LinguaLens semantic design system | Competing authority |
| Cases detail | `Stack`, `Text` | Semantic HTML and existing utilities provide the same layout/type behavior | Replaceable wrapper |
| Pipeline progress | `Stack`, `Center`, `Text` | Existing flex/grid and semantic elements provide the same behavior | Replaceable wrapper |
| Agent guidance | `.claude/CLAUDE.md` | Conflicts with repository conventions and root `DESIGN.md` | Remove |

Decision for implementation: **remove Astryx**. LinguaLens semantic CSS,
Tailwind, Lucide, and focused application primitives remain the frontend
foundation.

## C. Semantic token table

| Token | Current value | Intended semantic | Actual usage | State |
|---|---:|---|---|---|
| `accent` | `#08747d` | Primary action and interaction teal | CTA, active indicators, waveform | Correct |
| `accent-strong` | `#074f56` | Dark teal text/hover/selected emphasis | Active text, CTA hover, selected controls | Correct |
| `accent-soft` | `#e2f2f3` | Pale selected/active teal surface | Selected rows, tabs, navigation | Correct |
| `accent-subtle` | `#b7791f` | Mid/subtle accent teal | Selected/current borders; Case next-action border | Incorrect: amber value in accent role |
| `warning-*` | amber family | Caution, review required, stale/blocking precondition | Review badges, warnings, stale state | Correct family |
| `danger-*` | red family | Error, failed, destructive/blocking | Errors and danger actions | Correct family |
| `success-*` | green family | Completed/current confirmation | Attested, ready, successful save | Correct family |
| `info-*` | indigo/blue family | Neutral informational/processing state | Processing and informational badges | Correct family |

The remediation must not turn warnings teal. It must correct only the accent
family and retain explicit text/icon cues so state is not conveyed by color
alone.

## D. Dead component classification

| Export | Classification | Evidence |
|---|---|---|
| `AppHeader` | Unused/dead | Definition only |
| `QuickActionCard` | Unused/dead | Definition only |
| `SessionCard` | Unused/dead | Definition only |
| `ResultMetricCard` | Unused/dead | Definition only |
| `SmallListRow` | Unused/dead | Definition only |
| `PrimaryActionRow` | Unused/dead and legacy | Definition only; links to legacy `/record` |
| `ProgressSummaryCard` | Active but clinically unsupported | Imported by Report; hard-coded percentages and trend |
| `WorkspacePanel` | Active and appropriate | Shared border/surface primitive |
| `PrimaryActionButton` | Active and appropriate | Shared dominant action primitive |
| `SafetyNote` | Active and appropriate when context-specific | Intake/Report/Reports boundaries |
| `WorkflowStep` | Active and appropriate | Intake workflow presentation |

## E. Preliminary Transcript fidelity ledger

The current implementation evidence is full-page, so it cannot prove exact
viewport fidelity. It is still sufficient to confirm hierarchy and length
defects; paired fresh captures are required after remediation.

| Viewport | Concept | Current implementation evidence | Difference | Severity | Fix |
|---:|---|---|---|---|---|
| 390×844 | Context → compact player → editable rows → sticky Save/QA | Named file is 390×3795; six context fields, tabs, status, headings and filters precede tall form-card rows | Core edit/listen workflow is displaced and system state is overexposed | High | Compact transcript context; compact filter; row-like edit anatomy; keep sticky/safe-area contract |
| 768×1024 | Full-width editor plus switchable Audio/QA/context | Named file is 768×3313; switch controls exist but only a small part of the editor fits near the task start | Switching is correct; density/hierarchy is not | High | Transcript-only compact header and denser rows |
| 1024×1366 | Approx. 65/35 where width allows | Split breakpoint exists at `lg`; inspector can hide; named evidence is 1024×3085 | Structural contract exists but exact first viewport is unproven | Medium | Preserve split; capture exact viewport and check clipping/focus |
| 1280×800 | Dominant editor with contextual inspector | Editor ratio assertion is ≥60%; named evidence is 1280×3044 | Excess pre-editor vertical chrome and permanent filter row | High | Compact workbench header; pair captures |
| 1440×900 | Compact context/tabs then 65/35 workbench with transcript rows immediately visible | Named evidence is 1440×2025; screenshot shows title, context card, status, duplicate headings and filters before row content | Material concept mismatch | High | Consolidate hierarchy and re-capture exact viewport |

## F. Airtable-inspired alignment snapshot

| Principle | State | Evidence |
|---|---|---|
| Canvas | Aligned | Cool-neutral page chrome with white/near-white working surfaces |
| Typography | Partially aligned | Noto stack and compact scale are correct; several active headings/statuses still overuse bold weight |
| Borders | Aligned | Neutral one-pixel hairlines carry most workspace separation |
| Geometry | Partially aligned | Token system is 6/8/10px; two active/legacy 20px+ literals remain and dead primitives include one of them |
| Density | Partially aligned | Cases is structured; Transcript and Findings still delay the primary task with stacked chrome/cards |
| Actions | Aligned | Teal primary actions are dominant and secondary actions are bordered/quiet |
| Navigation | Aligned | Five stable destinations and precise selected state; no Kanban/marketing navigation |
| Tables/lists | Aligned | Cases and transcript line list use structured row semantics |
| Inspectors | Partially aligned | Transcript inspector is contextual and collapsible; first-viewport composition remains too tall |
| Elevation | Aligned | Ordinary panels are border-led; shadow is limited to temporary overflow UI |

## G. Architectural invariants to protect

The remediation may not change:

- `/today` as canonical landing and focused-workbench model;
- validated Session Workspace views and legacy route compatibility;
- backend capability and explicit remote-state handling;
- server-side stale Findings/Report invalidation and stale-response guards;
- therapist/admin authorization and fail-closed admin lifecycle state;
- transcript attestation/eligibility, immutable signed reports, sign-off and
  export gates;
- the Noto Sans Thai / Noto Sans product stack and non-diagnostic boundary.

## Audit conclusion

Implementation is authorized only for the **Confirmed** and **Partially
confirmed** rows above. Cases architecture and already-correct authorization,
workflow and safety behavior must be preserved. Final completion remains
unproven at the baseline stage until paired screenshots, side-by-side visual
review, regression evidence, the full required test matrix, and synchronized
documentation exist.

## Post-remediation evidence — 2026-07-23

| ID | Final state | Remediation evidence |
|---|---|---|
| A | Corrected | Root `DESIGN.md` is the human-readable authority, the app document defers to it, and `scripts/release_scope.py` plus its regression test include the root file. |
| B | Corrected | Astryx dependencies, CSS, Theme/Link providers, wrapper consumers, configuration and conflicting agent instructions are absent. LinguaLens semantic CSS + Tailwind remain. |
| C | Corrected | `accent-subtle` is coherent teal `#4f9fa5`; amber remains in the warning family. Selected, warning, error and success contract tests pass. |
| D | Corrected | Six dead primitives and the unsupported hard-coded Report progress percentages were removed. Active focused primitives remain. |
| E | Corrected | Transcript now has compact context, a directly editable utterance in the first mobile viewport, a dominant editor, collapsible/switchable inspector, compact filter, selected-row state and overflow actions. Fixed safe-area Save/QA and canonical navigation layers do not overlap, and the final row scrolls clear. Browser-native off-screen layout containment keeps 500/1,000-line editing within budget without removing rows from the DOM. |
| F | Corrected | `docs/frontend/final-remediation-screenshots/` contains 50 exact viewport captures and 50 paired full-page captures; all viewport dimensions were checked with `sips`. |
| G | Corrected | `AIRTABLE_DESIGN_ALIGNMENT.md` records the principle and screen matrices, source boundary, fidelity ledger and intentional deviations. A final visual hard-gate regression converted Today from card-per-item anatomy to one hairline-divided queue; exact-viewport assertions require at least three rows at 1280×800 and four at 1440×900. |
| H | Preserved | Cases remains structured master/detail on desktop/tablet and list-to-detail on mobile; the verified architecture was not replaced. |
| I | Corrected | Findings begins with the five clinical review groups; status is a compact workflow strip and provenance follows as tertiary disclosure. |
| J | Corrected | Settings uses desktop rail and mobile category-list drill-down; therapist/admin route and data boundaries remain fail-closed. |
| K | Corrected | Only redundant generic safety copy was removed; global, contextual and action-blocking clinical boundaries remain. |

Fresh proof includes 395/395 frontend tests, 177/177 focused backend contract
tests, 778 repository-gate Python tests, build and bundle budgets, real smoke
3/3, explicit demo 2/2, accessibility 2/2, responsive 36/36, the passing
100/500/1,000-line production benchmark, paired visual review and synchronized
design/status reports. Remaining dependency, staging, production and clinical
validation limits are recorded as launch constraints rather than hidden.

**FINAL UI REMEDIATION: COMPLETE**
