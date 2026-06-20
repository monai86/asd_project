# Therapist App v2 Local Demo

Therapist App v2 is a case-centered, manual-first clinical decision-support
prototype. It does not replace therapist judgment, does not provide an
automated diagnosis, and keeps transcript review and therapist sign-off as
workflow gates.

## Install

Backend:

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Frontend:

```bash
cd apps/therapist-app-v2
npm install
```

## Run Backend

```bash
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

The default repository mode is JSON for locally usable-prototype persistence.
Case, session, transcript, QA, attestation, feature, and report records survive
API restarts at `.local/therapist-app-v2-repository.json`.

```bash
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Use `THERAPIST_APP_V2_REPOSITORY_MODE=memory` only for isolated tests or an
intentional demo reset. SQL mode is PostgreSQL-ready but not pilot-hardened.

For SQLAlchemy-backed local persistence with SQLite:

```bash
cd apps/api
THERAPIST_APP_V2_REPOSITORY_MODE=sql \
THERAPIST_APP_V2_DATABASE_URL=sqlite:///.local/therapist-app-v2.db \
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

For PostgreSQL, set `THERAPIST_APP_V2_DATABASE_URL` to a
`postgresql+psycopg://...` URL and apply the Alembic migration before pilot
testing.

## Run Frontend

```bash
cd apps/therapist-app-v2
npm run dev
```

Open `http://localhost:3000/login`.

If the backend is running on the default port, start the frontend with the
explicit API URL for the demo:

```bash
cd apps/therapist-app-v2
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

The simplified therapist workflow uses these user-facing routes:

- `/record` for recording and input selection
- `/results` for the session decision-support summary
- `/review-transcript` for therapist transcript review
- `/report-summary` for the session report draft and finalization state

Quick Start uses `/record?mode=audio`, `/record?mode=cha`, and
`/record?mode=paste` for alternate local inputs. `/record` uses the browser
MediaRecorder API for microphone permission, live recording, pause/resume,
timer and amplitude display, in-page playback, deletion, and re-recording.
Real ASR is not enabled.
Recorded audio bytes and object URLs remain memory-only for the current page
lifecycle. `sessionStorage` retains only duration, MIME type, recording status,
creation time, and whether an unsaved recording existed. Refresh clears the
audio and displays: “Unsaved recording was cleared for privacy. Please record
again.” Recording is not uploaded automatically. An explicit **Upload for
transcription** action sends the current in-memory Blob to a local mock
processing API, shows queued / processing / completed / failed job states, and
routes the resulting draft to `/review-transcript`.
The mock output is always labelled “Draft transcript — therapist review
required.” and does not represent accurate or production ASR.
Pasted speaker-labelled text is converted into a reviewable CHAT draft.
Uploaded `.cha` files are validated for CHAT boundaries and speaker tiers, with
speaker labels and media-bullet timestamps retained for transcript review.
Basic import also retains `@Languages`, `@Participants`, `@ID`, and `@Media`
metadata. Syntactically valid configured speaker codes are preserved; dependent
tiers that are not supported by the editor are skipped with visible warnings.
The `/review-transcript` route presents those turns as editable rows with
timestamps, speaker labels, utterance text, QA state, add/delete, split/merge,
and unclear controls. Draft saves do not unlock downstream outputs: QA must run
and the therapist must attest the transcript before feature extraction or
report generation is enabled.

Reviewed export is rebuilt from the current transcript lines and includes basic
CHAT headers, participant IDs, optional non-identifying linked media, speaker
tiers, and available media bullets. The UI labels this boundary explicitly:
“Basic CHAT export. Therapist review required before research or clinical use.”
This is not a claim of full TalkBank compatibility.

The login page is mock mode only. The role selector routes therapists to
Today / Work Queue and routes admins to Settings / Admin with an admin scope
query parameter; it does not create a production auth session. The active
simplified workflow uses backend records as the source of truth whenever
session, transcript, or report IDs exist. Current-tab `sessionStorage` is only a
UI cache/local fallback. If the API is unreachable, the app visibly shows
**Backend unavailable — local workspace mode**. This mode is not production
clinical storage and local changes may not persist across devices or server
restarts. Do not enter real child identifiers or sensitive clinical transcripts
in local/demo mode.

## Demo Workflow

1. Open `http://localhost:3000` and choose **Start Recording**.
2. Allow microphone access, then start and stop the experimental recording.
3. Select **Upload for transcription** and wait for the queued, processing,
   and completed states.
4. Review and correct the draft transcript. Run QA and attest it.
5. Extract language-sample features and open `/results`.
6. Generate the editable report draft.
7. Review the report and select **Finalize Report**.

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the presenter checklist.

