# LinguaLens product design contract

This document defines the current UI contract for the canonical therapist product in `apps/lingualens-app`. Root `DESIGN.md` is the human-readable product authority. The executable source is split by responsibility under `src/design-system/`: `tokens.css` owns every semantic token, `typography.css` owns the shared type hierarchy, and `components.css` owns reusable workbench primitives. `src/styles/globals.css` imports those files and is limited to reset, body/app defaults, generic transition binding, and global accessibility rules. Historical concepts and screenshots are evidence, not competing design systems.

## Product character

LinguaLens is a calm clinical workbench for therapist-reviewed language-sample workflows. It must feel precise, quiet, readable, and trustworthy without implying automated diagnosis or Thai clinical validation. Use clear hierarchy, restrained surfaces, explicit workflow state, and one obvious next action.

## Typography

The unified Thai–Latin product stack is:

```css
font-family: "Noto Sans Thai", "Noto Sans", system-ui, sans-serif;
```

This stack is mandatory for the product shell, controls, forms, tables, reports, and mixed-script transcript content. Do not introduce Inter, Haas, or Atkinson Hyperlegible as a competing global stack. Atkinson Hyperlegible may be offered only through a deliberate accessibility preference or in a Latin-only transcript context where mixed-script metric changes cannot occur.

## Layout contracts

- Today uses a focused workbench: one prioritized queue, one next action per row, one prominent Start session action, and a quiet contextual rail. Status grouping belongs inside the queue, not in a full Kanban board.
- Cases and Session Workspace may use split views on tablet and desktop. Today must not.
- Session Workspace uses validated `?view=intake|transcript|findings|report`; missing or invalid values resolve to `intake`.
- `/settings` is canonical. Organization administration exists only in role-gated sections within Settings.
- Desktop transcript editing remains dominant at 60% width or more. The QA inspector is collapsible or resizable and may not clip.
- On iPad portrait, Audio/QA can collapse or switch views so the transcript remains usable.
- On mobile, sticky media and action regions honor safe-area insets and reserve content space.

## Surfaces and controls

Use the semantic color, radius, spacing, and surface tokens in `src/design-system/tokens.css`; do not redefine them in feature styles. Prefer true-white reading surfaces, neutral hairlines, 4–6px control radii, 8px panels, and 10–12px maximum workspace radii. Ordinary panels do not use shadows. Controls may be visually compact on desktop, but touch devices require a 44px interactive hit area. Transcript lines remain directly editable; selected lines are unmistakable and use `aria-selected`. Secondary line actions belong in an overflow menu.

## Motion

Use the timing tokens in `src/design-system/tokens.css`:

- selection and hover: `--motion-selection` (100ms; acceptable range 80–120ms)
- popovers and menus: `--motion-popover` (160ms; acceptable range 150–180ms)
- drawers and panels: `--motion-panel` (220ms; acceptable range 180–240ms)
- pane resizing: `--motion-resize` (immediate)

Respect `prefers-reduced-motion`. Never animate pane resizing in a way that delays direct manipulation.

## Accessibility acceptance

- Transcript selection exposes `aria-selected`.
- Save, job, and error results use an appropriate `aria-live` region.
- Modal and drawer focus is trapped and restored to the trigger on close.
- Essential states remain legible in `forced-colors` mode.
- Input errors are linked to their fields with `aria-describedby`.
- Keyboard shortcuts do not override browser defaults and are documented where exposed.
- Scrolling to a selected transcript line preserves keyboard focus.
- Focus indicators remain visible and touch targets remain at least 44px on touch devices.

## Authorization and safety

Hiding controls is never an authorization boundary. Admin routes, data reads, and mutations must be backend- and server-boundary authorized. Therapists receive only the minimum read-only care-team summary already present on an authorized case record. Role, invitation, privacy, care-team, and organization-management mutations retain backend audit logging.

## Session architecture

The canonical Session boundary is deliberately layered:

- `session-workspace.tsx` resolves the canonical view and isolates Report as its own lazy feature.
- `useSessionWorkspace` in `session-workspace-model.tsx` is the identity-scoped controller. It owns request sequencing, cancellation guards, persistence, and workflow mutations.
- `session-workspace-view.tsx` is the typed presentational dispatcher and lazy-loads Intake, Transcript, and Findings independently.
- Intake mutations enter through the Session controller; Intake steps and source/result presentation are split from the route-level view.
- Report transport lives behind `session-report-service.ts`, identity-scoped orchestration lives in `use-session-report.ts`, and the Report view remains presentational.
- Findings derivations and small provenance/status components live in `session-findings-support.tsx` so the Findings screen stays within the complex-container budget.
- The transcript editor separates controller state, the directly editable memoized line list, and pure/support calculations into `transcript-editor-panel.tsx`, `transcript-line-list.tsx`, and `transcript-editor-support.tsx`.
- Each feature view owns only its cohesive screen layout and interaction presentation; reusable transport operations live behind services and workflow adapters.

The controller is intentionally kept as one identity-scoped orchestration boundary so a late request or mutation cannot settle into a different Session. It must not absorb feature layout. New transport behavior should first be added to the service/adapter boundary, and new view behavior belongs in the relevant feature view.

## Settings architecture

`/settings` remains the single route. Desktop uses a category rail and mobile uses category selection/drill-down. Shared categories are Account, Organization, Accessibility & Display, Notifications, Privacy & Security, Export, and Help. Team, Invitations, Audit, Privacy Operations, and Integration Status are organization-admin only. `settings-workspace.tsx` owns the role-gated section switch and organization-admin lifecycle controller; navigation, therapist presentation, backend-authorized care-team administration, and reusable status/lifecycle presentation are split into dedicated components. Moving those components does not weaken the server route or backend authorization boundary: ordinary therapists never mount admin controllers, receive admin navigation, or fetch admin lifecycle data. Failed or malformed admin responses clear lifecycle state and never substitute sample records.

Complex feature containers are limited to 500 lines by an architecture test. The identity-scoped Session controller is the documented exception because splitting its request identity and stale-settlement coordination would weaken the race-safety boundary; it contains no feature layout.

## Today architecture

The canonical Today route is a backend-driven feature boundary:

- `WorkQueueDashboard` is a thin authenticated-shell entry point; its data controller mounts only after the shell access gate allows workspace content.
- `useTodayWorkbench` owns request identity, cancellation, retry, and remote-state translation.
- `today-workbench-adapter.ts` loads authorized Cases and Reports in parallel and rejects malformed non-array payloads rather than rendering an inferred success state.
- `today-workbench-model.ts` deterministically derives one operational next action per case and groups those items inside the queue.
- `TodayWorkbenchView` and `TodayContextRail` are presentational and do not call APIs.

Today never imports product rows from `mock-data`. Sample records remain isolated to explicitly flagged `/demo/*` surfaces.

## Verification

Visual changes require approved-concept comparison, responsive screenshots at the required viewports, accessibility checks, and recorded intentional deviations. Behavior changes require characterization or failing regression tests first. Frontend contract types must remain aligned with backend schemas.
