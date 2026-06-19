# Known Limitations

- **Decision-support only, not diagnostic**: This is a research and education prototype, not a clinical diagnostic product or validated clinical tool. It does not provide automated diagnoses.
- **ASR is experimental**: Browser recording and automated speech recognition (ASR) are experimental. The transcription job uses a local mock processing API and does not claim accurate speech recognition.
- **Basic CHAT import/export only**: Import and export support basic CHAT file structure (metadata headers, speaker tiers, timestamps) and skip unsupported tiers with warnings.
- **Not full TalkBank/CLAN-grade compatibility yet**: The parser does not validate full TalkBank/CLAN compatibility or enforce all syntactic conventions of the CLAN utility suite.
- Audio remains memory-only in the browser and is lost on page refresh.
- Current-tab browser persistence is for demonstrations only and must not contain real identifiers, sensitive clinical data, or raw transcript recordings.
- Feature extraction provides descriptive language-sample cues for clinical interpretation, not diagnostics.
- ML output is editable/dismissible decision support trained on limited/public datasets and is not clinically validated.
- Reports require therapist review. Local finalization is not a production signature or secure caregiver-delivery workflow.
- Markdown and HTML export are available. PDF export is not yet implemented.
- Production authentication, encrypted private storage, durable queues, deployment monitoring, and audited role enforcement remain future work.

For engineering detail, see
[`docs/THERAPIST_APP_V2_KNOWN_LIMITATIONS.md`](docs/THERAPIST_APP_V2_KNOWN_LIMITATIONS.md).