## Limitations

This is a local research/education prototype. Recording and ASR are
experimental, browser audio is memory-only, mock ASR is not accurate or
clinically validated, local browser state is not secure clinical storage, and
all transcript, feature, ML, and report content requires therapist review.

See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for the concise demo-facing
limitations and
[`docs/THERAPIST_APP_V2_KNOWN_LIMITATIONS.md`](docs/THERAPIST_APP_V2_KNOWN_LIMITATIONS.md)
for the detailed engineering list.

## Run Worker

```bash
cd apps/api
PYTHONPATH=. python -c "from app.tasks.worker import run_worker; print(run_worker())"
```

The current worker boundary is local/demo-oriented. Audio processing is exposed
through API jobs and can later move behind Redis or another durable queue
without changing the therapist workflow.

Audio processing jobs are queued by `/audio/process`. Run the worker to process
one queued job:

```bash
cd apps/api
PYTHONPATH=. python -c "from app.tasks.worker import run_worker; print(run_worker())"
```

Queue modes:

- `THERAPIST_APP_V2_JOB_QUEUE_MODE=memory`: local in-process queue for demos and
  tests.
- `THERAPIST_APP_V2_JOB_QUEUE_MODE=redis`: Redis queue boundary for pilot
  wiring; requires the `redis` Python package and a configured `REDIS_URL`.

## Run Tests

```bash
cd apps/api
PYTHONPATH=. pytest -q

cd ../../apps/therapist-app-v2
npm run typecheck
npm run lint
npm test
npm run build
```

Backend tests cover the manual workflow gates plus core feature metrics: MLU in
words, TTR, NDW, unintelligible ratio, unknown speaker ratio, QA blocking, and
transcript-version capture.

The simplified workflow extracts deterministic descriptive language-sample
cues only after the transcript is saved, reviewed, QA-checked, and attested.
The `/results` page shows utterance counts, child-word count, MLU-w, NDW, TTR,
question and unclear ratios, plus conservative repetition, echolalia, and
pronoun-reversal review cues. These values are not an ASD prediction or
diagnosis.

`/report-summary` generates an editable report draft from session metadata,
reviewed transcript status, feature summaries, therapist notes, and therapy
goals. Reports move through Draft, Reviewed, and Finalized; finalized content
is read-only. Markdown and HTML downloads are available, while PDF remains a
later/dependency-gated option. Share status is recorded without claiming real
delivery in local mode.

## Professor Demo And Scope Docs

- `docs/PROFESSOR_DEMO_SCRIPT.md` gives the exact local command sequence and
  click-by-click walkthrough for the manual-first MVP.
- `docs/MVP_VS_EXPERIMENTAL_SCOPE.md` separates stable local MVP behavior from
  experimental audio/ASR/ML and pilot-hardening surfaces, and includes the final
  feature-to-endpoint verification table.
- `docs/THERAPIST_APP_V2_KNOWN_LIMITATIONS.md` remains the limitation checklist
  for Thai validation, production auth, storage hardening, durable workers, and
  real ASR providers.

## Create A Case

```bash
curl -X POST http://localhost:8000/api/v1/cases \
  -H 'content-type: application/json' \
  -d '{"child_code":"C-2001","age_months":54,"language":"English","consent_status":"granted"}'
```

## Create A Session

```bash
curl -X POST http://localhost:8000/api/v1/cases/case_demo_001/sessions \
  -H 'content-type: application/json' \
  -d '{"session_date":"2026-06-13","session_type":"therapy_session"}'
```

## Upload A `.cha`

Use `data/demo/sample_session.cha` as demo input. The endpoint accepts JSON in
mock mode:

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/transcripts/upload-cha \
  -H 'content-type: application/json' \
  -d '{"filename":"sample_session.cha","cha_text":"@Begin\n@Languages:\teng\n@Participants:\tCHI Child Target_Child, THER Therapist Investigator\n*CHI:\tI see car .\n@End"}'
```

`data/demo/demo_manifest.json` lists the local demo package: mock therapist and
admin accounts, anonymized case codes, demo sessions, the sample `.cha`, and
the sample report. It intentionally excludes real child identifiers, raw audio,
storage keys, and transcript identifiers.

## Edit And Export A Transcript

The API supports utterance-level transcript edits:

```bash
curl -X POST http://localhost:8000/api/v1/transcripts/{transcript_id}/split \
  -H 'content-type: application/json' \
  -d '{"utterance_id":"utt_id","split_at_character":12}'

