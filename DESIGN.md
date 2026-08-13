# LinguaLens design language

Status: authoritative for the canonical therapist product in
`apps/lingualens-app/`.

LinguaLens is a calm, precise clinical workbench for therapist-reviewed
language-sample workflows. It borrows structural restraint from data-oriented
workflow software such as Airtable—white canvas, compact rows, clear selection,
hairline separators, and disciplined hierarchy—without copying Airtable
branding, typography, marketing layouts, or palette.

## Product character

The interface is professional, editorial, lightweight, and trustworthy. It is
structured rather than decorative. It must not resemble a generic healthcare
analytics dashboard, colorful SaaS landing page, glassmorphism product, AI
sparkle interface, or Kanban clone.

The stable information architecture is Today, Cases, Session, Reports, and
Settings. Today is the focused workbench and is not a split view. Cases and
Session may use measured master-detail or editor-inspector layouts on tablet and
desktop. `/settings` remains canonical for both therapist settings and strictly
role-gated organization administration.

## Authoritative implementation

The executable design system has one source per responsibility:

- `apps/lingualens-app/src/design-system/tokens.css` — colors, spacing, radii,
  borders, shadows, type sizes, motion, layout dimensions, and z-index;
- `apps/lingualens-app/src/design-system/typography.css` — shared type hierarchy;
- `apps/lingualens-app/src/design-system/components.css` — reusable workbench
  panels, reading surfaces, controls, sticky bars, motion helpers, and the
  restrained transcript/wave ruler motif;
- `apps/lingualens-app/src/styles/globals.css` — imports, reset, body/app defaults,
  generic interaction timing, and global accessibility behavior only.

Feature code must consume semantic tokens. It must not redefine a second palette
or token vocabulary.

## Color

- Canvas: very light cool neutral gray.
- Reading and working surfaces: true or near white.
- Primary ink: near black; secondary ink: cool dark gray.
- Separation: light neutral hairlines; stronger neutral borders only for active
  or temporary boundaries.
- Teal: primary action, focus, active navigation, selected transcript line,
  workflow progress, and necessary interactive emphasis.
- Amber: caution or needs review.
- Red: blocking, failed, or destructive state.
- Green: confirmed or completed state only.
- Blue: neutral information or links only when needed.

Teal never dominates a whole page. Coral, peach, mustard, forest, rainbow, and
decorative gradient palettes are not LinguaLens branding.

## Typography

The unified Thai-Latin product stack is:

```css
font-family: "Noto Sans Thai", "Noto Sans", system-ui, sans-serif;
```

Use moderate weights and create hierarchy through scale and spacing. Page titles
are approximately 28–32px; section titles 20–24px; panel titles 16–18px; body
14–16px; transcript text 15–16px with generous line height; metadata 12–14px;
buttons 14–16px medium. Avoid marketing-scale display typography. Atkinson
Hyperlegible is permitted only in an explicit accessibility mode or a verified
Latin-only transcript context; it is not a competing global stack.

## Geometry and surfaces

- Compact controls: 4–6px radius.
- Standard panels: 8px radius.
- Large workspace panels: 10–12px maximum.
- Status chips may use the pill token when the shape communicates compact status;
  ordinary buttons, panels, rows, and navigation do not become pills.
- Prefer borders and surface contrast. Ordinary panels have no broad shadow.
- Use elevation only for popovers, menus, drawers, modals, and other temporary
  layers.
- Avoid nested card grids, giant pills, glass panels, wide blur, and decorative
  gradients.

## Core screen contracts

### Today

Preserve the approved focused workbench: one backend-derived priority queue, one
next action per row, one prominent Start session action, status grouping inside
the queue, and a quiet contextual rail. Do not convert it to Kanban, analytics,
or case-management split view.

### Cases

Prioritize the question “Which case requires what action next?” Desktop and
tablet landscape use a compact list plus an authorized selected-case summary.
Default rows show case label, latest activity, workflow status, and one next
action. Mobile navigates from case list to a dedicated Case Detail route rather
than stacking list, analytics, progress, and activity.

### Session Transcript

