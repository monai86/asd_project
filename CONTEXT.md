# Project Glossary

This file defines shared project language only. It is not an implementation
specification.

## Screening risk estimate

A model-generated probability or category used to support ASD screening review.
It must be interpreted with transcript quality, developmental history, and
professional judgment. It is not an ASD diagnosis.

## Screening Support Score

A user-facing form of a screening risk estimate in the speech therapist
prototype. It is clinical decision support only and must not be presented as a
diagnostic score.

## Reference Cohort Label

A training or evaluation label that identifies the source cohort group for a
transcript, such as ASD, TD, or DD. It may support internal model evaluation and
reference comparison, but it must not be presented as a clinical diagnosis for
an uploaded transcript.
_Avoid_: diagnosis label, AI diagnosis, detected disorder

## Training-Ready Reference Dataset

A curated set of transcripts and metadata with reviewable reference cohort
labels, participant grouping, and sufficient quality for model development or
evaluation. It is not a clinical validation dataset unless separately evaluated
for that intended use.
_Avoid_: diagnosis dataset, validated clinical dataset

## Group-Based Evaluation Split

A train/test or cross-validation boundary that keeps all sessions from the same
child or participant on one side of the evaluation split. It prevents repeated
sessions from making model performance look stronger than it is.
_Avoid_: random session split, file-level validation split

## Runtime Model Artifact

The model bundle and schema files that the application loads for decision
support at runtime. It is the source of truth for inference behavior and should
stay aligned with the canonical feature schema and model card.
_Avoid_: sample model copy, export-only model file

## Compatibility Model Export

A secondary model file or folder created to satisfy an external deliverable,
handoff, or documentation convention. It must point back to the runtime model
artifact and must not create a separate clinical behavior.
_Avoid_: second production model, alternate diagnosis model

## Interpretable Runtime Model

The model selected for clinical decision-support runtime because its behavior
can be explained and reviewed alongside transcript features. It may be chosen
over a more complex benchmark model when performance is similar.
_Avoid_: black-box default model, highest-AUC-only model

## Optional Benchmark Model

A model candidate used to compare performance during experimentation when its
dependencies are available. It does not become the runtime model unless it is
explicitly selected and documented with safety, calibration, and interpretability
trade-offs.
_Avoid_: required clinical model, automatic production model

## Reference Cohort Similarity

A decision-support output describing which reference cohort label an uploaded
transcript's feature pattern most resembles. It is a statistical comparison for
clinical review, not a diagnosis or diagnostic probability.
_Avoid_: ASD probability, diagnosis probability, predicted diagnosis

## Reference Cohort Probability

An internal model value estimating how strongly a transcript feature pattern
maps to each reference cohort label. It may be stored for audit, calibration,
and evaluation, but user-facing surfaces must present it as reference cohort
similarity rather than diagnostic probability.
_Avoid_: ASD risk probability, probability of autism, diagnostic probability

## Reference Cohort Similarity Output

A stored decision-support output whose purpose is to present reference cohort
similarity for a session. It may reuse the existing AI screening output record
shape, but its meaning is cohort similarity rather than diagnostic screening.
_Avoid_: diagnosis output, ASD classifier result

## Existing Output Record Shape

The current prototype record shape used to store AI decision-support outputs
and related model run metadata. It may be extended with reference cohort
similarity fields before a separate database table is justified.
_Avoid_: new production table, separate diagnosis record

## Report Eligibility

Whether a decision-support output is allowed to appear in exported or
therapist-facing reports. Preliminary outputs are not report eligible; reviewed
outputs may become report eligible when transcript review and safety wording
requirements are satisfied.
_Avoid_: export by default, preliminary report result

## Reviewed-Only Report Output

A report rule that includes reference cohort similarity only when the output is
reviewed and report eligible. Preliminary similarity may remain in workflow or
audit data, but it must not be used as a report result.
_Avoid_: preliminary report output, triage score in report

## Preliminary Reference Cohort Similarity

A reference cohort similarity output computed from an unreviewed or ASR-derived
transcript. It may help prioritize therapist review, but it must be clearly
marked as preliminary and must not be exported as a reviewed clinical result.
_Avoid_: final AI result, official score, report-ready prediction

