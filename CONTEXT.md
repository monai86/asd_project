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

## Review Priority

A simplified therapist-facing label for how urgently a session or output should
be reviewed in context. It may be informed by a Screening Support Score, but it
must not be presented as a diagnosis, probability of ASD, or final clinical
conclusion.
_Avoid_: ASD probability, diagnostic priority, automated triage result

## Session Workspace

The therapist-facing work area for one therapy or assessment session. It groups
intake, transcript review, attestation, feature extraction, AI-Assisted Review
Support, report drafting, and sign-off without making those steps independent
top-level products.
_Avoid_: model dashboard, diagnosis workspace, research console

## Workflow Locator

The backend case, session, transcript, and report identifiers carried by a
workflow route so the therapist can refresh or reopen the same persisted work.
_Avoid_: browser session state, local workflow ID, page-only state

## ASR-Generated CHAT Draft

A transcript draft produced from audio automation that must be corrected and
attested by a therapist before it can support report-eligible features or
clinical decision-support summaries.
_Avoid_: final transcript, automatic clinical transcript, ready transcript

## ASR Draft Provider

A replaceable source of draft transcript text from audio or manual fallback
input. Its output is always an unreviewed draft until a therapist corrects
speaker labels, transcript text, and quality concerns.
_Avoid_: production transcription authority, automatic child speaker detector

## ASR Gold Dataset

A small engineering QA set that pairs therapist-reviewed gold transcripts with
ASR-generated draft transcripts to measure coverage, speaker labels, error
rates, and feature deviation. It evaluates the audio-to-draft workflow, not a
child, diagnosis, clinical norm, or deployment-ready model.
_Avoid_: clinical validation dataset, diagnostic benchmark, Thai norm set

## Clinical Repository Mode

The backend storage mode used by the lingualens API for demo, local
persistence, or future pilot storage. It describes where workflow state lives,
not the clinical status of a case or report.
_Avoid_: browser storage mode, clinical readiness mode, validation mode

## Transcript Quality Attestation

The therapist's confirmation that a transcript has enough reviewed quality to
serve as the source for feature extraction and report-eligible interpretation.
It is a clinical workflow gate, not an automated parser result.
_Avoid_: automatic QA pass, model approval, report sign-off

## Debug Feature Override

A local engineering-only permission to extract features from a failed-QA or
unattested transcript when runtime debug override mode is enabled and a reason
is recorded. It must not be used for ordinary therapist workflow, report
eligibility, or pilot clinical records.
_Avoid_: therapist bypass, clinical override, silent feature extraction

## Transcript Coverage Warning

A transcript QA warning that compares reviewed transcript timestamps with known
audio duration metadata and flags when the transcript appears to cover too
little of the linked recording. It asks for therapist review of source
completeness, not a clinical conclusion.
_Avoid_: failed session, invalid child sample, diagnostic quality result

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

## Research Model Result

A model training, evaluation, or performance result used to explain the research
component of the project. It is separate from therapist-facing clinical
decision support and must not be presented as clinical validation.
_Avoid_: clinical validation result, deployed diagnostic model result

## Research Baseline Boundary

The product boundary that keeps explainable ML baseline datasets, metrics, and
model cards in research support rather than therapist-facing diagnosis. It may
support review priority, contributing feature explanation, cohort similarity, or
research summaries, but never automated diagnosis or clinical validation claims.
_Avoid_: diagnostic model boundary, validated clinical classifier

## Advisor-Readiness Release

A project release focused on defensible scope, therapist usability, report
safety, and guideline-linked interpretation for academic/advisor review. The
v1.6.3 release is the current maintained Advisor-Readiness Release.
_Avoid_: production clinical release, validated deployment release

## Demo User

A user path for exploring the therapist workflow with anonymized sample data
derived from public research corpora. It must not be used for real child cases,
clinical persistence, or private media.
_Avoid_: pilot user, production account, real clinic user

## Real User

