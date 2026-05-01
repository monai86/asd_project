---
name: project-update-workflow
description: Maintain this asd-project repository after every meaningful project change by updating README.md, CHANGELOG.md, project docs, version notes, commit messages, GitHub push steps, and release tags in a systematic way. Use whenever code, features, dependencies, folder structure, documentation, deployment, reports, models, data-processing behavior, Streamlit dashboard behavior, or project milestones change.
---

# Project Update Workflow

## Purpose

Keep `asd-project` documented, versioned, and ready to push to GitHub after every meaningful change. Treat documentation as part of the deliverable, not a cleanup task.

Source project docs:

- `docs/DEVELOPMENT.md`
- `docs/VERSION_UPDATE_CHECKLIST.md`
- `CHANGELOG.md`
- `README.md`

## Trigger Decision

Use this skill when any of these change:

- New feature or changed behavior
- Bug fix that affects runtime behavior
- Folder structure
- Important dependency
- How to run, test, deploy, or use the app
- Streamlit dashboard behavior
- Data pipeline, audio pipeline, ML model, metrics, reports, or figures
- Important documentation or advisor-facing summary
- Release milestone

Do not require a README update for tiny internal bug fixes, formatting-only edits, comments, or docstrings unless they affect user-facing behavior or project instructions.

## Required Workflow

1. Inspect the actual diff before deciding what to update:
   - `git status --short`
   - `git diff --stat`
   - `git diff`
2. Classify the change:
   - `feat`: new feature
   - `fix`: behavior-affecting bug fix
   - `docs`: documentation only
   - `refactor`: behavior-preserving code cleanup
   - `test`: test-only change
   - `deps`: dependency update
   - `chore`: config or maintenance
3. Update `README.md` when project entry-point information changed.
4. Update `CHANGELOG.md` when behavior, features, bug fixes, dependencies, deployment, or important docs changed.
5. Update project docs when their topic is affected:
   - `docs/DEVELOPMENT.md` for workflow/version process
   - `docs/DEPLOYMENT.md` for deploy/runtime changes
   - `docs/AUDIO_PIPELINE.md` for audio/ASR/CHAT pipeline changes
   - `docs/PROJECT_SUMMARY_TH.md` for advisor-facing project progress
   - `docs/DISCUSSION_TH.md` for discussion points
   - `docs/REFERENCES.md` for new papers, libraries, or methods
6. Run relevant checks before commit or push.
7. Prepare a clear Conventional Commit message.
8. Push to GitHub only when the user asks or approves.

## README Update Rules

Update `README.md` when:

- A feature is added or removed.
- The folder tree changes.
- Important dependencies are added or removed.
- Run, test, deploy, or usage commands change.
- Important docs are added.
- Dashboard pages, pipeline stages, output files, or reports change.

Keep README concise. It should remain the project entry point, not the full technical diary. Link to detailed docs instead of duplicating long explanations.

## CHANGELOG Rules

Update `CHANGELOG.md` for meaningful project changes. Use a new top entry with:

```markdown
## [vX.Y.Z] - YYYY-MM-DD

### Added
- **Feature name** — concise impact-oriented description

### Changed
- **Area** — what changed and why

### Fixed
- **Bug** — what was fixed

### Removed
- **Area** — what was removed
```

Version bump guidance:

- PATCH: bug fixes and small behavior improvements.
- MINOR: backward-compatible features or notable new capabilities.
- MAJOR: breaking changes, major scope expansion, or removal of important functionality.

Documentation-only changes do not need a version bump unless they represent an important project milestone.

## Verification Rules

Choose checks based on the changed area:

- Python/data pipeline: run targeted scripts or tests.
- Streamlit dashboard: run or smoke-check `streamlit run app/dashboard.py` when UI behavior changes.
- Tests: run relevant `pytest` tests when code behavior changes.
- Docs-only: proofread links, commands, file paths, and version references.
- Deployment: verify `requirements.txt`, `packages.txt`, Docker/Streamlit config, and deploy instructions.

Do not push code that is known not to run.

## GitHub and Release Rules

Use Conventional Commits:

```text
<type>(optional-scope): <imperative subject>
```

Good examples:

```text
feat(audio): add echolalia ratio feature
fix(dashboard): handle empty DataFrames gracefully
docs: update project summary with latest results
deps: add faster-whisper for ASR pipeline
```

Before push:

- Confirm `git status --short`.
- Confirm README/CHANGELOG/docs reflect the actual change.
- Confirm no secrets, tokens, large audio files, or unnecessary binaries are staged.
- Commit with a clear message.
- Push to `origin main` only with user approval.

For major milestones:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z: short summary"
git push origin vX.Y.Z
```

## Security Note

If a remote URL contains an embedded token or credential, warn the user and recommend rotating the token and changing the remote URL before pushing.

## Final Response Contract

When this skill is used, include:

- Files updated for documentation/versioning.
- Whether README was updated or why it was not needed.
- Whether CHANGELOG was updated or why it was not needed.
- Checks run and results.
- Commit/push status, if performed.
- Any remaining manual steps.