curl -X POST http://localhost:8000/api/v1/transcripts/{transcript_id}/merge \
  -H 'content-type: application/json' \
  -d '{"first_utterance_id":"utt_a","second_utterance_id":"utt_b"}'

curl http://localhost:8000/api/v1/transcripts/{transcript_id}/export-cha
```

Any transcript edit or replacement clears therapist attestation and makes prior
outputs stale until QA, attestation, and feature extraction are repeated. Active
session pointers to prior feature sets, AI-assisted review support, and report
drafts are cleared; retained artifacts remain audit context, not current output.
Transcript QA warns when CHAT language metadata is outside the supported local
QA languages or when mixed Thai/English text appears without matching language
metadata so the therapist can document interpretation limits.
If retained audio metadata is linked to the session, corrected `.cha` export
includes a non-identifying `@Media` header based on session/audio record IDs,
not the original uploaded filename.

## Generate A Report

Run transcript QA, therapist attestation, feature extraction, AI-assisted review
support, then draft a report:

```bash
curl -X POST http://localhost:8000/api/v1/cases/{case_id}/goals \
  -H 'content-type: application/json' \
  -d '{"title":"Increase reciprocal turns","target":"Use reviewed transcript samples across sessions."}'

curl -X POST http://localhost:8000/api/v1/transcripts/{transcript_id}/qa
curl -X POST http://localhost:8000/api/v1/transcripts/{transcript_id}/attest \
  -H 'content-type: application/json' \
  -d '{"reason":"Therapist reviewed transcript quality."}'
curl -X POST http://localhost:8000/api/v1/transcripts/{transcript_id}/extract-features -H 'content-type: application/json' -d '{}'
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/ai-review
curl -X PATCH http://localhost:8000/api/v1/ai-reviews/{ai_review_id} \
  -H 'content-type: application/json' \
  -d '{"summary":"Therapist-edited decision-support summary.","therapist_review_status":"Attested","therapist_notes":"Reviewed before report draft."}'
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/reports/draft -H 'content-type: application/json' -d '{}'
```

The Session Workspace `Run demo workflow` action exercises the complete
API-backed manual-first path: create/open case, create session, upload sample
CHA, run QA, attest transcript, extract features, generate AI-assisted review
support, draft report, edit report, sign off report, export report, and export
reviewed CHA.

Feature extraction from a failed-QA or unattested transcript is blocked by
default clinical workflow. `THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE=false` is
the local demo default. Engineering-only runs may opt in with
`THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE=true` and must send an explicit
override reason.
The v2 Session Workspace demo workflow shows extracted MLU, TTR, NDW, and
question-ratio summaries plus AI review priority/status after the attested
manual CHA workflow runs.
AI-assisted review records retain model/prompt metadata plus the input
transcript version, feature set id, and feature schema version used to generate
the decision-support summary. Each record also returns five therapist-review
areas: Transcript QA Assistant, Feature Explanation Assistant, Review Priority,
Progress Summary, and Report Drafting. These areas are editable decision
support only; Review Priority is shown as low, moderate, or high without raw
model probability.
Text prepared for AI-assisted processing is sanitized for direct identifiers
such as names, birth dates, phone numbers, emails, addresses, and clinical or
school record IDs. This is a safety layer, not a compliant external-AI
deployment approval.

When the same case has a previous reviewed session with extracted features, the
draft includes a descriptive Progress Comparison section. It is not an automated
clinical improvement conclusion.
Set `report_type` to `Session Review Report`, `Progress Report`,
`Transcript QA Report`, or `Research/Model Summary Report` to generate the
matching focus section. Drafts also include transcript QA detail, recommended
therapist review, clinical interpretation notes, limitations, sign-off status,
and export timestamp state.
The v2 Reports page mirrors these four report types and disables Markdown,
HTML, and PDF export actions until the report has therapist sign-off.

Rejected AI-assisted review support is excluded from report content:

```bash
curl -X PATCH http://localhost:8000/api/v1/ai-reviews/{ai_review_id} \
  -H 'content-type: application/json' \
  -d '{"therapist_review_status":"Withdrawn","rejected_reason":"Not clinically useful for this session."}'
```

Report export is blocked until therapist sign-off:

```bash
curl -X POST http://localhost:8000/api/v1/reports/{report_id}/sign-off \
  -H 'content-type: application/json' \
  -d '{"signed_by":"Demo Therapist","attestation":"I reviewed this report."}'