An authenticated clinician or therapist account intended for real case workflow
use when the deployment is configured for secure persistence, storage, consent,
and audit boundaries.
_Avoid_: demo account, sample user, mock therapist

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

## Pilot Access Lifecycle

The local advisor-facing admin workflow for exercising invitation records, active organization membership state, and membership revocation against backend guards. It is not real production account provisioning, MFA enrollment, invitation delivery, or Supabase custom-claim synchronization.
_Avoid_: production onboarding, real clinic account setup, public signup, clinic launch admin

## Invitation-Only Onboarding

The production access path where a Real User can enter a tenant only after an organization-controlled invitation has been issued and accepted. It excludes self-service registration and is separate from the local Pilot Access Lifecycle.
_Avoid_: public signup, self-service signup, open registration, pilot access lifecycle

## Active Organization Session

The single organization context attached to a Real User's current authenticated session. At launch, a user may belong to multiple organizations over time, but each session operates in exactly one active organization.
_Avoid_: global tenant context, multi-org session, organization-free login

## Organization Role

The clinic-scoped responsibility assigned to a Real User within one organization. The launch role set is therapist, clinical supervisor, and organization admin.
_Avoid_: platform role, generic admin, global user type

## Platform Operator

A platform-level operator role used for tightly scoped operational intervention outside ordinary clinic membership. It is separate from organization roles and must not be treated as routine clinic access.
_Avoid_: org admin, clinic admin, ordinary staff role

## Break-Glass Access

Scoped emergency access to a specific clinical target for a Platform Operator under explicit reason, expiry, and audit controls. It is not routine clinical access and must not become a standing permission.
_Avoid_: admin override, normal support access, platform-wide clinical access

## Clinical Grant

An explicit permission path that allows a user to access clinical content beyond administrative organization management rights. It must be granted intentionally and must not be implied by an organization admin role alone.
_Avoid_: automatic admin access, implicit clinical rights, default full access

## Primary Assigned Therapist

The assigned therapist designated as the accountable clinical signer for a case's report sign-off path. Other assigned therapists may collaborate on the case, but they are not the default report signer.
_Avoid_: any assigned therapist, implicit signer, generic case owner

## Controlled Clinic Rollout

The first production launch shape where lingualens is introduced to a limited, explicitly approved clinic tenant set under operational, legal, and security gates. The launch starts with one clinic tenant, not a broad multi-clinic or public rollout.
_Avoid_: public launch, open SaaS launch, unrestricted multi-tenant rollout

## Assignment-Safe Metadata

The minimum operational case metadata that an organization admin may view in order to manage care-team assignment without receiving full clinical access. It excludes transcript text, report body, audio details, clinical notes, and unnecessary child identifiers.
_Avoid_: full case access, transcript preview, report preview, clinical content summary

## Tenant-Safety Promotion Gate

The pre-production verification gate that proves tenant isolation and authorization behavior on staging using real Supabase Auth claims and production-like infrastructure. It is not satisfied by local mock or scaffold-only tests.
_Avoid_: local-only auth test, mock tenant proof, scaffold verification only

## Draft Report Preview

A non-final report view used to show workflow status before transcript review is
complete. It may show missing steps and preliminary context, but it must not
present guideline-linked interpretation as report eligible.
_Avoid_: preliminary Progress Report, unsigned clinical report

## Exportable Progress Report

A Progress Report that may be saved, printed, exported, or treated as
report-eligible because transcript review sign-off and safety wording
requirements are satisfied. It excludes preliminary-only outputs.
_Avoid_: unsigned report export, preliminary clinical report

## Signed Report Snapshot

The report content after therapist sign-off has stamped the signer, sign-off
status, and export timestamp into the report body. It records workflow
accountability, not a diagnostic conclusion.
_Avoid_: diagnostic certificate, automated final report

## Report Attestation

