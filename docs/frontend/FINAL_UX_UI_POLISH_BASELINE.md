# LinguaLens final UX/UI polish baseline

Date: 2026-07-21
Branch: `codex/lingualens-ux-modernization`
Frozen commit: `e37979d0e9ed4a345e85d5e51cfb2e7fb4c86114`
Canonical frontend: `apps/lingualens-app/`
Canonical API: `apps/api/`

## Audit boundary and freeze

This baseline was completed before modifying production UI code for the final
polish pass. The existing dirty worktree is intentional work-in-progress and is
outside the frontend-polish ownership boundary unless a file is explicitly
called out below. Nothing was reset, reverted, discarded, checked out over, or
silently replaced.

The tracked worktree and the only untracked frontend directory were backed up
outside the repository before this audit:

```text
/tmp/lingualens-pre-final-polish-worktree-2026-07-21.patch
/tmp/lingualens-pre-final-polish-untracked-frontend-2026-07-21.tar.gz
```

The patch was created with `git diff --binary HEAD`. The archive contains
`apps/lingualens-app/.claude/`, which is not production application source.

## Changed-file inventory at freeze

There were no tracked production-frontend changes relative to `HEAD`. The only
untracked item under `apps/lingualens-app/` was:

- `apps/lingualens-app/.claude/`

The following pre-existing changes are unrelated backend, ML, release,
deployment, documentation, or verification work-in-progress. They must be
preserved and are not authorized for replacement by this polish pass:

### Modified

- `.github/workflows/deploy.yml`
- `CHANGELOG.md`
- `PROJECT_STATUS.md`
- `README.md`
- `SCOPE_AND_DELIVERABLES.md`
- `apps/api/README.md`
- `apps/api/app/core/config.py`
- `apps/api/app/services/audio_job_service.py`
- `apps/api/app/services/ml_providers/reference_evidence.py`
- `apps/api/app/services/storage_service.py`
- `apps/api/app/tasks/worker.py`
- `apps/api/tests/test_one_day_pilot.py`
- `apps/api/tests/test_reference_evidence_provider.py`
- `apps/api/tests/test_workflow.py`
- `docs/DEPLOYMENT.md`
- `docs/PRODUCTION_SAAS_FIRST_LAUNCH_BACKLOG.md`
- `docs/PROJECT_SOURCE_OF_TRUTH.md`
- `docs/RENDER_BACKEND_STAGING_RUNBOOK.md`
- `packages/ml/reference_dataset.py`
- `requirements.txt`
- `scripts/check_project.sh`
- `scripts/check_repo_consistency.py`
- `scripts/package_release.sh`
- `scripts/security_scan.py`
- `tests/test_ml_reference_dataset.py`

### Deleted

- `artifacts/reference_evidence/candidate-v1/canonical_rows.csv`
- `artifacts/reference_evidence/candidate-v1/dataset_audit.csv`
- `artifacts/reference_evidence/candidate-v1/gate1_validation.json`
- `artifacts/reference_evidence/candidate-v1/manifest.json`
- `artifacts/reference_evidence/candidate-v1/reference_cells.csv`

### Untracked

- `.python-version`
- `apps/api/app/services/ml_artifact_registry.py`
- `apps/api/tests/test_ml_artifact_registry.py`
- `apps/api/tests/test_supabase_private_storage.py`
- `apps/api/tests/test_worker_runtime.py`
- `artifacts/active_artifacts.json`
- `artifacts/artifact_registry.json`
- `artifacts/reference_evidence/reference-core-14-v1/`
- `artifacts/verification/`
- `data/manifests/research_datasets.json`
- `docs/RENDER_FRONTEND_STAGING_RUNBOOK.md`
- `docs/THERAPIST_PRESENTATION_BLUEPRINT.md`
- `docs/release_artifacts/auth_verifier/preflight/`
- `docs/release_artifacts/auth_verifier/probes/`
- `docs/release_artifacts/auth_verifier/verifier-run-summary.md`
- `docs/release_artifacts/tenant_safety/`
- `docs/remediation/`
- `pyproject.toml`
- `scripts/benchmark_clinical_speech_artifacts.py`
- `scripts/build_review_archive.py`
- `scripts/build_review_archive.sh`
- `scripts/check_diarization_runtime.py`
- `scripts/check_python_runtime.py`
- `scripts/promote_artifact.py`
- `scripts/release_scope.py`
- `scripts/run_verification.py`
- `scripts/runtime_support.py`
- `scripts/verify_all.sh`
- `scripts/verify_backend.sh`
- `scripts/verify_frontend.sh`
- `scripts/verify_legacy.sh`
- `scripts/verify_migrations.sh`
- `scripts/verify_ml_artifacts.py`
- `scripts/verify_ml_artifacts.sh`
- `scripts/verify_release_archive.sh`
- `scripts/verify_repo_hygiene.sh`
- `scripts/verify_research_audio.sh`
- `scripts/verify_review_archive.py`
- `scripts/verify_shared.sh`
- `tests/test_check_diarization_runtime_script.py`
- `tests/test_clinical_speech_benchmark.py`
- `tests/test_clinical_speech_quality.py`
- `tests/test_create_supabase_project_setup_evidence_script.py`
- `tests/test_promote_artifact.py`
- `tests/test_python_runtime_support.py`
- `tests/test_release_scope.py`
- `tests/test_review_archive.py`

