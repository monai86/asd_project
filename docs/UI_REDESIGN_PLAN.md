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

### Phase 2 — Shell (sidebar/topbar)
- Notion-like calm sidebar: tighter hierarchy, clear active state in teal,
  quieter secondary text; mobile header reduced to brand + context, no
  technical labels.
- Consistent page-header rhythm (one title, one primary action, one sub-line)
  across Today/Cases/Session/Reports/Settings via the existing `page-header`
  component.
- Breadcrumbs on 3+ level deep session flows (mobile + desktop).

### Phase 3 — Cases (Airtable-like)
- Compact row list: label, latest activity, workflow status, one next action
  (already the DESIGN.md contract; tighten density + selection affordance).
- Selected-case summary panel: reduce stacked sections, progressive disclosure
  for history/activity.
- Consent surface: single shared form (done in remediation), presented as a
  guided step, not a wall of fields.

### Phase 4 — Session steps (chat-like guidance)
- Intake/transcript/findings/report as one guided sequence: one question at a
  time where possible (progressive disclosure), a persistent but quiet step
  rail, and one primary action per screen.
- Findings: keep the three disclosure levels (clinical groups → feature detail
  → methods/provenance) but render the first level as the default calm view.
- Error/loading states humanized app-wide (shared copy patterns).

### Phase 5 — Reports + Settings
- Reports: list + preview with the calm table vocabulary; export actions
  clearly grouped.
- Settings: category drill-down (already the contract), remove admin
  placeholders for therapists (already done), quieter description text.

### Phase 6 — Cross-cutting quality
- Empty/loading/error states everywhere (skeletons, not spinners).
- Accessibility pass per impeccable product register (contrast, focus,
  keyboard, reduced motion, 44px touch).
- e2e selector/label updates + fresh screenshot baselines for every touched
  surface; visual-deviations ledger updated.

## Verification per phase

- Unit suites (frontend + API), typecheck, lint must stay green.
- Playwright default suite 50/50 + demo config 2/2 on fresh memory backends.
- Screenshots captured to `docs/frontend/final-remediation-screenshots/` and
  noted in `docs/frontend/visual-deviations.md`.