The therapist's final confirmation before exporting an Exportable Progress
Report that they reviewed and edited the report wording, limitations, and
included decision-support outputs. It is an export confirmation state, not a
replacement for Transcript Sign-Off as the report eligibility gate.
_Avoid_: second transcript sign-off, automatic report approval

## Report Preview

The in-app rendered Progress Report view used for review, editing context, and
browser print/PDF output. It is not a separate standalone HTML export artifact
unless a future handoff format is explicitly designed.
_Avoid_: HTML export, standalone clinical HTML file

## Report Type Focus Section

A section inside a Draft Report Preview that explains whether the draft is
focused on a session review, progress comparison, transcript QA, or
research/model summary. It changes emphasis inside the report, not the clinical
safety gates or therapist sign-off requirements.
_Avoid_: separate ungated report, diagnostic report mode

## Reviewed-Only Report Output

A report rule that includes reference cohort similarity only when the output is
reviewed and report eligible. Preliminary similarity may remain in workflow or
audit data, but it must not be used as a report result.
_Avoid_: preliminary report output, triage score in report

## Report Lifecycle Status

The therapist-facing state of a report: Draft while generated content remains
unreviewed, Reviewed after therapist editing, and Finalized after therapist
sign-off. A Finalized report is read-only; later changes require a new report
version rather than silently changing signed content.
_Avoid_: editable finalized report, automatic final report

## Report Share Status

A workflow record describing whether a report is Not shared, had a secure-link
action copied, or was recorded as Sent to caregiver. It does not prove delivery
and must not imply that a production secure-sharing service exists in local
mode.
_Avoid_: delivery confirmation, public report link

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

## Transcript Line Review

A per-utterance or per-line QA state used to track edits, speaker labels,
confidence concerns, and therapist comments during transcript review. It
supports audit detail but does not by itself make a report exportable.
_Avoid_: report sign-off, final transcript approval

## Transcript Sign-Off

The whole-transcript clinical review checkpoint that confirms the transcript is
ready to serve as the source for report-eligible feature interpretation. It is
the report eligibility gate for an Exportable Progress Report.
_Avoid_: line edit, automatic transcript approval

## Reviewed Similarity Refresh

The automatic post-sign-off workflow that recomputes clinical speech features
and reviewed reference cohort similarity from reviewed transcript lines. It
does not create or export a progress report by itself.
_Avoid_: automatic report generation, auto-diagnosis

## Reviewed Feature Refresh

The post-sign-off workflow that recomputes reviewed feature values and
AI-Assisted Review Support from the signed-off transcript. Failure to refresh
does not undo Transcript Sign-Off, and edited transcripts make prior outputs
stale until refreshed again.
_Avoid_: manual-only feature step, automatic report approval

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

## Language Sample Analysis Finding

A descriptive transcript-derived observation such as utterance length, lexical
diversity, question use, or turn-taking. It should be interpreted first as a
language sample analysis measure before any autism-related framing is added.
_Avoid_: autism marker by default, diagnostic language feature

## Evidence-Linked Finding

A report finding that connects a feature value to its calculation, clinical
relevance, source reference, Thai validation status, and any follow-up review
prompt. When no project-verified threshold or norm exists, it may show
construct linkage and limitations but must not label the value as normal,
abnormal, elevated, low, or clinically significant.
_Avoid_: automated diagnosis, final clinical interpretation, unsourced severity label

## Descriptive Feature Value

A computed speech-language measurement that can be shown without claiming it is
normal, delayed, elevated, or clinically significant. Clinical meaning requires
a verified source or must remain pending verification.
_Avoid_: implied norm, unsourced concern flag

## Thai Developmental Source

A Thai child-development reference that can support milestone context or
follow-up screening prompts for Thai children. It must not be treated as a
language sample analysis norm unless it directly provides that measurement.
_Avoid_: Thai LSA norm by implication, borrowed threshold

## Traceable Follow-Up Prompt