`PROJECT_STATUS.md`, `README.md`, `CHANGELOG.md`, and
`docs/PROJECT_SOURCE_OF_TRUTH.md` contain overlapping pre-existing release/ML
documentation edits. Later frontend documentation synchronization must use
small, targeted hunks and preserve those edits.

## Authoritative inputs inspected

- The attached final-polish brief, SHA-256
  `3a98aa9f8fad5c2c3d978d31688c5d2dd2495d700cbad76d5b287701cc87cbf4`
- `docs/PROJECT_SOURCE_OF_TRUTH.md`
- root `DESIGN.md`
- `apps/lingualens-app/DESIGN.md`
- `apps/lingualens-app/src/styles/globals.css`
- active UI imports and component source
- existing responsive, accessibility, bundle, benchmark, role, route, and
  workflow evidence
- the Airtable design reference linked by the brief

## Airtable-inspired decisions

Adopt as structural inspiration:

- white or near-white canvas, dark readable ink, and hairline separators;
- compact data rows, controls, toolbars, and structured panels;
- clear hierarchy with one dominant action rather than several equally loud
  actions;
- restrained radii, minimal elevation, and progressive disclosure for dense
  information.

Reject for LinguaLens:

- Airtable branding, proprietary typography, and marketing-page composition;
- coral, peach, mustard, forest, cream, rainbow, or editorial campaign palettes;
- large marketing cards, pricing pills, oversized headline bands, decorative
  gradients, and ornamental product chrome;
- any visual treatment that weakens clinical provenance, consent, stale-state,
  authorization, or therapist-review gates.

The unified LinguaLens product font remains `Noto Sans Thai`, `Noto Sans`, and
system fallbacks. Airtable is a layout-density reference, not a brand source.

## Design-system source audit

### Current executable state

`src/styles/globals.css` currently owns all of the following in one 315-line
file:

- semantic colors and compatibility aliases;
- radii, spacing, content widths, font, shadows, and motion timings;
- reset/body/global element behavior;
- component primitives such as `clinical-card`, `workspace-panel`,
  `reading-surface`, `control-strip`, `evidence-row`, `demo-note`, and
  `signature-band`;
- mobile safe-area, reduced-motion, and forced-colors rules.

The live base tokens are already close to the approved direction: near-white
surfaces, dark ink, muted teal accent, 6/8/10 px radii, Noto Thai/Latin font,
100/160/220/0 ms motion tiers, subtle shadows, and forced-colors handling.

### Contract drift

- Root `DESIGN.md` is stale and conflicts with the product: it names “ASD
  Project Speech Therapist,” specifies Outfit/Inter, 12–20 px radii, cyan-heavy
  surfaces, and older card guidance.
- `apps/lingualens-app/DESIGN.md` correctly documents the current Noto stack,
  canonical routes, role gates, responsive transcript contract, and
  accessibility acceptance, but incorrectly calls monolithic `globals.css` the
  executable token source for the new brief.
- The final contract requires a single authoritative split such as
  `src/design-system/tokens.css`, `typography.css`, and `components.css`, with
  `globals.css` limited to imports, reset, body/app primitives, and global
  accessibility rules.
- `evidence-row` and `signature-band` still use decorative gradients, and the
  waveform/ruler motif uses repeated linear gradients. These require visual
  review rather than blind keyword deletion because the ruler encodes a product
  motif while the surface gradients conflict with the quieter direction.

### Misleading active names

`src/components/liquid-ui.tsx` still exports `GlassCard` and `GradientButton`.
Active imports remain in Reports, Intake, Transcript, Findings, and Report
features. The rendered styles are no longer truly glass or gradient treatments,
so the names and central catch-all file misrepresent the current system. The
renaming/migration must preserve component behavior and test selectors.

## Current route and authorization contract

