# Project Update Workflow

Use the canonical project skill at:

`.agents/skills/project-update-workflow/SKILL.md`

After every meaningful project change:

- Inspect `git status --short`, `git diff --stat`, and the actual diff.
- Update `README.md` when entry-point information changes.
- Update `CHANGELOG.md` when behavior, features, dependencies, deployment, or important docs change.
- Update relevant docs under `docs/` when their topic changes.
- Run relevant checks before commit or push.
- Use Conventional Commits.
- Do not push to GitHub without user approval.
- Warn if any remote URL contains an embedded token or credential.

Final responses should state whether README/CHANGELOG were updated, which checks ran, and whether commit/push was performed.
