# Therapist App v2 Known Limitations

- **Decision-support only, not diagnostic**: Therapist App v2 is a research and education prototype, not a clinical diagnostic product. It does not provide automated diagnostic assertions.
- **ASR is experimental**: Audio recording and ASR-to-draft-CHA translation are experimental and must not be used as direct clinical input.
- **Basic CHAT format only**: CHAT import and export support basic header, speaker tier, and bullet timestamp structure.
- **Not full TalkBank/CLAN-grade compatibility yet**: The parser does not validate full TalkBank/CLAN conventions.
- **JSON repository mode is the default for usable-prototype persistence**: It survives API restarts and reloads case, session, transcript, and report states.
- **Memory mode is only for isolated tests/demo reset**: It is not persistent and clears on restart.
- **sessionStorage is UI cache/local fallback only**: It must never silently overwrite backend session, transcript, QA, attestation, or report states.
- **Backend is source of truth when IDs exist**: If a workflow identifier (like `transcript_id`) exists in the URL or props, the backend transcript must win and override any cached or stale sessionStorage values.
- **Audio bytes remain memory-only unless explicitly uploaded**: Browser microphone recording audio remains in-memory only and is lost on refresh unless the therapist explicitly initiates an upload.
- SQLAlchemy models and an initial Alembic migration define the PostgreSQL-ready
  schema. `THERAPIST_APP_V2_REPOSITORY_MODE=sql` provides a SQLAlchemy-backed
  snapshot repository, but SQL mode is not pilot-hardened and still needs
  transaction design, migrations discipline, role enforcement, and operational
  backup/restore procedures.
- Audio-to-draft-CHA is experimental and must not become the MVP dependency.
  Browser recording supports capture and playback but does not automatically
  upload audio. The explicit **Upload for transcription** action currently uses
  an in-memory local mock processing API and creates workflow-test draft text;
  it is not real or validated ASR.
  The current provider interface supports manual, Whisper, Faster Whisper,
  WhisperX, and Batchalign provider names, but non-manual providers are
  placeholders until deployment-specific ASR dependencies are configured.
- Audio processing is queued through a memory queue by default. Redis queue mode
  is a boundary for pilot wiring, not a fully hardened production worker system.
- ASR dataset evaluation compares reviewed gold transcripts with ASR draft
  transcripts for engineering QA. It does not establish clinical validation,
  deployment readiness, or Thai norms.
- **Local audio upload stores raw audio bytes in development mode**: Uploaded audio files are stored locally on the backend under `.local/storage/audio/` and streamed via HTTP range requests. Browser memory contains zero audio bytes for persisted sessions, and seeking and line-level synchronization utilize backend range streaming.
- ASR-generated transcripts are blocked from report-eligible feature use until
  therapist review and quality attestation. Mock and ASR drafts are labelled
  “Draft transcript — therapist review required.” and any speaker segments not matching the child (`CHI`) speaker are mapped to a default speaker code (`UNK`).
- Consent withdrawal unlinks local audio metadata, records storage deletion
  status, marks therapy goals as withdrawn, redacts goal notes when requested,
  removes linked feature artifacts, cancels queued audio jobs, and blocks new
  case workflow actions, feature reads, or exports.
  Real private object deletion requires the pilot storage integration.
- Review cues are descriptive prompts for therapist review, not diagnostic
  markers. All system outputs are decision-support only and must not be used for diagnostic validation.
- Import/export supports basic CHAT format only and does not claim full TalkBank/CLAN-grade compatibility.
- Thai clinical norms and Thai clinical validation are not established.
- PDF export depends on deployment packaging; Markdown and browser print are
  the reliable local demo paths. Report export is blocked until therapist
  sign-off in the API.
- Audit logs are exposed behind a mock admin role header in local mode. Real
  pilot deployments still require production authentication and authorization.
- The ML dataset builder can parse local `.cha` files into auditable feature
  rows, and the baseline evaluator only runs when enough labeled rows exist.
  This is still not clinical validation and does not establish Thai norms.