A suggested next review or assessment step that is linked to a finding,
rationale, evidence source, and evidence level. If that chain cannot be
verified, the prompt must remain pending verification rather than becoming a
clinical recommendation.
_Avoid_: generic automated recommendation, uncited referral advice

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

## AI-Assisted Review Support

The therapist-facing section that groups review priority, evidence review, and
editable draft summary support for a session or report. It helps the therapist
decide what to inspect next and must not be presented as an AI review of the
child or as a clinical conclusion.
_Avoid_: AI Review, AI diagnosis, automated triage, automated conclusion

## AI Review Disposition

The therapist's decision to keep editing, accept, or reject AI-Assisted Review
Support before it can influence report content. Rejection removes the AI text
from report output; it is not a clinical finding about the child.
_Avoid_: AI verdict, model decision, clinical conclusion

## AI Review Provenance

The traceable model, prompt, transcript version, and feature schema context used
to produce AI-Assisted Review Support. It supports audit and therapist review,
not clinical validation or automated authority.
_Avoid_: model proof, diagnostic provenance, final AI source of truth

## Direct-Identifier Sanitization

The required removal or replacement of names, birth dates, phone numbers,
emails, addresses, and clinical or school record identifiers before text is
prepared for AI-assisted processing outside the local clinical workflow. It
reduces exposure risk but is not a substitute for compliant deployment review.
_Avoid_: PHI-safe guarantee, anonymization proof, consent-free AI use

## Draft Summary

Editable report prose generated from reviewed transcript context, descriptive
features, and safety wording for therapist revision. It is not raw AI output
and must not become final report text without therapist review.
_Avoid_: final AI summary, automated clinical summary, raw AI output

## Progress Report

A therapist-facing artifact that summarizes descriptive changes across
sessions, therapy goals, transcript review status, and decision-support
outputs. It is the canonical report artifact for clinical decision support,
including guideline-linked interpretation and transcript quality context; it is
not an ASD diagnosis.
_Avoid_: clinical-support report as a separate report type, diagnostic report

## Therapist Workspace Note

A therapist-entered note attached to a child case, session, or observation
review during transcript review. It may be included in a Progress Report when
clinician-facing context is needed.
_Avoid_: AI note, generated finding, diagnostic note

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

## Withdrawn Therapy Goal

A therapy goal linked to a case whose consent has been withdrawn or whose
case workflow no longer retains goal details. It preserves governance state
without implying the clinical goal was completed, failed, or clinically
resolved.
_Avoid_: completed goal, failed goal, clinical outcome

## Case Progress View

A child-case-level view of session timeline, descriptive feature trends,
therapy goal progress, before/after comparison, and review status across
sessions. It supports Progress Report drafting but is not a separate top-level
therapist workspace.
_Avoid_: Progress Workspace, standalone progress dashboard

## Therapist Simple Mode

The default therapist-facing presentation of the existing clinical workflow,
focused on case, session, upload, transcript review, and Progress Report steps.
It simplifies labels and hides technical metrics by default without creating a
separate product surface or clinical workflow.
_Avoid_: separate simple app, reduced clinical workflow, beginner mode

## lingualens

A workflow redesign of the existing therapist/clinician app focused on
case-centered clinical decision support, transcript review, and Progress Report
generation. It is not a separate Next.js product surface or parallel clinical
workflow.
_Avoid_: separate therapist app, Next.js rewrite, parallel clinician product

## Today / Work Queue

The default therapist landing view that organizes sessions, transcript reviews,
processing issues, reports awaiting sign-off, and recent child cases by what
needs attention next. It replaces a dashboard-first mental model for the
therapist workflow.
_Avoid_: dashboard, analytics home, research overview

## Derived Work Queue

A Today / Work Queue view calculated from existing child case, session,
transcript, processing, report, sign-off, and privacy-operation states. It is
not a separate persisted task model unless durable assignment or workload
routing is later introduced.
_Avoid_: new queue table, duplicated workflow status, manual task mirror

## Therapist Five-Step Workflow

