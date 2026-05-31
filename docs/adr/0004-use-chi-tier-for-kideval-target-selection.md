# Use CHI tier for KIDEVAL target selection

KIDEVAL defaults to selecting speakers with the `Target_Child` role, but some
analysis-ready TalkBank corpora mark the child role as `Child` while still
using the canonical `*CHI` speaker tier. We will run KIDEVAL with `+t*CHI` for
curated English child transcripts because the Corpus Manifest already requires
both a CHI ID and a CHI tier before analysis.

This keeps CLAN-Derived Metrics available across corpora without rewriting
curated CHAT transcripts or treating role labels as clinical truth. The result
remains a descriptive research metric only, not a diagnostic norm or validated
clinical benchmark.