Transcript lines remain directly editable. Selection is visually unmistakable
and exposed with `aria-selected`; focus is preserved when scrolling to a selected
line; secondary line actions live in an overflow menu.

- Desktop: editor remains at least 60% and normally about 65%; Audio/QA inspector
  is collapsible/resizable, does not clip, and never causes page overflow.
- iPad portrait: Transcript, Audio/QA, and context are switchable so the editor is
  never squeezed.
- Tablet landscape/1024+: use a measured approximately 65/35 split when space
  allows.
- Mobile: session context → sticky compact player → editable transcript →
  safe-area-aware sticky Save/QA controls. QA detail, report readiness, and
  technical provenance use progressive disclosure rather than permanent stacked
  panels.

### Findings

Use three disclosure levels. Level 1 shows only clinical review groups: Language
sample, Lexical use, Interaction, Speech/intelligibility, and Data quality. Level
2 reveals feature details. Level 3 contains methods, reference evidence,
provenance, limitations, and interpretation cautions. No level makes a diagnosis
or normative conclusion.

### Settings

Use category navigation and drill-down rather than an all-in-one card feed.
Therapist categories are Account, Organization, Accessibility & Display,
Notifications, Privacy & Security, Export, and Help. Authorized administrators
add Team, Invitations, Audit, Privacy Operations, and Integration Status.
Ordinary therapists do not see admin navigation, disabled admin controls, or
admin placeholders. Backend and server-boundary authorization remain mandatory.

## Motion

- Hover and selection: 80–120ms (`--motion-selection`, currently 100ms).
- Menus and popovers: 150–180ms (`--motion-popover`, currently 160ms).
- Drawers and inspectors: 180–240ms (`--motion-panel`, currently 220ms).
- Pane resize: immediate (`--motion-resize`, currently 0ms).

Use ease-out. `prefers-reduced-motion` makes motion effectively instant. Do not
decorate workflow data changes with animation.

## Accessibility

- WCAG 2.2 AA contrast and logical semantic structure.
- Visible focus; keyboard-complete transcript editing.
- `aria-selected` for selected lines.
- `aria-live` for save, job, and error results.
- Focus trap and trigger restoration for modal/drawer layers.
- Focus restoration after inspector, menu, or disclosure close where applicable.
- Essential states remain legible in forced-colors mode.
- Input errors are associated through `aria-describedby`.
- Shortcuts do not override browser defaults.
- Touch layouts preserve 44px hit areas without inflating desktop controls.
- Sticky controls reserve content space, respect safe-area insets, and do not
  overlap content at native size or 200% zoom.

## Clinical and authorization boundaries

Safety and authorization are behavior, not decoration. The persistent product
boundary may be concise—“Decision-support only · Therapist review required”—but
strong contextual warnings remain at Findings interpretation, AI-assisted
review, report generation, and export/sign-off. Reducing repeated copy must never
remove consent, stale-state, report-safety, provenance, or role gates.

Hiding controls is never authorization. Admin data reads and mutations remain
backend and server-boundary authorized. Transcript edits invalidate existing
downstream Findings and editable Report drafts server-side; stale Findings are
not current and stale Reports cannot be signed or exported.

## Anti-patterns

- Misleading component names based on retired glass, gradient, or liquid styles.
- Decorative gradients, sparkles, floating action clutter, and marketing blocks.
- 20–30px radii or rounded-everything composition.
- Repeating the same long safety paragraph in simultaneous panels.
- Exposing every Findings method/reference paragraph by default.
- Squeezing the tablet transcript beside an always-open inspector.
- Showing sample or fallback records as backend-confirmed success.
- Adding visual layout or feature rendering to the identity-scoped Session
  orchestration controller.

## Evidence contract

Pure visual work is proven through approved-concept comparison, responsive
screenshots at 390×844, 768×1024, 1024×1366, 1280×800, and 1440×900,
accessibility checks, and a fidelity ledger. Behavior changes require
characterization or failing regression tests first. Final verification includes
lint, typecheck, unit tests, production build/bundle budgets, real-contract and
explicit-demo Playwright, responsive/accessibility suites, role/route contracts,
and the 100/500/1,000-line transcript benchmark.
