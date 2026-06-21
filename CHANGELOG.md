# Changelog

## [v1.6.3] - 2026-06-21

### Changed
- Replaced therapist Cases pages with backend-backed case and timeline views,
  while keeping seeded fallback content only for offline/demo continuity.
- Replaced the placeholder Reports page with a persisted report index that opens
  draft or finalized reports from the active API workspace.
- Aligned maintained therapist-product metadata across the therapist app,
  shared package, API OpenAPI version, and report audit provenance.
- Removed obsolete demo surfaces, legacy benchmark pipelines, stale benchmark
  artifacts, and outdated summary documents from the working tree so the
  repository points only to the current therapist workflow and current
  reference-evidence ML path.
- Refreshed maintained documentation and repository checks to describe only the
  current runtime, current ML workflow, and current verification path.

### Fixed
- Accepted the therapist frontend `X-User-Id` header in the active API security
  dependency to remove auth-contract drift between the canonical frontend and
  backend.
