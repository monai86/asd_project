# Store clinical speech artifact content outside primary records

Clinical speech artifacts will keep review, provenance, freshness, and lookup
metadata in database records while storing larger generated content, such as
CHAT files, Batchalign outputs, CLAN raw output, and long subprocess logs, in
private file or object storage. Small parsed metrics and short summaries may
remain in structured database fields. This avoids mixing generated files with
clinician-reviewed transcript lines, supports multiple artifact versions per
session, and preserves a private download/export boundary instead of exposing
storage keys to browser clients.
