# Therapist App v2 Product Spec

Therapist App v2 is a new case-centered workflow surface at
`apps/therapist-app-v2/` backed by the `apps/api/` FastAPI boundary. It is a
human-in-the-loop clinical decision-support prototype for speech therapists and
clinicians. It does not diagnose ASD, does not claim Thai clinical validation,
and does not replace qualified clinical judgment.

## Product Principles

- Therapist workflow first.
- Clarity over creativity.
- Manual-first transcript workflow.
- Human review before report-eligible interpretation.
- No hidden automation.
- No ASD diagnosis or diagnostic probability language.
- No raw AI output used as final clinical record.
- Every transcript, feature output, AI-Assisted Review Support output, and
  Progress Report shows review status.
- Every AI-assisted output is editable, rejectable, or clearly unavailable.
- Every report includes limitations and clinical safety wording.
- Privacy, consent, sample-data mode, and role boundaries remain visible.

## Primary Persona

The primary user is a speech therapist or clinician who is time-limited, manages
child cases and sessions, reviews transcripts, inspects language sample analysis
features, drafts Progress Reports, and needs AI-assisted review support without
AI diagnosis.

## Canonical Workflow

Therapist App v2 uses the Therapist Five-Step Workflow:

1. Open or create a child case.
2. Add a therapy or assessment session.
3. Upload or enter source material.
4. Review and sign off the transcript.
5. Generate, edit, attest, and export a Progress Report.

Detailed sub-statuses for intake, transcript QA, feature extraction,
AI-Assisted Review Support, report drafting, and sign-off live inside the
Session Workspace. They do not replace the five-step workflow.

## Main Navigation

The main therapist navigation contains only:

- Today / Work Queue
- Cases
- Session Workspace
- Reports
- Settings / Admin

For admin users, Settings may be presented as Admin and include admin-only audit
and runtime tools. Audit logs, Resource Library, AI review, Progress, and
Transcript Review are not ordinary top-level therapist nav items.

Mock login supports therapist and admin role selection. Therapist selection
opens Today / Work Queue. Admin selection may open Settings / Admin in an
admin-scoped view through URL state, but this remains a demo boundary and not
production authentication.

## Today / Work Queue

Today / Work Queue is the default post-login landing view. It organizes work by
what needs attention next:

- transcripts awaiting review or sign-off
- sessions currently processing
- failed processing jobs
- reports awaiting attestation or export
- recent child cases
- follow-up cases

This replaces a dashboard-first mental model.

## Cases

Cases is the child-case list and case-detail entry point. It shows anonymized
child code or nickname, age, language/context where available, consent status,
latest session date, latest session status, latest report status, and Review
Priority.

Case Detail owns cross-session progress: session timeline, descriptive feature
trends, Therapy Goal Progress, before/after comparison, review status across
sessions, and links into Session Workspace and Reports.

Therapy goals are therapist-entered case records. They may appear in Progress
Reports and must be marked withdrawn or unretained when case consent is
withdrawn.

## Session Workspace

Session Workspace is the core working view for one session. It supports source
material intake, transcript review, transcript QA, feature extraction status,
AI-Assisted Review Support, and report readiness.
After feature extraction, the workspace shows therapist-facing feature summary
values such as MLU, TTR, NDW, and question ratio, plus AI review priority and
therapist review status. These are decision-support statuses, not clinical
conclusions.
Feature extraction is unavailable until the current transcript is saved,
reviewed, QA-checked, and therapist-attested. Results are labelled
language-sample cues and include basic utterance, lexical-diversity, question,
unclear-speech, repetition, echolalia, and pronoun-reversal measures. No ML
prediction is produced in this step.

Report Summary combines session metadata, reviewed transcript status, extracted
feature summaries, therapist notes, and therapy goals into an editable draft.
The lifecycle is Draft → Reviewed → Finalized. Finalized reports are read-only.
Markdown is the primary export, HTML is secondary, and PDF remains optional.
Local share statuses do not assert successful delivery.

Supported source paths:

- Upload CHAT Transcript: preferred manual-first source path.
- Paste Transcript Text: converted into a reviewable CHAT draft and marked
  awaiting review.
- Upload or record audio: experimental backend audio-to-CHAT source path that
  produces an ASR-Generated CHAT Draft awaiting therapist review.