## Reviewed Reference Cohort Similarity

A reference cohort similarity output computed after transcript line review and
sign-off. It may be included in therapist-facing reports as clinical decision
support when accompanied by safety wording and transcript quality context.
_Avoid_: confirmed diagnosis, diagnostic result, ASD determination

## Reviewed Similarity Refresh

The automatic post-sign-off workflow that recomputes clinical speech features
and reviewed reference cohort similarity from reviewed transcript lines. It
does not create or export a progress report by itself.
_Avoid_: automatic report generation, auto-diagnosis

## Similarity Unavailable State

A recorded state indicating that reference cohort similarity could not be
computed because of missing artifacts, schema mismatch, insufficient transcript
quality, or another processing failure. It preserves auditability and recovery
without blocking transcript sign-off.
_Avoid_: negative result, low-risk result, successful similarity output

## Feature Summary

A therapist-facing view of extracted speech-language feature values from the
shared project schema. It supports review and interpretation but does not by
itself establish clinical meaning.

## Canonical Feature Schema

The stable set of feature names and meanings used to compare transcripts,
train models, run inference, and keep reports consistent. New display labels or
derived names should map back to this schema to avoid changing clinical meaning
across surfaces.
_Avoid_: ad hoc feature list, UI-only feature schema

## Feature Alias

A reader-friendly or task-specific display name for a canonical feature. It may
help therapists understand an output, but it must preserve the canonical
feature's meaning and must not create a separate model input by accident.
_Avoid_: duplicate feature, replacement feature name

## Evidence Review Panel

A decision-support panel that lists the feature-level reasons or contextual
evidence a clinical user should review. It is not an automated conclusion.

## Progress Report

A therapist-facing artifact that summarizes descriptive changes across
sessions, therapy goals, transcript review status, and decision-support
outputs. It supports clinical review and caregiver communication but is not an
ASD diagnosis.

## Safe Thai Summary

A clinician-reviewed, bilingual summary section in the Progress Report containing templated developmental trend estimates in Thai (such as MLU or TTR progress), designed for caregiver sharing and therapist annotation. It enforces human-in-the-loop review by allowing the therapist to edit or override any automated estimates, and strictly excludes diagnostic or validation claims.
_Avoid_: diagnostic report summary, automated conclusion summary


## Thai Word Mean Length of Utterance (MLU-w)

A descriptive linguistic feature measuring the average number of Thai words per child utterance, calculated using a Thai word segmenter.
_Avoid_: Thai MLU, word MLU


## Thai Syllable Mean Length of Utterance (MLU-s)

A descriptive linguistic feature measuring the average number of syllables per child utterance in Thai, serving as a stable clinical indicator for developmental progress tracking.
_Avoid_: syllable length, child MLU-s


## Therapy Goal Progress

The status of therapist-entered goals for a child case, such as active,
paused, or completed. It reflects clinical workflow tracking and must not be
treated as an AI-determined outcome.

## Before/After Radar

A visual comparison of selected speech-language feature values from an earlier
session and a later session. It is descriptive progress tracking only and does
not establish clinical improvement by itself.

## Clinical decision support

Information that helps a speech-language therapist, clinician, advisor, or
trained reviewer inspect patterns and decide what should be reviewed next. It
does not replace clinical assessment.

## Clinical Safety Wording

User-facing language that clearly presents automated outputs as reviewable
clinical decision support rather than diagnosis, diagnostic certainty, or
clinical validation. It must avoid implying that speech-language features alone
can determine ASD status.
_Avoid_: diagnostic feature, AI diagnosis, automatic ASD finding

## Clinical Workflow Complete

A delivery milestone where reference cohort similarity is correctly gated,
stored, audited, and report-controlled inside the therapist workflow. It
prioritizes safe preliminary/reviewed behavior over research-grade training
experimentation.
_Avoid_: model fully validated, research pipeline complete

## Human-in-the-loop

A workflow boundary where a qualified human reviewer checks transcript quality,
speaker labels, low-confidence segments, and safety wording before interpreting
or exporting a screening risk estimate.

## Thai validation

External evaluation on Thai child speech or Thai clinical data with appropriate
consent, governance, and reference standards. The current English-speaking
TalkBank/ASDBank evaluation is not Thai validation.