The canonical simple workflow for demonstrating the therapist app: open a case,
add a session, upload a file, review the transcript, and generate a Progress
Report. Technical metrics and reference comparisons remain secondary details.
_Avoid_: AI-first workflow, diagnosis workflow, research dashboard workflow

## Session Workspace

The therapist-facing workspace for one session inside the Therapist Five-Step
Workflow. It may show detailed sub-statuses for intake, transcript QA, feature
extraction, AI-assisted review, report drafting, and sign-off, but those
sub-statuses do not replace the five-step workflow.
_Avoid_: seven-step primary workflow, research pipeline view, model dashboard

## Upload CHAT Transcript

The preferred manual-first source path for adding a session transcript to the
therapist workflow. Uploaded CHAT content remains awaiting therapist review
until transcript sign-off confirms it is ready for report-eligible
interpretation.
_Avoid_: final transcript upload, automatically approved transcript

## Paste Transcript Text

A manual entry path that converts pasted speech-language transcript text into a
reviewable CHAT draft. It is source material for therapist review, not a final
clinical transcript.
_Avoid_: final manual transcript, reviewed transcript by entry

## ASR-Generated CHAT Draft

A CHAT-style transcript draft produced from uploaded or recorded audio through
the backend audio-to-CHAT boundary. It is experimental source material and must
remain awaiting therapist review before feature interpretation or report use.
_Avoid_: production transcription, automatic clinical transcript, final ASR output

## Primary Therapist Deliverable

The therapist/clinician app is the main project deliverable and the surface
used to demonstrate clinical decision support, transcript review, and Progress
Report generation.
_Avoid_: equal-priority public screening app, dashboard-first deliverable

## Supplementary Public Screening Surface

The public screening app is an educational demo surface, not the main clinical
workflow. It should receive only safety wording and broken-demo fixes unless
the project scope explicitly changes.
_Avoid_: primary clinical app, diagnostic screening product

## Supplementary Presentation Dashboard

The presentation dashboard is a research and advisor-demo surface for
explaining model results, dataset limitations, feature importance, and Thai
validation gaps. It does not duplicate the therapist workflow.
_Avoid_: primary therapist workflow, clinical report surface

## Before/After Radar

A visual comparison of selected speech-language feature values from an earlier
session and a later session. It is descriptive progress tracking only and does
not establish clinical improvement by itself.

## Reviewed Progress Comparison

A Progress Report section that compares numeric feature values from the current
reviewed session with a previous reviewed session for the same case. It is a
descriptive longitudinal summary and still requires therapist interpretation.
_Avoid_: clinical improvement proof, automated progress conclusion

## Exploratory Acoustic Feature

An audio-derived or prosody-related measurement shown for technical review or
research demonstration only. It must be labeled exploratory/display-only unless
separate validation evidence supports its clinical use.
_Avoid_: acoustic clinical marker, validated prosody indicator

## Experimental Audio-to-CHAT Pipeline

The audio processing workflow that can produce CHAT-style transcript artifacts
for review. It is not a production-ready clinical transcription system and
requires therapist transcript review before any report-eligible interpretation.
_Avoid_: production-ready audio pipeline, automatic clinical transcription

## Clinical decision support

Information that helps a speech-language therapist, clinician, advisor, or
trained reviewer inspect patterns and decide what should be reviewed next. It
does not replace clinical assessment.

## Guideline Source

A traceable clinical or methodology reference used to explain why a finding is
clinically relevant. It must be verified before it can support a threshold,
normative value, cutoff, or interpretation.

## Verified Open-Access Guideline Source

A Guideline Source whose public source page or document can be reviewed and
linked in the project. It may support broad clinical construct linkage, but it
does not by itself validate thresholds, norms, or Thai clinical interpretation.
_Avoid_: validated norm source, diagnostic guideline proof

## Pending Local Guideline Source

