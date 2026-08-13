# Use canonical semantic CHAT round-trip with deterministic LinguaLens exports

LinguaLens v1.7.0 verifies `.cha` exports by comparing supported semantic fields
after export and parse, while preserving or explicitly rejecting unknown
content instead of silently dropping it. External CHAT files are not required
to retain their original bytes, but artifacts serialized by the same
LinguaLens CHAT subset, parser, serializer, and normalization versions must
re-export to identical canonical bytes and checksums; this balances
interoperability with deterministic, auditable loss detection.

To avoid allowing attestation before serializer integrity is known while still
forbidding pre-attestation clinical exports, QA runs the same round-trip on an
internal non-downloadable candidate. Final export repeats verification against
the attested versions and persists the clinical artifact only after both gates
pass.