## Thai ASR Drift Simulation

A synthetic mock-data exercise that estimates how ASR word error rate could
shift descriptive speech-language features such as MLU, TTR, and echolalia
ratio before real Thai validation data are collected. It is planning support,
not Thai validation or clinical validation.
_Avoid_: Thai validation result, Thai child validation dataset

## Clinical Validation

Evidence that a tool has been evaluated for a specific clinical population,
setting, language, and intended use with appropriate reference standards and
governance. The current prototype is not clinically validated.

## Acoustic profile

Descriptive audio measurements such as pitch, voiced ratio, pause ratio, and
speech rate from an uploaded recording. In this project cycle, acoustic profile
values are not classifier inputs and do not support accuracy claims.

## Context-Only Acoustic Indicator

An acoustic profile value shown to help interpret recording quality,
interaction timing, or review context. It must not change reference cohort
similarity outputs unless a separate validated acoustic model decision is made.
_Avoid_: acoustic classifier input, acoustic diagnosis marker

## Research-gap support

Paper discovery, screening, and Zotero import workflows used to understand the
field and identify future development directions. These tools are not core
clinical/demo features of the prototype.

## Clinical User

A therapist, clinician, or admin who can enter the speech therapist prototype. Therapist
and clinician are equivalent case-owning roles; admin is a demo/testing role
with cross-case visibility.

## Case Owner

The clinical user responsible for a child case. Each child case has exactly one
case owner unless an admin is viewing across owners for testing/demo purposes.

## Child Case

An anonymized record for one child being reviewed or tracked by a clinical user.
It must not contain the child's real name or direct identifiers.

## External Clinical Status

Therapist-entered context about information recorded outside the system. It is
not generated by the model and is separate from any screening risk estimate.
_Avoid_: diagnosis status, AI diagnosis

## Mock Mode

A clearly labeled demonstration mode using seeded clinical users, anonymized
child cases, and seeded workflow records. Mock mode must not be silently mixed
with real uploaded data or real clinical records.

## Sample Data Mode

A visible UI state indicating that mock, local development, or placeholder
runtime boundaries are active. When sample data mode is visible, no real child
identifiers or clinical source media should be entered.
_Avoid_: pilot mode, production mode

## Cross-Platform Clinical App

The shared therapist/clinician product experience when the same clinical
workflow is delivered through web and iOS surfaces. It must preserve the same
sample-data, consent, ownership, and clinical decision-support boundaries on
every surface.
_Avoid_: native rewrite, mobile demo

## Native Clinical Shell

An iOS-native container around the shared clinical workspace that handles
launch, safe-area, offline, and system-status presentation. It is not a
separate clinical workflow or a SwiftUI rewrite of child case, transcript, or
reporting features.
_Avoid_: native clinical workflow, SwiftUI rewrite, mobile-only app

## Supabase Anonymized Pilot

A pilot runtime where authenticated clinical users work with anonymized child
case records through Supabase Auth, Row Level Security, and private storage.
It is not permission to store direct child identifiers or diagnostic claims.
_Avoid_: production clinic database, real child record mode

## Signed Upload Intent

A consent-gated authorization to upload one clinical media object to private
storage for a limited time. It is not a permanent storage path and must not
expose the private object key to the browser.
_Avoid_: direct storage key, public upload URL

## Data Mode

The active persistence mode for the speech therapist prototype: mock,
browser localStorage, database placeholder, backend API, or Supabase pilot.
It identifies where workflow records are read and written without changing the
clinical meaning of the records.

## API Repository

The backend-backed persistence boundary for clinical workflow records such as
child cases, sessions, consent records, reports, and audit history. It is the
intended product source of truth when the app leaves mock or browser-only data
mode.
_Avoid_: localStorage repository, database placeholder

## Consent Record

A dated record that captures guardian or authorized consent evidence for a
child case, including what processing is permitted and whether the consent has
expired or been withdrawn. It is separate from a child case's summary consent
status.
_Avoid_: consent flag, permission checkbox

## Privacy Operation

An auditable request to export case records, withdraw consent, or review
deletion for a child case. It is a workflow request, not automatic data erasure.
_Avoid_: hard delete, purge button

