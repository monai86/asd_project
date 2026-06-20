# ASR Evaluation Dataset

This directory is the local scaffold for small, auditable ASR quality checks.

- `audio_samples/`: optional local audio sample placeholders or deployment-managed references.
- `gold_transcripts/`: therapist-reviewed gold `.cha` or `.txt` transcripts.
- `hypothesis_transcripts/`: ASR-generated draft `.cha` or `.txt` transcripts with matching file stems.

Do not commit real child identifiers, private transcript text, raw audio bytes,
storage keys, or consent-restricted media here.
