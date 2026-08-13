# LinguaLens Airtable-inspired design alignment

Date: 2026-07-23
Canonical design authority: [`DESIGN.md`](../../DESIGN.md)
Implementation contract: [`apps/lingualens-app/DESIGN.md`](../../apps/lingualens-app/DESIGN.md)

## Scope and reference boundary

LinguaLens uses the structural and interaction discipline documented in the
independent Airtable design analysis at
`https://getdesign.md/airtable/design-md` as visual inspiration. Airtable does
not own, sponsor, or provide the LinguaLens product, and no Airtable logo,
proprietary asset, typography, terminology, or marketing layout is used.

The intended result is a therapist workbench with data-product precision:
true-white working surfaces, dark ink, restrained neutral chrome, hairline
separation, compact rows, quiet navigation, contextual actions, and
editor/inspector layouts where the task requires them. LinguaLens teal,
clinical workflow language, consent and authorization boundaries, and the
non-diagnostic product boundary remain authoritative.

## Evidence inspected

- root and app design contracts;
- semantic tokens and active workbench primitives;
- approved concepts in `docs/frontend/final-polish-concepts/`;
- exact-viewport and full-page implementation evidence in
  `docs/frontend/final-remediation-screenshots/`;
- rendered Today, Cases, Transcript, Findings, and Settings screens at
  390×844, 768×1024, 1024×1366, 1280×800, and 1440×900;
- responsive Playwright assertions for horizontal overflow, split-view width,
  inspector switching, role-safe Settings navigation, and 44px controls.

## Principle alignment matrix

| Principle | State | Current implementation evidence | Remaining or intentional deviation |
|---|---|---|---|
| Canvas | **Aligned** | `--color-page-bg: #f7fafa`; working/reading surfaces are true or near white | Cool-neutral application chrome is retained to distinguish workspace boundaries. |
| Typography | **Aligned** | Unified `Noto Sans Thai` / `Noto Sans` stack; 28–32px page titles, compact labels, moderate body hierarchy | Atkinson Hyperlegible remains reserved for an optional accessibility mode rather than mixed-script product UI. |
| Borders | **Aligned** | Neutral 1px hairlines carry panel, row, table, and selected-state structure | Stronger borders remain for focus, selected rows, warnings, and temporary overlays. |
| Geometry | **Aligned** | 6px controls, 8px panels, 10px shell maximum in active workbench surfaces | Pills remain for short statuses where their compact anatomy communicates state. |
| Density | **Aligned** | Today uses one compact hairline-divided queue with three rows intersecting 1280×800 and four at 1440×900; Cases is row/table-led; Transcript exposes editable rows in the first viewport; Findings begins with five structured groups | Touch layouts retain 44px targets and editable timestamp/speaker controls, so mobile transcript rows are taller than the static concept. |
| Actions | **Aligned** | One dominant teal action per Today row; secondary actions use neutral borders; transcript line actions live in overflow | Safety-gated actions remain visible when their disabled/blocked reason is clinically important. |
| Navigation | **Aligned** | Quiet five-destination shell; precise teal selected marker; canonical `/settings` and Session query views | Mobile shell retains organization context above the work surface for tenant clarity. |
| Tables and lists | **Aligned** | Cases uses a four-column structured desktop table; Today groups status inside a single hairline-divided queue rather than cards; transcript is a directly editable row list | Cases uses cards below the table breakpoint because stacked fields and a 44px action are safer on narrow touch screens. |
| Inspectors | **Aligned** | Transcript editor is approximately 65% and Audio/QA approximately 35% on desktop; inspector collapses and switches on tablet | At 768px the inspector becomes a switchable view rather than a permanently narrow side pane. |
| Elevation | **Aligned** | Ordinary surfaces are border-led; shadow is limited to the line overflow menu and elevated temporary UI | The transcript/wave ruler uses small linear-gradient marks as a restrained LinguaLens motif, not a decorative page gradient. |
| Color semantics | **Aligned** | Accent family is coherent teal; amber is warning/review; red is error/destructive; green is confirmed; blue/indigo is information | Color never carries state alone; labels, icons, and status text remain present. |
| Motion | **Aligned** | Selection 100ms, popover 160ms, panel 220ms, resize 0ms; reduced-motion rules remain global | Pane resizing stays immediate by contract. |

## Primary-screen alignment

