# Stale derived-state debugging ledger — 2026-07-15

## Intent

Represent transcript-driven invalidation explicitly and persistently so findings and editable report drafts cannot be mistaken for current results after a transcript changes.

## Experiments and breadcrumbs

1. **Source trace of transcript mutation**
   - Path: transcript PATCH/replacement → repository `update_transcript`/`create_transcript` → session downstream identifiers.
   - Observation: both mock and SQL repositories clear the session's feature, ML/AI review, and report pointers.
   - Consequence: the UI loses the reason after reload, while the preserved derived records retain current-looking statuses.
   - Rules out: a frontend-only stale flag as an adequate fix.

2. **Source trace of report gates**
   - Path: report read → `sign_off_report` or `export_report`.
   - Observation: export requires `Signed Off`; sign-off is indirectly blocked after transcript edits because the session no longer points to the draft, not because the draft is explicitly stale.
   - Consequence: direct report reads have no explicit invalidation state and the safety rule depends on pointer topology.
   - Rules out: relying on the existing indirect sign-off failure as the final contract.

3. **Source trace of feature/report regeneration**
   - Path: feature extraction/report drafting → session pointer lookup → reuse/create behavior.
   - Observation: report drafting reuses any non-signed active report; feature/report readiness does not currently reject an explicit stale status because that status does not exist.
   - Consequence: retaining stale pointers requires explicit currentness checks and regeneration behavior.
   - Rules in: persisted stale status plus gate-aware replacement/regeneration.

4. **Existing model capabilities**
   - `FeatureSet.review_status` and `Report.status` already use `ReviewStatus`.
   - `MLResult.is_current` already represents derived-result currentness.
   - AI review uses `therapist_review_status`.
   - Consequence: the smaller backend change is to extend existing fields rather than introduce parallel stale-ID columns.

## Ranked hypotheses

1. Persisting `stale` on existing derived records, retaining their session references for explanation, and making all consumers currentness-aware provides the required reload and gate behavior with the smallest schema expansion.
2. Clearing pointers and adding separate stale-reference fields would work but duplicates provenance and expands every repository/schema path.
3. Keeping pointer clearing with only frontend cache migration cannot satisfy server-side persistence or reliable reload behavior.

## Falsification target

The preferred design is disproved if a stale pointer can be consumed as current by any feature, ML/AI, report drafting, sign-off, export, or previous-session comparison path, or if regeneration reuses stale content without recomputation/version updates.

## Evidence and resolution

- RED transition tests showed that a failed first analysis was incorrectly
  promoted to stale and that failed regeneration lost existing stale
  provenance; the reducer now distinguishes never-generated from preserved
  derived records.
- RED mock and SQL tests showed that pointer clearing erased invalidation
  context; transcript writes now atomically mark findings, AI review, ML review,
  and editable reports stale/non-current while preserving signed snapshots.
- RED workflow-gate tests showed stale report, AI, and ML mutation paths plus
  transcript-version mismatches were still actionable; consumers and mutation
  routes now reject obsolete inputs.
- RED interleaving tests showed late findings, report, AI, and ML completions
  could repoint the session after a transcript edit; frontend settlement guards
  and repository conditional writes now require matching live provenance.
- RED persistence/UI tests established lowercase stale-state migration, signed
  versus stale report hydration, hidden stale findings, and explicit
  regeneration guidance.
- Final verification: 279 frontend tests and 125 focused backend workflow/
  transaction tests passed; frontend typecheck passed and `git diff --check`
  was clean.
