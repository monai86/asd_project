# Therapist App v2 Known Limitations

- **Decision-support only, not diagnostic**: Therapist App v2 is a research and education prototype, not a clinical diagnostic product. It does not provide automated diagnostic assertions.
- **ASR is experimental**: Audio recording and ASR-to-draft-CHA translation are experimental and must not be used as direct clinical input.
- **Basic CHAT format only**: CHAT import and export support basic header, speaker tier, and bullet timestamp structure.
- **Not full TalkBank/CLAN-grade compatibility yet**: The parser does not validate full TalkBank/CLAN conventions.
- Mock mode is the default. A JSON-backed local repository exists for backend
  demo persistence, but secure pilot persistence, role enforcement, signed URLs,
  encrypted storage, and audit hardening require deployment-specific
  configuration.
- The active simplified workflow uses current-tab `sessionStorage` so page
  refreshes retain local session state. This is demo persistence only, clears
  when the tab session ends, and must not contain real child identifiers,
  sensitive clinical transcripts, or audio bytes. Browser microphone audio is
  memory-only and is intentionally lost on refresh; only duration, MIME type,
  status, creation time, and an unsaved-recording flag persist.
- SQLAlchemy models and an initial Alembic migration define the PostgreSQL-ready
  schema. `THERAPIST_APP_V2_REPOSITORY_MODE=sql` provides a SQLAlchemy-backed
  snapshot repository, but a final audited pilot repository still needs
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
- Local audio upload stores metadata and a mock signed upload intent only.
  Upload completion records checksum metadata, not raw audio bytes. The local
  storage adapter can delete development files under its configured root, but
  private pilot object storage remains deployment-specific.
- ASR-generated transcripts are blocked from report-eligible feature use until
  therapist review and quality attestation. Mock and ASR drafts are labelled
  “Draft transcript — therapist review required.”
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