The audio path must expose audio quality status and provider provenance. A draft
from any ASR Draft Provider remains blocked from feature extraction until
therapist correction, QA, and attestation.
The simplified browser recording flow currently uses an explicit-upload local
mock processing API to exercise queued, processing, completed, and failed UI
states. Its generated text is workflow-test content, is labelled “Draft
transcript — therapist review required.”, and must not be presented as accurate
ASR output.
Audio processing jobs expose status history through queued, processing,
transcription completed, and needs-review states, plus draft warnings such as
diarization failed, transcript too short, or no child speech detected.
Placeholder ASR providers must fail with a clear ASR failed state rather than
inventing transcript content when no provider output is available.
Any override for failed-QA or unattested transcripts must be explicit, include
a reason, and be available only when runtime debug override mode is enabled.

Audio upload must use backend-managed metadata and signed upload intents rather
than raw audio bytes in frontend state or API JSON payloads. Upload completion
records checksum metadata and leaves object storage behind a backend adapter.
Audio metadata includes duration, sample rate, channels, and quality estimates
when available so transcript QA can warn about low timestamp coverage against
the linked recording.
Corrected CHAT export includes a non-identifying `@Media` header when retained
audio metadata is linked; it must not expose original filenames or storage keys.
Transcript QA warns when language metadata is outside the supported local QA
languages or when mixed Thai/English text appears without matching language
metadata so therapists can document interpretation limits.

Audio processing must be asynchronous from the therapist's perspective: the API
queues a processing job, and a worker produces an unreviewed draft transcript
when processing completes.

ASR quality evaluation uses reviewed gold transcripts and ASR draft transcripts
to measure coverage, speaker accuracy, word/character error rates, and feature
deviation. It is engineering QA for the draft pipeline, not clinical
validation.

Before Transcript Sign-Off, extracted features and AI-assisted outputs may
exist only as preliminary review support. They are not report-eligible.

On Transcript Sign-Off, reviewed feature values and AI-Assisted Review Support
refresh from the signed-off transcript. Refresh failure does not undo Transcript
Sign-Off; the UI shows an unavailable or retry state.

If transcript lines change or the session transcript source is replaced after
sign-off, previous feature and AI-assisted outputs become stale until refreshed
again. Active session links to prior feature sets, AI-assisted review support,
and report drafts are cleared so the old artifacts cannot be used as current
workflow output.

## AI-Assisted Review Support

AI-Assisted Review Support is a contextual section inside Session Workspace and
Reports. It groups:

- Review Priority
- Evidence Review Panel
- Draft Summary

It must not be presented as AI review of the child, automated triage, diagnosis,
or final clinical interpretation.

Therapists must be able to edit or reject AI-Assisted Review Support. Rejected
support is excluded from Progress Report content and retained only as workflow
disposition/audit context.
Stored AI-Assisted Review Support must retain model name, model version, prompt
version, input transcript version, feature set id, feature schema version,
timestamp, and therapist review status.
Any text prepared for external AI use must pass through direct-identifier
sanitization for names, birth dates, phone numbers, emails, addresses, and
clinical or school record identifiers unless a compliant pilot deployment is
explicitly configured.

## Reports

Reports manages Draft Report Previews and Exportable Progress Reports.
Supported draft report types are Session Review Report, Progress Report,
Transcript QA Report, and Research/Model Summary Report. Each draft includes a
report-type focus section plus transcript QA detail, recommended therapist
review, clinical interpretation notes, limitations, therapist sign-off, and
export timestamp state.
The Reports UI must show all four report types and keep Markdown, HTML, and PDF
export actions disabled until therapist sign-off is complete.

Before Transcript Sign-Off, a report may only be a Draft Report Preview and must
withhold guideline-linked interpretation as final report content.

When a case has at least two reviewed sessions with extracted features, report
drafts include a Reviewed Progress Comparison. The comparison is descriptive
and must not claim clinical improvement without therapist interpretation.

After Transcript Sign-Off, the report may become an Exportable Progress Report
if safety wording and report eligibility rules are satisfied.

Before export, the therapist completes Report Attestation confirming they
reviewed and edited the report wording, limitations, and included
decision-support outputs.
The signed report snapshot includes signer, sign-off status, and export
timestamp in the report body.

Supported export modes remain Markdown and Print / Save PDF. HTML may be used
as a browser-rendered report view, but it should not introduce a separate report
type unless the product scope changes.

## Settings And Admin