## Auth Mode

The active authentication boundary for the speech therapist prototype: mock
sample-account sign-in or provider placeholder. It controls how a clinical
user enters the workspace but does not change case ownership rules.

## Auth Session

A remembered sign-in state for one clinical user in one browser session. It
may restore the clinical user after refresh, but it does not grant access unless
case ownership and role rules still allow the requested record.
_Avoid_: account, permanent identity

## Local Dev Auth

A development-only authentication path that talks to the pilot backend while
preserving the same clinical user roles and ownership rules as production auth.
It is not a production identity provider.
_Avoid_: production login, real clinic SSO

## Speech Therapist Prototype

The logged-in prototype area where speech therapists or clinicians manage
anonymized cases, review workflow queues, and inspect progress over time. It is
clinical decision support, not an automated diagnostic workspace.

## Session Timeline

The chronological view of clinical sessions attached to a child case. It helps
a clinical user inspect progress and review status over time; it is not a
clinical conclusion by itself.

## Therapist Note

A clinical user's free-text note attached to a child case or a specific
session. It should contain professional context only and must not include real
child identifiers in mock mode.

## Audio File Metadata

A mock or database-ready record describing an uploaded audio or video file by
IDs, filename, type, size, upload time, owner, case, session, and processing
status. It is not the stored file content itself.

## File Storage Mode

The active file handling boundary for uploaded audio or video in the speech
therapist prototype. It distinguishes metadata-only records, temporary browser
preview, and future backend storage without changing the clinical meaning of
the audio file metadata.

## File Object

A private backend record for stored audio or video bytes attached to an audio
file metadata record. Its permanent storage key is backend-only and must not be
shown to the browser.
_Avoid_: uploaded file, browser file path

## Signed Upload Intent

A short-lived permission for the browser to upload one approved audio or video
file to private storage after consent and ownership checks pass. It is not a
stored clinical record by itself.
_Avoid_: storage key, public upload URL

## Native Secure Media Upload

An iOS or device-assisted upload flow that still requires the same consent and
ownership checks as the web secure upload flow. It is a secure media handling
path, not a bypass around clinical upload governance.
_Avoid_: direct device upload, local recording storage

## Clinical Uploads Namespace

A strictly isolated directory path boundary (e.g., `data/uploads`) and validation check that resolves and validates all client-requested file upload and retrieval paths to prevent directory traversal outside the uploads root.
_Avoid_: public bucket path, raw mirror folder

## CHAT Transcript

A transcript in CHAT `.cha` style that can be reviewed by a clinical user and
used later for feature extraction. A CHAT transcript may be uploaded, selected,
or generated by a future audio pipeline, but it must be reviewed before
clinical interpretation.

## Reviewed CHAT Export

A CHAT `.cha` artifact rebuilt from reviewed transcript lines for CLAN,
Batchalign, or downstream language-sample analysis. It reflects clinician
line-level corrections and must not be regenerated from an older raw transcript
snapshot when reviewed lines exist.
_Avoid_: raw transcript export, regenerated ASR transcript

## Line-First CHAT Export

The export rule that reviewed CHAT files are generated from transcript lines as
the primary input. Raw CHAT text may support import or migration, but it is not
the post-review export source when reviewed transcript lines exist.
_Avoid_: transcript-text-first export

## Session CHAT Export

A session-scoped download of the current CHAT transcript for clinical review or
CLAN-compatible language-sample analysis. It normally requires transcript
review sign-off; preliminary exports must be explicitly labeled as requiring
clinician review.
_Avoid_: arbitrary transcript dump, hidden preliminary export

## TalkBank Raw Mirror

A private local copy of TalkBank corpus files kept for audit and repeatable
research processing. It is separate from clinical user uploads and must not be
shown as public app content.
_Avoid_: user upload, public dataset folder

## Corpus Manifest

A tabular audit record describing which corpus files were observed, copied,
checked, or excluded during research data intake. It is evidence about corpus
handling, not a clinical record.
_Avoid_: patient record, transcript review

## Reference Cohort

A reviewed group of transcripts or derived feature rows used as a comparison
context for descriptive screening support. It must be matched by age, task,
language, and corpus limitations before interpretation.
_Avoid_: diagnostic norm, ground truth diagnosis