The build emits 21 application routes. Canonical product routes are `/today`,
`/cases`, `/cases/[caseId]`, `/sessions/[sessionId]`, `/reports`, `/settings`,
and `/login`. `/` redirects to `/today`. Identifier-less legacy routes
`/record`, `/review-transcript`, `/transcript`, `/results`, and
`/report-summary` resolve safely to `/cases?intent=start-session` unless a valid
identifier can be carried into Session Workspace. `/demo/*` is present only
when exact `NEXT_PUBLIC_DEMO_MODE=true` is enabled; otherwise it resolves through
the framework not-found boundary.

Session Workspace validates `?view=intake|transcript|findings|report` and uses
`intake` for missing or invalid values. `/settings` remains the only Settings
route. Team and audit sections are resolved from server-confirmed role data;
ordinary therapists do not mount admin controllers. Backend organization,
membership, invitation, care-team, privacy, and audit endpoints retain their
existing authorization and audit boundaries.

The frontend consumes backend contracts for runtime settings/capabilities,
remote-state errors, Cases, Sessions, Transcripts, QA, Features, ML/AI review,
Reports and provenance, organization readiness/memberships/invitations,
care-team assignments, Privacy, Jobs, and Audit. Existing contract tests cover
capability parsing, remote-state failure, authorization routing, stale response
settlement, and transcript/report provenance. This polish pass does not own API
schema or authorization changes.

## Workflow behavior frozen for characterization

- Today remains the approved focused workbench: one prioritized backend-derived
  queue, one next action per row, one prominent Start session action, and a quiet
  contextual rail.
- Cases uses list/detail routing and a desktop/tablet split pattern; mobile uses
  a dedicated detail route.
- Session preserves the four canonical views and identity-scoped controller.
- Transcript lines remain directly editable, selected lines expose
  `aria-selected`, secondary line actions use overflow, and save/job/error state
  is announced.
- Editing an existing transcript marks generated Findings and editable report
  drafts `stale` server-side. Never-generated artifacts remain `not_started`.
  Stale Findings are not current and stale Reports cannot be signed or exported.
- Settings admin data and mutations remain organization-admin only. Therapists
  receive only the safe case-level care-team summary already authorized by the
  backend.

## Visual baseline findings

Existing phase captures at 390×844, 768×1024, 1024×1366, 1280×800, and
1440×900 were reviewed under `docs/frontend/*-phase-screenshots/`.

### Today

The focused-workbench direction is already correct and should be preserved.
Desktop has a clear primary queue and quiet rail. Safety copy is repeated in the
shell rail and lower sidebar/context areas, so this pass should consolidate
global versus contextual messaging without changing queue behavior.

### Cases

The list is readable but the desktop right rail combines selected context,
overview statistics, workflow, and recent activity into one busy column. The
table is long and fixture repetition amplifies density. The next-action signal
should outrank secondary metadata. Mobile must keep deliberate selection and
dedicated detail navigation.

### Transcript

- Desktop must keep the editable transcript at least 60% wide while making the
  inspector collapsible/resizable without clipping.
- At 768×1024 the current one-column composition embeds Audio/QA inside a large
  workspace panel. The inspector is switchable, but the visual hierarchy still
  reads as stacked cards rather than a compact tablet workbench.
- At 390×844 the action strip is horizontally crowded and the player, QA,
  report-lock, and checklist content create an excessively long task path.
  Sticky regions require explicit safe-area and reserved-content checks.
- Selected lines and direct editing are present and must not regress.

### Findings

Findings is the clearest density failure. At 1440×900 and 390×844, every feature
renders its method, reference, and safety note inline, producing an extremely
long page. Summary, disposition, provenance, and primary next action should be
level 1; feature details level 2; evidence, methods, references, and limitations
level 3.

### Settings

Therapist Settings is a long sequence of large rounded cards on mobile.
Organization-admin Settings adds readiness, lifecycle, care-team, invitation,
membership, safety, and audit panels in one continuous desktop page. Both need
category → drill-down information architecture while preserving `/settings` and
strict role gating.

## Existing-change conflict requiring an explicit decision

`settings-workspace.tsx` initializes admin memberships and invitations from
`fallbackMemberships` and `fallbackInvitations`. On the first backend failure
for the same organization, those sample lifecycle records can remain visible
because they are only cleared when the organization identifier changes. This is
pre-existing behavior and appears intended as local-pilot demonstration data,
but it conflicts with the current fail-closed/no-fake-success contract and could
show admin data that was not confirmed by the backend.

Per the preserved-worktree instruction, production replacement of that behavior
is paused pending user approval. If approved, the smallest safe change is to add
a failing regression test, initialize lifecycle collections empty, render an
explicit unavailable state on failure, and leave every production authorization
guard unchanged.

