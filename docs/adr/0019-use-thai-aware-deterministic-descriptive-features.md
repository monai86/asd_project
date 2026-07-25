# Use Thai-aware deterministic descriptive features for the v1.7.0 testbed

LinguaLens v1.7.0 limits milestone-gated Findings to versioned descriptive
counts, timing and intelligibility measures, plus token-dependent values only
when a pinned Thai-aware tokenizer profile passes golden fixtures. Tokenizer
failure preserves non-token metrics and returns token metrics as explicitly
`unavailable` rather than zero or a silent regex fallback; heuristic cues
remain experimental, while ML, reference comparisons, norms, diagnostic
classification, and treatment recommendations stay outside this vertical
slice.