curl 'http://localhost:8000/api/v1/reports/{report_id}/export?format=markdown'
curl 'http://localhost:8000/api/v1/reports/{report_id}/export?format=html'
curl 'http://localhost:8000/api/v1/reports/{report_id}/export?format=pdf'
```

Sign-off stamps the report body with signer, sign-off status, and export
timestamp before export.

PDF export returns base64 PDF content when the optional PDF dependency is
available. Otherwise it returns Markdown plus an `unavailable_reason` so the
therapist can use Markdown or browser print.

## Run Experimental Audio-To-Draft-CHA

Audio automation is not the MVP dependency. In mock/local mode it creates an
unreviewed draft transcript through a provider interface and requires therapist
correction before feature extraction.

Audio upload uses backend-side metadata and a mock signed upload intent. Raw
audio bytes are not placed in API JSON payloads or persistent browser storage.
The `/record` microphone preview may hold one unsaved Blob in memory only while
the page remains open. After an explicitly authorized future upload through a
signed intent, the client would mark upload completion with checksum metadata.

When uploaded audio metadata includes duration and the reviewed transcript has
timestamps, transcript QA warns if the transcript appears to cover too little of
the linked recording.

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/audio/upload \
  -H 'content-type: application/json' \
  -d '{"filename":"session.wav","content_type":"audio/wav","size_bytes":1024,"duration_seconds":120,"sample_rate_hz":16000,"channels":1}'

curl -X POST http://localhost:8000/api/v1/audio/aud_example/complete-upload \
  -H 'content-type: application/json' \
  -d '{"checksum_sha256":"0000000000000000000000000000000000000000000000000000000000000000","size_bytes":1024}'

curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/audio/process \
  -H 'content-type: application/json' \
  -d '{"provider":"manual","draft_text":"THER: what do you see\nCHI: I see car","duration_seconds":120,"sample_rate_hz":16000,"channels":1}'
```

Then run the worker once to create the draft transcript:

```bash
cd apps/api
PYTHONPATH=. python -c "from app.tasks.worker import run_worker; print(run_worker())"
```

Available provider names are `manual`, `whisper`, `faster_whisper`,
`whisperx`, and `batchalign`. The non-manual providers are placeholders until
deployment-specific ASR dependencies and quality gates are configured; without
draft transcript text they fail with `asr_failed` instead of inventing a
transcript.
Completed audio processing jobs include a `status_history` such as `queued`,
`processing`, `transcription_completed`, and `needs_review`. Draft outputs also
surface warnings such as `diarization failed`, `transcript too short`, or
`no child speech detected` so therapists know what to correct before
attestation.

## Evaluate ASR Draft Quality

The ASR harness supports single-pair evaluation and small gold transcript
datasets. Dataset mode expects reviewed transcripts under
`data/evaluation/gold_transcripts/`, ASR draft transcripts with matching file
stems under `data/evaluation/hypothesis_transcripts/`, and optional local audio
sample references under `data/evaluation/audio_samples/`.

```bash
curl -X POST http://localhost:8000/api/v1/evaluation/asr \
  -H 'content-type: application/json' \
  -d '{"reference_text":"*CHI:\tI see car .","hypothesis_text":"*CHI:\tI see a car .","reference_speakers":["CHI"],"hypothesis_speakers":["CHI"],"audio_duration_seconds":10,"transcribed_duration_seconds":8}'

curl -X POST http://localhost:8000/api/v1/evaluation/asr-dataset \
  -H 'content-type: application/json' \
  -d '{"dataset_dir":"data/evaluation"}'
```

ASR quality reports are engineering evidence for whether audio-to-draft-CHA is
usable. They do not validate diagnosis or Thai clinical norms.

## Build ML Dataset And Model Card

The API can build auditable feature rows from local `.cha` files and only runs
baseline metrics when there are enough labeled rows.
Rows include basic language sample features plus review-cue fields such as
unknown speaker ratio, question ratio, and repetition marker count. Binary
baseline output includes accuracy, sensitivity, specificity, ROC-AUC when
available, and a confusion matrix; insufficient labeled data is reported as a
warning rather than a clinical result.

```bash
curl -X POST http://localhost:8000/api/v1/evaluation/ml-dataset \
  -H 'content-type: application/json' \
  -d '{"source_dir":"data/demo","include_unlabeled":true}'

curl -X POST http://localhost:8000/api/v1/evaluation/ml-baseline \
  -H 'content-type: application/json' \
  -d '{"source_dir":"data/demo"}'

curl -X POST http://localhost:8000/api/v1/evaluation/model-card \
  -H 'content-type: application/json' \
  -d '{"source_dir":"data/demo"}'
```

## Docker Compose

```bash
docker compose up
```

Services:

- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`
- worker: mock worker startup
- postgres: future persistence target
- redis: future async queue target

## Local Demo Persistence

The default API runtime uses `JsonFileRepository`. Memory mode is reserved for
isolated tests and intentional demo resets. The frontend uses current-tab
`sessionStorage` only as a UI cache/local fallback; backend data wins whenever
workflow IDs exist. Microphone audio bytes remain memory-only unless explicitly
uploaded. `JsonFileRepository` writes
case, session, transcript, feature, AI-assisted review, report, job, privacy
operation, and audit state to a JSON file on the backend side.

`/api/v1/settings` exposes non-sensitive runtime modes for the clinician UI,
including repository, job queue, and storage mode. API request logging is JSON
structured and records method, path, status, duration, and request ID only; it
does not log transcript text, raw audio, or child identifiers.

Consent withdrawal marks linked therapy goals and audio metadata as not
retained, clears audio object keys in the local repository, and redacts goal
notes when requested. Linked feature artifacts are removed and session feature
pointers are cleared. New sessions, session edits, transcript edits/uploads,
audio upload or processing, feature extraction or reads, AI-assisted review
generation, report edits, sign-off, and exports are blocked after withdrawal.
Queued audio jobs are cancelled if consent is withdrawn before the worker runs.
`THERAPIST_APP_V2_STORAGE_MODE=metadata` is the default metadata-only adapter.
`THERAPIST_APP_V2_STORAGE_MODE=local`
enables a local adapter rooted at `THERAPIST_APP_V2_LOCAL_STORAGE_ROOT` for
development object deletion tests. Production private storage remains
deployment-specific.

## Audit Logs And Roles

Audit logs are available to mock admin users only:

```bash
curl http://localhost:8000/api/v1/audit/logs \
  -H 'x-mock-role: admin'
```

Therapists can create case-scoped privacy operation requests without putting
child identifiers, transcript text, or audio in the request body:

```bash
curl -X POST http://localhost:8000/api/v1/cases/{case_id}/privacy-requests \
  -H 'content-type: application/json' \
  -d '{"operation_type":"case_export","reason":"Guardian requested retained records."}'
```

Admins can review and update the privacy queue:

```bash
curl http://localhost:8000/api/v1/privacy/requests \
  -H 'x-mock-role: admin'

curl -X PATCH http://localhost:8000/api/v1/privacy/requests/{privacy_operation_id} \
  -H 'content-type: application/json' \
  -H 'x-mock-role: admin' \
  -d '{"status":"in_review","admin_note":"Verifying retention policy before export."}'
```

The `x-mock-role` header is a demo boundary, not production authentication.
Pilot deployments still need real identity, role enforcement, and audit review
operations.
In the v2 frontend, Settings opens in therapist scope by default with profile,
organization, sample-data, consent, and owned privacy operations. The admin
scope shows the privacy operation queue with export, consent follow-up, and
deletion-review items plus model, runtime, audit, and pipeline diagnostics.

## PostgreSQL-Ready Schema

`apps/api/app/db/models.py` defines SQLAlchemy models for the v2 clinical
workflow tables, and `apps/api/app/db/migrations/versions/0001_initial_v2_schema.py`
contains the initial Alembic migration. This does not make the MVP a secure
pilot deployment by itself; role enforcement, signed storage, encryption, and
deployment-specific audit hardening still need pilot configuration.

`THERAPIST_APP_V2_REPOSITORY_MODE=sql` activates a SQLAlchemy-backed repository
adapter that persists the current v2 service snapshot to SQL tables. It is a
bridge toward a production repository, not the final audited pilot data layer.

## Demo To A Professor

1. Open `/login` and point out mock mode.
2. Open Today / Work Queue and show review statuses.
3. Open Cases, then `C-1024`, and show consent, timeline, therapy goal
   progress, and before/after comparison.
4. Open Session Workspace and walk through the seven-step review gate.
5. Open `data/demo/demo_manifest.json` and discuss the mock account/case/session
   package, then upload or discuss `data/demo/sample_session.cha`.
6. Show that features and reports are gated by QA and therapist attestation.
7. Open Reports and show limitation text plus sign-off status.

## Known Limitations

The simplified `/results` workflow can generate an ML decision-support draft
from reviewed-transcript feature values. It shows model-informed pattern cues,
editable review suggestions, and explicit confidence/limitations. The therapist
may edit or dismiss the draft, and report generation remains available
regardless of ML state. The UI does not show class predictions, ASD
positive/negative results, diagnostic labels, or probabilities.

Required limitation: “This model is trained on limited/public datasets and is
not clinically validated for diagnosis.”

See `docs/THERAPIST_APP_V2_KNOWN_LIMITATIONS.md`.