## Corpus Task Type

The canonical activity label used to match TalkBank-derived Reference Cohorts,
such as `toyplay`, `narrative`, or `picture_description`. Labels are normalized
from official corpus metadata and headers; they must not be inferred from model
output or user-facing prose.
_Avoid_: task guess, model-inferred activity

## Reference Comparison

A descriptive comparison of one extracted feature set against matched
Reference Cohorts. It summarizes cohort position and uncertainty context but is
not a screening risk estimate, diagnosis, diagnostic norm, or validated
clinical benchmark.
_Avoid_: reference score, diagnostic benchmark, norm

## Reference Similarity Retrieval

A descriptive matching process that finds the top K (specifically 5) most similar Reference Cohort feature rows using min-max scaled Euclidean distance calculated within the matching cohort slice. It provides descriptive comparative context without making diagnostic claims or screening determinations.
_Avoid_: diagnostic similarity search, normative match

## Reference Cohort Coverage Report

A research readiness summary showing which Reference Cohort slices have enough
derived feature rows, cohort summaries, and CLAN-Derived Metrics for cautious
descriptive comparison. It guides data intake and confidence labeling; it is
not a clinical conclusion.
_Avoid_: clinical result, model performance report

## Reference Readiness Index

A descriptive metadata summary index showing the readiness, low-count caution, or unavailable status for Reference Cohort cells. It supports therapist app visibility into cohort readiness without containing raw transcripts or diagnostic claims.
_Avoid_: validation status, diagnostic norms index

## Low-count Reference Cell

A Reference Cohort slice below the project's minimum row threshold for normal
confidence labeling. It remains visible as research context but should be
kept separate from cohort-ready comparison output and must not be interpreted
as clinical validation, model performance, or evidence that a child belongs to
that group.
_Avoid_: weak diagnosis cell, failed model cell

## Policy-Exhausted Reference Cell

A Low-count Reference Cell where the local source corpus has no additional
analysis-ready rows under the current Reference Cohort eligibility policy. The
raw corpus may still contain excluded material such as short samples, so this
term must not imply that the corpus itself has no remaining files.
_Avoid_: exhausted corpus, complete norm, source depleted

## ASD Add-on Candidate Matrix

A research intake decision table used to compare possible ASDBank English
corpora against unresolved ASD Reference Cohort gaps, access limits, task fit,
and corpus warnings before any new raw download. It is not a clinical
validation table, diagnostic norm, model benchmark, or permission to publish
raw TalkBank content.
_Avoid_: ASD validation matrix, diagnostic corpus ranking, download approval

## ASD Add-on Review Gate

A research intake checkpoint that combines the ASD Add-on Candidate Matrix,
Reference Cohort coverage, and source-exhaustion audit results to decide
whether a possible ASDBank addition should be reviewed further, kept blocked,
or treated as a manual download candidate. It is not a login workflow,
clinical validation, or automatic permission to download restricted data.
_Avoid_: automatic download gate, ASD validation approval, access bypass

## AAC Access and Task Review

A research intake check for ASDBank AAC corpus access eligibility, task fit,
and modality boundaries before any Reference Cohort intake. It can identify a
separate AAC-focused task candidate but is not access approval, clinical
validation, or permission to merge AAC samples into toyplay Reference Cohorts.
_Avoid_: AAC download approval, AAC validation, toyplay shortcut

## Official Corpus Refresh Review

A research intake check that compares a corpus page's currently published
transcript count or release statement with the local TalkBank Raw Mirror and
derived Reference Cohort artifacts. It can support a manual download decision
but is not a login workflow, access approval, or clinical-readiness claim.
_Avoid_: automatic corpus update, access approval, validation refresh

## CLAN-Derived Metric

A descriptive metric produced by CLAN from a CHAT transcript or transcript
batch. It can support research feature review but is not clinical truth,
diagnosis, diagnostic norm, validated benchmark, or clinical validation by
itself.
_Avoid_: diagnostic metric, clinical benchmark, ground truth

## Preliminary CLAN Output