A Thai or local-context source that may be clinically relevant but has not yet
been verified for the specific report claim being made. It must remain marked
as pending verification until the source and intended use are reviewed.
_Avoid_: assumed Thai norm, unverified local guideline

## Guideline Mapping Catalog

The canonical structured mapping between speech-language features, clinical
constructs, Guideline Sources, Thai validation status, and report-use
limitations. Report views and advisor documentation should derive from this
catalog rather than maintaining separate source lists.
_Avoid_: duplicated guideline list, UI-only mapping, report-only citation list
_Avoid_: placeholder citation, invented guideline URL, uncited norm

## Reference Pending Verification

The required placeholder for any guideline threshold, normative value, cutoff,
citation detail, or interpretation that has not been verified from a traceable
source. It preserves missing evidence instead of turning uncertainty into a
clinical claim.
_Avoid_: estimated reference, provisional norm, assumed cutoff

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

## Thai Validation Status

A finding-level label that states whether the supporting source has been
validated for Thai children, is partially applicable to Thai context, is not
validated for Thai children, or is pending verification. It describes evidence
fit, not whether the finding is clinically important.
_Avoid_: pass/fail evidence label, Thai norm by default

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

## Settings Workspace

The therapist or clinician workspace for profile, credentials, organization,
sample-data/runtime status, and owned-case privacy operation requests. It should
not expose research, model, audit, or debug controls as ordinary therapist
workflow.
_Avoid_: admin panel for all users, debug settings, research controls

## Admin Workspace

The admin-only workspace for audit logs, privacy operation queues, runtime
diagnostics, and local development reset controls. It is role-scoped and must
not become part of the ordinary therapist workflow.
_Avoid_: therapist settings, main clinical workflow, hidden audit access

## Case Owner

The clinical user responsible for a child case. Each child case has exactly one
case owner unless an admin is viewing across owners for testing/demo purposes.

## Child Case

An anonymized record for one child being reviewed or tracked by a clinical user.
It must not contain the child's real name or direct identifiers.

## Anonymized Child Code

The stable non-identifying code used as the canonical child case identifier in
records, exports, and clinical workflow references. It must not contain direct
child identifiers.
_Avoid_: real child name, hospital number, school ID

## Display Label

An optional non-identifying therapist label used to scan and recognize a child
case in the UI. It must not be a real child name, surname, direct nickname,
address, school ID, hospital ID, phone number, or other direct identifier.
_Avoid_: nickname, child name, identifying label

## External Clinical Status

Therapist-entered context about information recorded outside the system. It is
not generated by the model and is separate from any screening risk estimate.
_Avoid_: diagnosis status, AI diagnosis

## Mock Mode

A clearly labeled demonstration mode using seeded clinical users, anonymized
child cases, and seeded workflow records. Mock mode must not be silently mixed
with real uploaded data or real clinical records.

## Local Clinician Workspace

A browser-local therapist workflow that opens directly for immediate use with
anonymized cases, local uploads, CHAT/.cha transcript review, feature
extraction, reference cohort similarity, and report drafting when a secure
backend is not configured. It is a usable local workflow mode, not a diagnostic
system or validated clinical deployment.
_Avoid_: toy demo, production deployment, automated diagnosis

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

## Consent-Gated Source Material

Session source material whose upload, storage, processing, or export depends on
guardian consent or transcript permission in real or pilot modes. Mock/local
demo mode may allow reviewable sample workflows only when Sample Data Mode is
visible and direct identifiers are excluded.
_Avoid_: consent-free clinical upload, hidden consent state

## Consent Withdrawn State

A case state where new uploads, processing, and exports are blocked while
retained audit, sign-off, and policy-required records remain available for
authorized review.
Queued processing jobs are cancelled instead of producing new clinical
artifacts.
_Avoid_: immediate hard delete, continued processing

## Privacy Operation

An auditable request to export case records, withdraw consent, or review
deletion for a child case. It is a workflow request, not automatic data erasure.
_Avoid_: hard delete, purge button