| Screen | Alignment | Evidence and outcome |
|---|---|---|
| Today | **Aligned** | One prioritized queue remains dominant; status grouping is internal to the queue; every hairline-divided row has one next action; Start session is the prominent page action; the context rail is quiet. Desktop exact-viewport assertions require at least three visible rows at 1280×800 and four at 1440×900; mobile keeps the queue and first row in the first viewport. |
| Cases | **Aligned** | Desktop uses structured list plus selected-case context; 1024px uses list plus contextual detail; mobile stays list-first. Filters precede the task but were compressed into a two-column control row on narrow screens. |
| Transcript | **Aligned with recorded deviations** | Compact session context, canonical tabs, directly editable rows, selected-line highlight, overflow actions, 65/35 desktop inspector, tablet switching, sticky mobile audio, compact filter, and fixed safe-area Save/QA plus canonical navigation layers are present. Product/tenant context and touch-sized edit controls make the actual mobile list less dense than the static concept. |
| Findings | **Aligned** | The five clinical review groups appear first as compact structured rows. Workflow summary follows as a hairline-separated strip; technical provenance and evidence remain tertiary disclosure. No unsupported clinical score grid is shown. |
| Settings | **Aligned** | Desktop uses category rail plus selected surface. Canonical `/settings` opens a category list on mobile, then drills into one category with a back action. Admin groups never appear for therapists and remain backend/server-authorized. |

## Transcript fidelity ledger

| Viewport | Approved intent | Final implementation | Difference | Severity | Resolution |
|---:|---|---|---|---|---|
| 390×844 | Compact context → sticky player → editable rows → sticky Save/QA | Tenant header and compact session disclosure precede sticky audio, one filter, and a directly editable first utterance above fixed Save/QA and navigation layers | Fewer simultaneous lines than the static concept because timestamp, speaker, and utterance controls keep 44px touch targets | Low, intentional | Preserve the real editable anatomy and safety context; geometry tests prove both fixed layers and the final row remain unobscured. |
| 768×1024 | Full-width transcript with switchable Audio/QA | Full-width editable list shows three line rows in the viewport; Audio/QA switches without narrowing the transcript | Persistent shell occupies more space than the isolated concept | Low, intentional | Preserve authenticated product navigation and switch-view behavior. |
| 1024×1366 | Split workbench where width allows | Transcript and QA inspector are shown side by side without horizontal overflow; inspector can hide and restore | Editor is less table-dense than desktop because this remains a touch-capable width | Low, intentional | Keep switch/collapse controls and readable inputs. |
| 1280×800 | Editor dominant at ≥60%, contextual inspector | Editable rows begin in the first viewport and editor width passes the ≥60% assertion; audio inspector does not clip | Session provenance is more explicit than the static concept | Low, intentional | Keep provenance because backend version/state is safety-relevant. |
| 1440×900 | Compact context/tabs followed immediately by 65/35 workbench | Three directly editable rows plus inspector are visible; line selection, QA/confidence, and overflow actions are explicit | Rows are taller than static mock rows because every field is live and keyboard/touch accessible | Low, intentional | Accepted responsive contract; no read-only summary substitution. |

## Screenshot methodology

Each primary screen has two separately named captures at every required
viewport:

```text
<screen>-viewport-<width>x<height>.png
<screen>-fullpage-<width>x<height>.png
```

Viewport captures are the authority for concept fidelity. Full-page captures
are used only for overflow, workflow length, and disclosure completeness. The
capture helper clears focus, disables smooth scrolling, resets both document
scroll roots, and waits until `window.scrollY === 0` before creating the
viewport image. The
primary set contains 25 exact-viewport files and 25 matching full-page files
for Today, Cases, Transcript, Findings, and Settings. Additional paired files
cover case selection/detail, report workspace/library, and admin Settings.

## Intentional deviations from the approved concepts

1. The authenticated product shell shows active organization and user context;
   isolated concepts omit some of this chrome.
2. Mobile transcript rows keep directly editable timestamp, speaker, and
   utterance fields with 44px targets, so fewer rows fit than in a static mock.
3. Session provenance and workflow state remain discoverable because backend
   identity, consent, stale state, and source version are safety-relevant.
4. Findings says “Session Results” in the canonical Session Workspace rather
   than creating a separate top-level Findings product route.
5. Settings admin sections are absent—not disabled—for therapists; admin
   concepts are verified separately under an authorized role.

No remaining deviation changes the approved information architecture, makes a
clinical claim, weakens authorization, or substitutes a mock-only success
state.
