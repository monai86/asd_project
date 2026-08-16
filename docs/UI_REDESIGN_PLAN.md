# LinguaLens UI Redesign Plan

Status: Phase 1 implemented 2026-08-16 (this document is the living roadmap for
the owner-approved redesign).

## Owner brief

The app currently feels like a prototype: too much backend/technical text, too
many simultaneous surfaces, hard to use, not interesting, and not obviously
usable as a public product. The owner wants: user-friendly, responsive on every
platform, minimal chrome, low learning curve, easy personal dashboard, and a
conversational (chat-like) feel with few buttons but real capability. Design
references: **Airtable** (compact data rows, hairline structure, clear
selection), **Notion** (calm neutral shell, sidebar hierarchy, quiet focus),
**ChatGPT** (single focus, minimal chrome, progressive disclosure, human tone).

## Design direction (DFII)

Direction name: **Calm clinical workbench, execution-realized**. Building on the
existing authoritative `apps/lingualens-app/DESIGN.md` (Airtable structural
restraint, clinical teal, 8px rhythm) — the gap is not the design language but
its execution:

| Dimension | Score | Note |
|---|---|---|
| Aesthetic impact | 3 | Calm-by-design; distinction comes from craft, not decoration |
| Context fit | 5 | Clinical tool: trust and clarity beat visual noise |
| Implementation feasibility | 5 | Tokens + Tailwind already exist; changes are mostly text/affordance |
| Performance safety | 5 | No new heavy dependencies, no decorative motion |
| Consistency risk | −1 | Token-driven, so changes cascade safely |
| **DFII** | **17/15 → capped 15** | Strong; execute with discipline |

What this is NOT: a generic SaaS dashboard, glassmorphism, marketing landing
pages, sparkle/AI-chat gimmicks, or a Kanban clone. Safety wording (non
-diagnostic), consent gates, human-review gates, and provenance stay intact
everywhere — the redesign never weakens clinical guarantees for visual clarity.

## The prototype-tell inventory (what makes it feel unfinished)

1. Technical/backend jargon in user-facing chrome: "Today · Backend confirmed",
   "Backend verification pending", "Backend unavailable" as page chrome.