### Post-baseline resolution — 2026-07-21

The user explicitly approved this replacement after the audit. A regression
test was first observed failing on the retained `Pilot Org Admin` sample record.
Memberships, invitations, and readiness now initialize and fail empty; the UI
shows backend-unavailable and empty-record states instead of sample admin data.
Production backend authorization guards were not changed. The role/deep-link
matrix now covers all five admin-only Settings categories.

## Baseline verification

Commands were run from `apps/lingualens-app` on the frozen commit unless noted.

| Gate | Result |
|---|---|
| `npm test` | PASS — 49 files, 377 tests |
| `npm run typecheck` | PASS |
| `npm run lint` | PASS with two pre-existing warnings in `supabase-mfa-panel.tsx`: missing `refreshFactors` effect dependency and raw `<img>` usage; `next lint` deprecation warning also remains |
| `npm run verify:bundle` | PASS — production build and all route/chunk budgets |
| `npx playwright test e2e/therapist-workflow.smoke.spec.ts e2e/accessibility-acceptance.spec.ts` | PASS — 5 tests |
| `NEXT_PUBLIC_DEMO_MODE=true npx playwright test e2e/demo-mode.smoke.spec.ts` | PASS — 2 tests |

Running demo smoke without `NEXT_PUBLIC_DEMO_MODE=true` fails by design because
the sample routes correctly return not-found. A combined unflagged invocation
therefore produced 5 passes and 2 expected demo failures; it must not be reported
as a product failure or as demo success. Explicit product and demo modes must be
verified separately.

### Bundle snapshot

| Route/chunk | Current | Budget |
|---|---:|---:|
| Shared first-load JS | 102 kB | 112 kB |
| `/today` | 213 kB | 213 kB |
| `/cases` | 225 kB | 242 kB |
| `/reports` | 212 kB | 229 kB |
| `/settings` | 218 kB | 232 kB |
| `/sessions/[sessionId]` | 219 kB | 230 kB |
| Largest async client chunk | 13.1 kB gzip | 80 kB gzip |

Today is exactly at its route budget. Any additional Today client code requires
remediation or an approved exception; the brief otherwise says to preserve this
screen.

### Transcript benchmark snapshot

The latest committed production benchmark was captured 2026-07-17 on headless
Chromium 149 / Apple M2, five runs per size:

| Lines | Ready p95 | Keystroke p95 | Selection p95 | Filter p95 | Worst scroll |
|---:|---:|---:|---:|---:|---:|
| 100 | 1179.73 ms | 23.4 ms | 24.0 ms | 33.3 ms | 60.51 fps |
| 500 | 962.91 ms | 23.0 ms | 28.9 ms | 34.0 ms | 60.45 fps |
| 1,000 | 966.47 ms | 19.7 ms | 14.0 ms | 47.8 ms | 61.84 fps |

Current evidence does not justify virtualization. The benchmark must be rerun
after transcript layout work; a budget regression requires remediation or an
approved exception.

## Documentation inconsistencies

- Root `DESIGN.md` is materially stale and must be replaced or redirected to the
  canonical app design contract.
- `apps/lingualens-app/DESIGN.md` must describe the new split design-system source
  rather than monolithic `globals.css`.
- `PROJECT_STATUS.md` is already dirty from unrelated remediation work and still
  cites 175 frontend tests in its tracker/snapshot while the current suite has
  377. Update only the frontend evidence hunks and preserve all unrelated edits.
- `UX_UI_COMPLETION_AUDIT_2026-07-17.md` and
  `LINGUALENS_UX_UI_MODERNIZATION_REPORT.md` describe the prior modernization as
  complete. They require a dated final-polish addendum and synchronized fresh
  evidence, not deletion of historical results.

## Approved implementation sequence after this gate

1. Resolve the admin fallback conflict explicitly.
2. Create or update the required concepts for Today, Cases, Transcript desktop,
   Transcript iPad portrait, Transcript iPad landscape, Transcript mobile,
   Findings, and Settings mobile before production visual changes.
3. Split and document the authoritative design system; migrate misleading
   legacy component names without changing behavior.
4. Polish Transcript, Findings, Settings, Cases, and repeated safety copy in
   small test-backed phases while preserving Today and all workflow/security
   contracts.
5. Run the per-phase completion gate and capture exact responsive evidence.
6. Synchronize documentation and publish
   `docs/frontend/LINGUALENS_FINAL_UX_UI_POLISH_REPORT.md` with a truthful
   COMPLETE or INCOMPLETE verdict.

Baseline gate status: **COMPLETE; production UI remains unchanged.**