A CLAN-derived output produced before transcript review sign-off. It can help a
clinician inspect transcript quality or language-sample patterns, but it must
remain labeled as preliminary and requires clinician review before clinical
interpretation.
_Avoid_: final CLAN metric, signed-off language result

## Structured CLAN Run

A clinician-requested CLAN operation represented as a constrained command
choice, target participant, language, and command-specific parameters. It is
not a raw shell command and must remain auditable and review-gated.
_Avoid_: free-form CLAN command, shell command input

## Parsed CLAN Metric

A structured value extracted from CLAN output only when the parser can identify
the value conservatively. Ambiguous CLAN output remains raw reviewable output
rather than being guessed into a metric.
_Avoid_: inferred CLAN metric, guessed language score

## Transcript Line

One speaker tier line within a CHAT transcript, including the speaker code,
speaker role, original utterance text, clinician-reviewed text when present,
timing evidence when available, and therapist review state. A transcript line
belongs to exactly one CHAT transcript and is the canonical review record.
_Avoid_: utterance when referring to the persisted review record, ASR segment

## Speaker Role

The project-level clinical role mapped from a CHAT speaker code, such as
child, therapist, parent, family, or other. It is separate from the CHAT
speaker code because CLAN requires canonical codes while clinical review and
turn-taking summaries need stable role categories.
_Avoid_: speaker code, participant label

## Media Time Mark

A millisecond start/end range attached to a transcript line and rendered into
CHAT media bullet notation in reviewed exports. It is timing evidence for
audio review and CLAN alignment, not a clinical interpretation.
_Avoid_: display timestamp, session clock label

## Line Version

The edit currency for one transcript line during therapist review. It protects
against silently overwriting another reviewer or browser session's correction.
_Avoid_: save counter, row number

## Transcript QA

A quality review of a CHAT transcript that flags structural, speaker-label,
confidence, and language-tag issues before feature extraction or screening
support interpretation.

## Clinical Review Flag

A transcript-line marker that asks a therapist or clinician to inspect the
line before interpretation. Examples include unintelligible markers,
nonverbal vocalization markers, repetition markers, possible pronoun reversal
patterns, child questions, and zero spoken response markers. A clinical review
flag is not a clinical conclusion.

## Review Flag Disposition

The clinician's handling of a transcript-line or feature-output review flag,
such as accepted as relevant, rejected as not relevant, or left for more
context. It is not approval of an ASD marker or diagnostic finding.
_Avoid_: diagnosis approval, marker confirmation

## Preliminary Feature Output

Extracted speech-language feature values produced before a transcript has been
reviewed and signed off by a qualified clinical user. Preliminary feature
output can guide review priority but should not be interpreted as finalized
screening support.

## Clinical Speech Feature Output

Extracted speech-language values derived from reviewed transcript lines for a
session. It separates stable core features used for progress tracking from
optional indicators and review flags, and it remains clinical decision support
rather than an ASD diagnosis.
_Avoid_: diagnostic feature output, automated ASD markers

## Clinical Speech Pipeline

The backend boundary that turns reviewed transcript lines into reviewed CHAT
exports, clinical speech feature outputs, and optional CLAN-derived outputs. It
is separate from the audio pipeline that creates an initial transcript from
media.
_Avoid_: audio pipeline, browser feature extraction

## Core Feature Set

The fixed speech-language feature set used for screening-support and progress
tracking comparisons. It is separate from optional indicators so longitudinal
trends do not change meaning when extra context markers are added.
_Avoid_: all features, optional metrics

## Optional Indicator

A descriptive context marker that can support therapist review without being
part of the fixed core feature set. Examples include turn-taking, pause timing,
adult utterance counts, and restricted-interest word count.
_Avoid_: core feature, model input by default

## AI Decision-Support Output

A therapist-facing screening-support artifact that summarizes a score,
concern label, contributing features, evidence items, and plain-language
clinical-safety wording. It is not a diagnosis.
_Avoid_: AI diagnosis, final result

## Stale Feature Output

Extracted speech-language feature values that no longer match the current
reviewed transcript because transcript content changed after extraction. Stale
feature output must be rerun before clinical interpretation.
_Avoid_: outdated score, final feature result

## Audio-to-CHAT Boundary