2. Design-meta text that explains the layout ("Status grouping stays inside one
   queue; each row has one next action.").
3. Anti-hallucination developer phrasing in error/empty states ("No sample work
   or success state has been substituted.").
4. Accent drift: tokens use a muted purple-gray where DESIGN.md mandates teal
   for primary action/focus/selection.
5. Too many surfaces per screen competing for attention.

## Phases

### Phase 1 — Front door (DONE 2026-08-16)
- Today header de-jargoned: eyebrow ("Backend confirmed") removed, sub-line
  rewritten to a human action frame with the safety clause retained.
- Queue section meta line removed. Error/empty states rewritten without
  backend/anti-hallucination phrasing; retry preserved.
- Accent family realigned to clinical teal (`#0f766e` interactive fill, 4.9:1
  with white — same family-origin + darkened-fill pattern the tokens already
  documented), soft tint `#f0fdfa`, family origin `#0d9488`.
- Updated unit contracts + captured new Today screenshots.

### Phase 2 — Shell (sidebar/topbar) (DONE 2026-08-16)
- Sidebar tokenized and calmed: quiet brand wordmark, teal active state
  (accent-soft + accent-strong) per DESIGN.md, Sparkles icon removed (AI
  sparkle ban), hardcoded green/slate replaced with design tokens; the
  Clinical Safety box is kept with unchanged safety wording.
- Main canvas realigned to the page-bg token (light cool neutral gray) so
  white workspace panels gain surface separation; mobile header tokenized.
- PageHeader default eyebrow ("Clinical decision-support prototype") removed
  app-wide — the badge was the prototype tell; safety wording remains on the
  findings/report surfaces where it belongs.
- Session flows de-jargoned: "Data mode: Backend mode" is now
  "Connection: Connected / Offline draft / Offline".
- Breadcrumbs added to the session workspace (Cases → case → step) for both
  the workflow and report flows, mobile + desktop.
- Unit contracts updated (session-context-header, app-shell, pages,
  design-system); screenshot baselines regenerated; e2e 50/50 green.

### Phase 3 — Cases (Airtable-like) (DONE 2026-08-16)
- Compact row list: label, latest activity, workflow status, one next action
  (already the DESIGN.md contract; tightened density + selection affordance).
- Row selection: desktop rows are click-to-select (Airtable-style) with teal
  highlight + aria-selected; Preview button removed; mobile rows stay
  tap-to-open-detail with compact cards.
- Removed prototype-tells: "Backend-backed cases" meta badge and
  "Filter results update in place…" footer meta-text.
- Progressive disclosure: session history on the case detail shows the latest
  4 sessions with a "Show all sessions (N)" toggle; Progress rail uses a
  neutral Gauge icon instead of the AI Sparkles icon.
- Consent surface: single shared form (done in remediation), presented as a
  guided step, not a wall of fields.

### Phase 4 — Session steps (chat-like guidance) (DONE 2026-08-16)
- Intake/transcript/findings/report as one guided sequence: the four session
  views are now a quiet step rail (numbered dots + labels, complete/current/
  pending, connector lines) rendered persistently inside the session context
  header on every session page — it replaces the loud all-steps-at-once
  WorkflowStepper cards on Intake.
- Removed the backend-flavored PipelineProgressBar from Intake (kept on the
  case detail where it reads as case status); the step rail is now the single
  progress metaphor inside the guided flow.
- One primary action per screen: Intake's "Extract features" is demoted to a
  quiet secondary button (no AI Sparkles icon), so the step-continue is the
  only filled primary; transcript and findings keep their single teal primary.
- Removed the AI-sparkle icon everywhere in session views (Gauge/FileSearch/
  RefreshCw instead); the old WorkflowStepper component was deleted.
- Findings disclosure levels already collapse to the calm first level by
  default (evidence-cue vs evidence-detail toggle).

### Phase 5 — Reports + Settings (DONE 2026-08-16)
- Reports library: each group (Needs review / Needs regeneration / Signed)
  now renders with the calm Airtable-style DataTable vocabulary on desktop
  (Report / Updated / Version / Status / Action columns) and compact
  tap-friendly rows on mobile — same reports, one visible variant per
  breakpoint (DataTable gained an optional rowTestId for e2e assertions).
- Report view: export actions (Markdown / HTML / PDF later / reviewed .cha)
  grouped under a labeled "Export" subgroup, separated from the Save draft
  primary action.
- Settings: therapist-facing description and value copy quieted app-wide
  (removed prototype-y phrases like "authoritative data mode" and
  "Operational notifications remain intentionally limited in this
  prototype"); admin sections stay org-admin-only (no therapist placeholders,
  already the contract).

### Phase 6 — Cross-cutting quality (DONE 2026-08-16)
- Shared skeleton primitives (Skeleton / SkeletonLine / SkeletonPanel,
  motion-reduce aware, polite sr-only announcement) replaced bare-text
  loading states across Reports, Session workspace/view, Settings admin,
  care-team assignments, and the runtime login panel.
- Empty states carry a next action where one was missing: Today's
  "No work requires attention" now offers a Start-a-session link.
- A11y pass: added explicit visible focus rings to the 5 inputs that used a
  bare outline-none (topbar search, Supabase access gate + MFA, org
  summary, transcript editor), complementing the global focus-visible rule.
- Tests: +skeleton primitive test, +Today empty-state action assertion;
  unit 493/493, tsc + lint clean, e2e 50/50 on a fresh backend.

## Verification per phase

- Unit suites (frontend + API), typecheck, lint must stay green.
- Playwright default suite 50/50 + demo config 2/2 on fresh memory backends.
- Screenshots captured to `docs/frontend/final-remediation-screenshots/` and
  noted in `docs/frontend/visual-deviations.md`.