## Privacy Operation Queue

The admin-scoped list of Privacy Operations awaiting review, completion, or
rejection. It tracks governance workflow status and must not contain direct
child identifiers, transcript text, or raw audio.
_Avoid_: deletion engine, export package, clinical record dump

## Auth Mode

The active authentication boundary for the speech therapist prototype: mock
sample-account sign-in or provider placeholder. It controls how a clinical
user enters the workspace but does not change case ownership rules.

## Mock Role Selection

A demo-only login choice that routes a user into therapist or admin scoped
views without creating a production identity, access grant, or persisted
clinical session.
_Avoid_: real auth role, production access control, browser-stored permission

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

## Unsaved Browser Recording

A microphone recording whose audio bytes exist only in memory for the current
page lifecycle. Non-sensitive recording metadata may survive refresh, but the
audio itself is cleared unless a future explicit user-authorized upload occurs.
_Avoid_: locally stored recording, persisted browser audio

## File Object

A private backend record for stored audio or video bytes attached to an audio
file metadata record. Its permanent storage key is backend-only and must not be
shown to the browser.
_Avoid_: uploaded file, browser file path

## Linked Media Header

A CHAT `@Media` header generated from non-identifying session and audio record
IDs when an exported transcript is linked to retained audio metadata. It should
not expose original filenames, storage keys, or child identifiers.
_Avoid_: original media filename, private storage key, identifying file label

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

## Basic CHAT Export

A deliberately limited reviewed `.cha` artifact containing core metadata,
participant IDs, optional linked media, speaker tiers, and available media time
marks. It requires therapist review and is not a claim of full TalkBank
compatibility.
_Avoid_: TalkBank-compatible export, complete CHAT export

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

## CHAT Speaker Code

The participant code carried by a CHAT speaker tier, such as `CHI`, `INV`, or a
configured corpus code. Syntactically valid unfamiliar codes are preserved
during import and flagged for review rather than rewritten to `UNK`.
_Avoid_: speaker role, normalized speaker label

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

## Unsupported Language QA Warning

A transcript QA warning that the transcript language metadata is outside the
currently supported local QA languages. It asks the therapist to document
interpretation limits; it is not a clinical judgement about the child or
language ability.
_Avoid_: invalid language sample, diagnostic language flag

## Code-Switching QA Warning

A transcript QA warning that mixed-language text appears without matching CHAT
language metadata. It asks the therapist to review language labels and
interpretation limits, not to draw a clinical conclusion.
_Avoid_: language deficit flag, diagnostic code-switching marker

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

## Language-Sample Cue

A descriptive count, ratio, or conservative pattern flag derived from a saved,
therapist-reviewed language sample. Examples include utterance counts, MLU,
lexical diversity, question use, unclear speech, repetition, possible
echolalia, and possible pronoun reversal. A language-sample cue supports
therapist interpretation and is not a diagnosis, prediction, or confirmed
clinical finding.
_Avoid_: ASD marker, diagnostic feature, symptom detection

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

## Audio Upload Completion

The metadata-only API step that records an uploaded audio object's checksum,
size confirmation, and upload timestamp after a backend-issued signed upload
intent is used. It must not accept raw audio bytes in JSON payloads or browser
state.
_Avoid_: audio file upload body, frontend audio storage

## Clinical Storage Adapter

The backend boundary that creates signed upload intents and performs storage
object deletion during consent withdrawal. Local and metadata-only adapters are
development scaffolding; pilot private storage requires deployment-specific
configuration and audit review.
_Avoid_: browser storage adapter, implicit production storage

## Structured AI Assistance Area

A therapist-reviewable decision-support section that names one constrained AI
assistance purpose, such as transcript QA, feature explanation, review
priority, progress summary, or report drafting. It must stay editable,
rejectable, provenance-linked, and non-diagnostic.
_Avoid_: AI diagnosis section, final clinical finding, raw model output