The workflow boundary between uploaded audio or video and a CHAT transcript.
In mock phases, audio file metadata can exist without stored file content, so
real audio-to-CHAT execution is deferred.

## Backend Audio Processing Boundary

The boundary between the browser-based speech therapist prototype and a future
server-side service that can run ASR, diarization, CHAT formatting, transcript
QA, and feature extraction. Browser code must not run Whisper or Python audio
pipeline logic directly.

## Processing Job

An auditable backend work item for transforming an approved audio file into
review-gated clinical artifacts such as a CHAT transcript, QA result, feature
output, and screening support output. A processing job belongs to exactly one
session and one case owner.
_Avoid_: transcription task, background process

## Processing Stage

The current pipeline step inside a processing job, such as transcribing,
diarizing, CHAT formatting, QA, feature extraction, or awaiting review. It is
more specific than the processing job status.
_Avoid_: processing status

## Audio-to-CHAT Worker

A backend worker that runs the audio pipeline and produces a CHAT transcript
for human review. It is not browser code and does not finalize clinical
interpretation.
_Avoid_: browser ASR, final transcript generator

## Audio-to-CHAT Engine

The backend processing engine selected by an Audio-to-CHAT Worker, such as the
project's local Whisper pipeline or an explicitly enabled Batchalign2 backend.
It is not a browser capability and must preserve the same consent, privacy,
and review boundaries regardless of engine.
_Avoid_: frontend transcription mode, diagnostic engine

## Local-Only Speech Processing

The default privacy posture for clinical audio and transcript processing:
audio remains within approved local or clinic-controlled infrastructure unless
a separate consent, policy, and configuration decision explicitly permits an
external provider.
_Avoid_: default cloud ASR, silent third-party processing

## Clinical Speech Artifact

A generated or imported speech-processing output attached to a clinical
session, such as a CHAT export, Batchalign output, CLAN output, parsed CLAN
metrics, or speech-language feature output. It provides reviewable provenance
and downstream analysis context, but it is not the clinician-reviewed
transcript source of truth.
_Avoid_: transcript line, clinical conclusion, diagnostic output

## Artifact Freshness

Whether a clinical speech artifact still matches the reviewed transcript
source it was generated from. An artifact can be current, preliminary, stale,
failed, or superseded, and stale artifacts must not be presented as the latest
reviewed result.
_Avoid_: latest file, final output

## Structured Processing Run

An auditable invocation of an optional local processing tool using a
system-defined operation and constrained parameters. It is not a raw shell
command and must not allow clinicians or browser clients to submit arbitrary
subprocess arguments.
_Avoid_: shell command, custom command string

## Batchalign Artifact

A raw or generated file produced by a Batchalign2 audio-to-CHAT, alignment, or
morphotagging run. Batchalign artifacts provide provenance and optional
downstream analysis context, but clinician-editable transcript lines remain
the clinical review source.
_Avoid_: reviewed transcript line, finalized clinical transcript

## Processing Dependency Check

A backend preflight check that reports whether an optional local processing
tool such as Batchalign2, FFmpeg, or CLAN is enabled and available before a
clinical processing job runs. It returns setup guidance instead of installing
tools or failing with an unhandled subprocess error.
_Avoid_: automatic installer, silent dependency failure

## Public Screening Support Web App

The public-facing web app for parents, caregivers, students, or general users.
It supports preliminary reflection and preparation for professional
consultation, not diagnosis or clinical decision-making.

## Advisor Dashboard

The dashboard or slide-style surface used to explain the whole project to an
advisor or non-technical audience. It connects data, features, model trust,
workflow, safety limits, and next steps.

## Full Clinical Product

The intended product form of the speech therapist prototype after it gains real
authentication, case ownership, consent, secure storage, review gates, audit
history, and deployment readiness. It remains clinical decision support and is
not a diagnostic product.
_Avoid_: full diagnosis product, production diagnosis tool

## Clinical Command Interface

A therapist-facing interface style that prioritizes dense clinical workflow,
review queues, status visibility, consent state, and safety cues over marketing
or caregiver education presentation. It is the product interface stance for
clinical users, not a claim of clinical validation.
_Avoid_: marketing dashboard, generic SaaS dashboard
