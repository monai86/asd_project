# Use reviewed transcript lines as the clinical speech source

After a clinician edits a transcript, reviewed CHAT exports and clinical speech
feature extraction will be rebuilt from the transcript lines rather than from
the original CHAT transcript text snapshot. This preserves clinician
corrections, avoids silently reusing stale ASR output, and keeps the raw
transcript snapshot available as provenance rather than treating it as the
post-review source of truth.
