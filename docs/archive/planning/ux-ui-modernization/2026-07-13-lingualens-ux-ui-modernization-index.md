# LinguaLens UX/UI Modernization Plan Index

Approved specification: `docs/superpowers/specs/2026-07-13-lingualens-ux-ui-modernization-design.md`

Execute these plans in order. Each plan produces testable software and ends at the approved phase gate.

1. `2026-07-13-lingualens-contracts-and-data-modes.md`
2. `2026-07-13-lingualens-decomposition-routes-auth.md`
3. `2026-07-13-lingualens-responsive-screens.md`
4. `2026-07-13-lingualens-hardening-verification.md`

Global rules:

- Preserve the current dirty worktree and the external Phase 0 backup patch.
- Read `docs/PROJECT_SOURCE_OF_TRUTH.md` before each plan.
- Run frontend commands inside `apps/lingualens-app`.
- Characterize existing behavior before refactoring it.
- Start bug fixes and new behavior with a failing test.
- Use approved visual comparisons for purely visual changes.
- Do not move to the next plan until the current plan's phase gate passes.
- Every AI commit includes `Co-Authored-By: GPT-5 Codex <codex@openai.com>`.