## ASR Failed State

An audio processing job outcome where the configured ASR Draft Provider did not
produce transcript content. It preserves a clear failure for therapist review
instead of inventing an ASR-Generated CHAT Draft.
_Avoid_: silent fallback transcript, fabricated ASR draft

## Diarization Failed Warning

A draft transcript warning that speaker assignment could not be trusted and
the therapist must correct speaker labels before attestation or feature
interpretation. It is a transcript quality warning, not a conclusion about the
child.
_Avoid_: assumed child speech, final speaker assignment

## ML Review Result

A backend-persisted set of feature-based review cues derived only from features
extracted from a reviewed, attested transcript. It requires therapist
interpretation and never represents a diagnosis, positive/negative result, or
automatic report conclusion.
_Avoid_: ML Decision-Support Draft, ML diagnosis, ASD prediction, local ML result

## Insufficient-Sample ML Review Result

An ML Review Result recording that the reviewed language sample is too small
for pattern cues. It may provide only a request for additional language sample
and must not infer other patterns from the limited sample.
_Avoid_: low-confidence prediction, partial diagnosis, negative result

## ML Core Feature Set

The minimum feature values required to assess an ML review request:
child utterance count, adult utterance count, and total child word count.
Additional feature values enable individual cues but do not block the whole
review when absent.
_Avoid_: complete feature vector, classifier feature set, every extracted feature

## Attested QA Warning

A non-blocking transcript quality issue that remains visible after the
therapist attests the transcript. Attestation records acceptance of the warning
for continued review; it does not remove or resolve the issue.
_Avoid_: ignored warning, resolved warning, QA pass

## Current ML Review Result

The ML Review Result linked from a session because it matches the session's
current transcript and feature set. Earlier results remain audit history but
are not current review support.
_Avoid_: overwritten ML result, latest by timestamp only, browser-cached result

## Experimental Classifier Provider

A registered but unavailable ML provider representing the research baseline
until label provenance and runtime feature-schema compatibility are verified.
It must not produce therapist-facing output merely because a model artifact
exists.
_Avoid_: production classifier, available research model, artifact-driven provider

## Engineering Review Threshold

A transparent heuristic boundary used to decide when a feature should prompt
closer therapist review. It is not an age norm, clinical cutoff, risk level, or
validated diagnostic threshold.
_Avoid_: clinical threshold, abnormal range, ASD cutoff, normative score

## Review Cue Severity

The amount and type of therapist attention requested by a Review Cue: context
information, direct transcript review, or interpretation caution. It does not
represent symptom severity, clinical urgency, or ASD risk.
_Avoid_: condition severity, risk tier, diagnostic confidence

## Review-Workspace-Only Result

A decision-support result available for therapist inspection in the session
results workspace but excluded from report drafts and report eligibility. It
may enter a report only through a future explicit therapist-selection workflow.
_Avoid_: report-ready result, automatic report content, required report input

## Default ML Review Provider

The available provider selected automatically to create an ML Review Result.
Provider metadata remains visible for transparency, while experimental or
unavailable providers are not therapist-selectable.
_Avoid_: therapist-selected model, automatic experimental model, hidden provider

## Unavailable ML Review Request

A request that cannot produce an ML Review Result because the requested
provider is not available. It returns structured readiness reasons and is not
persisted as though provider processing occurred.
_Avoid_: failed inference result, persisted unavailable result, silent fallback

## Offline ML Review State

The session state shown when backend verification is unavailable. It does not
generate, restore, or display browser-cached review cues and requires the
backend before an ML Review Result can be shown.
_Avoid_: local ML preview, cached ML result, offline inference

## Experimental Audio Workflow

The explicitly labelled local-demo path that captures browser audio and may
produce an ASR draft for therapist correction. Recording and ASR are not
validated clinical capture or transcription services, and their output cannot
bypass transcript review and attestation.
_Avoid_: clinical recording system, validated ASR, final transcript