Settings for therapists and clinicians includes profile, credentials,
organization, sample-data/runtime status, and owned-case privacy operation
requests. The default Settings view is therapist-scoped and does not show model,
debug, audit, or runtime diagnostics.

Admin includes audit logs, privacy operation queues, runtime diagnostics, and
local development reset controls. Admin tools are role-scoped and not part of
the ordinary therapist workflow.
Privacy operation requests cover case export, consent withdrawal follow-up, and
deletion review. They are auditable workflow records, not automatic deletion or
export actions, and must not contain child identifiers, transcript text, or raw
audio.
The frontend must show owned privacy requests in therapist scope and the full
privacy operation queue only in admin scope.

## Runtime Mode

Mock Mode / Local Clinician Workspace remains the default runtime for the v2
MVP so the therapist workflow is immediately usable for advisor and demo review.
Backend/API and Supabase pilot modes remain opt-in through environment
configuration.

Local backend demo persistence may use backend-side JSON storage for advisor
review. Current-tab `sessionStorage` may retain the active simplified workflow
for refresh recovery in local/demo mode, but it must not be treated as secure
clinical persistence or used with real identifiers, sensitive transcripts, or
audio bytes. Browser microphone capture may retain one unsaved audio Blob in
memory only for the current page lifecycle, with object URLs revoked on delete,
replacement, or unmount. Refresh clears that Blob. Local audio storage may be
used only as a development adapter behind signed-intent metadata and an
explicit user-authorized upload action.
The local demo package must include a manifest that links mock therapist/admin
accounts, anonymized cases, demo sessions, the sample `.cha`, and the sample
report without direct identifiers, raw audio, or storage keys.

SQL-backed persistence is allowed for local or pilot scaffolding only when the
deployment also defines authentication, role boundaries, consent enforcement,
storage deletion behavior, audit review, and backup procedures.

The sample-data/runtime banner must stay prominent. Every source-material path
should make clear whether the user is in sample/local, backend, or secure pilot
mode.

## Secondary Surfaces

The public screening app and presentation dashboard are supplementary. They
should receive safety wording, consistency, and broken-demo fixes, but they
should not distract from therapist workflow implementation unless scope changes.

## Research Baseline Boundary

The ML baseline is an explainable research support path, not a therapist-facing
diagnosis feature. Dataset builder output must report feature rows, class
distribution, missing metadata, and insufficient-data warnings. Binary baseline
metrics may include accuracy, sensitivity, specificity, ROC-AUC, and confusion
matrix when enough labeled data exists, but the app must only use those results
for review priority, contributing feature explanation, cohort similarity, or
research summaries.

## Structured AI Assistance

AI-assisted review support is stored as therapist-editable decision support
with five named areas: Transcript QA Assistant, Feature Explanation Assistant,
Review Priority, Progress Summary, and Report Drafting. The output must explain
QA status, MLU, TTR, NDW, unintelligibility, question ratio, review-priority
factors, progress uncertainty, and report limitations without presenting a
diagnosis or raw model probability. Every AI-assisted record retains model,
prompt, transcript-version, feature-set, feature-schema, timestamp, and
therapist review status metadata.

## Implementation Sequence

## ML Decision-Support Draft

After reviewed-transcript feature extraction, `/results` may request a
model-informed decision-support draft. The output is limited to pattern cues,
therapist-editable review suggestions, and confidence/limitations. The
therapist can edit or dismiss every generated suggestion.

The ML draft must not change report eligibility, create a clinical conclusion,
advance report status, or finalize a report. It must not display class
predictions, positive/negative results, diagnostic labels, or raw
probabilities.

The interface must include: “This model is trained on limited/public datasets
and is not clinically validated for diagnosis.”

Start v2 implementation with a parallel MVP:

1. Create `apps/api/` with mock repository mode, service boundaries, and the
   case/session/transcript/features/AI-review/report/consent routes.
2. Create `apps/therapist-app-v2/` with Next.js App Router, TypeScript,
   Tailwind CSS, accessible components, and a calm clinical interface.
3. Make Today / Work Queue the post-login landing view.
4. Limit main navigation to Today / Work Queue, Cases, Session Workspace,
   Reports, and Settings / Admin.
5. Build the Session Workspace around intake, transcript review, attestation,
   feature extraction, AI-Assisted Review Support, report draft, and therapist
   sign-off.
6. Add tests and search gates for feature extraction blocking, report sign-off
   blocking, restricted current-tab browser persistence, and forbidden
   diagnosis wording.
