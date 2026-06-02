# Speech Therapist & Clinician App User Guide

> **Project:** AI-Assisted Clinical Assessment of Autism (Term Paper)  
> **Status:** Research/Demo Prototype (`MOCK_MODE = True` in [models.py](file:///Users/porschecaa/Desktop/asd-project/src/clinical_workflow/models.py))  
> **Target Audience:** Speech-language therapists, pathologists, and clinical supervisors.

---

## ⚠️ Important Safety & Clinical Boundary Notes

Before using the prototype, please review the safety constraints:
1. **Decision Support Only:** This application is a clinical decision-support prototype. It **does not diagnose ASD** and does not replace qualified clinical judgment.
2. **AI-Assisted Explanations:** All AI model predictions must be referred to as "screening support", "concern level", "review priority", "clinician review support", or "AI-assisted explanations". Diagnostic phrases like "diagnosis result" or "autistic child" must be avoided.
3. **No Local Validation:** The underlying machine learning model was trained on English-speaking public corpora and is **not validated for Thai children**.
4. **Data Privacy Guardrails:** Demo mode remains metadata-only. Clinical pilot mode can use secure backend storage only after guardian consent is granted; audio/video files must be private, encrypted, retention-limited, and audit logged.

---

## 🔑 1. Therapist Login & Mock Accounts

The application does not require a real backend database or active internet authentication. Instead, it utilizes pre-seeded clinical user credentials for demo scenarios:

| Role | Email | Password | Description & Privileges |
| :--- | :--- | :--- | :--- |
| **Therapist** | `therapist@example.test` | `demo-password` | Standard clinical user. Can view, create, and modify owned cases and sessions. |
| **Clinician** | `clinician@example.test` | `demo-password` | Standard clinical user. Has access to separate caseload data. |
| **Admin** | `admin@example.test` | `demo-password` | System administrator. Can view all cases, all files, and inspect the unified clinical audit logs. |

### Accessing the Login Screen
To launch the app locally:
1. Make sure dependencies are installed and run `npm run dev` in the [therapist-clinician-app](file:///Users/porschecaa/Desktop/asd-project/therapist-clinician-app) folder.
2. Open the URL shown in your terminal (typically `http://localhost:5173`).
3. Enter one of the pre-seeded emails and password to authenticate.

---

## 📁 2. Case Management

Case management in the app allows therapists to track child progress under anonymized identifiers.

### Sample / Mock Data Label
- The app shows a visible sample-data banner when mock auth, mock processing, local development persistence, or placeholder database mode is active.
- When this banner is visible, do not enter real child names, contact details, school IDs, medical record numbers, or raw clinical identifiers.
- Real pilot mode must use provider-backed auth, private storage, consent records, and database-backed ownership checks.

### Creating a Case
- **How to Create:** Click the **Create Case** button under the "Quick Actions" panel on the dashboard.
- **Fields Required:**
  - **Anonymized Child Code:** A custom code (e.g., `CHI-A03`) to protect the child's identity. No real names or government IDs should be recorded.
  - **Age (Months):** The child's age in months (e.g., `48` months for 4 years).
  - **Sex:** `female`, `male`, `other`, or `not_specified`.
  - **Primary Concerns:** Narrative description of developmental concerns (e.g., "Parent reports limited phrase speech and echolalia").
  - **External Clinical Status:** State of external diagnostics (`under_evaluation`, `not_provided`, etc.).
  - **Consent Status:** Explicitly mark if parent/guardian consent is `granted` or `pending`.
- **Caseload Separation:** When logged in as `therapist@example.test`, you will only see cases you own (e.g., `CASE-001`, `CASE-002`). Logged in as `clinician@example.test`, you see `CASE-003`. Admins see all three cases.
- **Audit Access:** Therapist and clinician users cannot inspect audit logs. Audit review is admin-only.

### Privacy Operations
- **Export:** Records a case-scoped privacy export request and prepares only records for that owned case.
- **Withdraw Consent:** Marks the case consent as withdrawn, updates active consent records, and records an audit event.
- **Delete Request:** Creates an operational deletion request for review. It does not immediately erase audit logs, sign-off evidence, or records that must be retained under clinic policy.
- **Review Queue:** Open Settings to inspect the privacy operation queue in the prototype.

---

## 📅 3. Session Management

Sessions represent individual therapy dates or screening evaluations for a case.

### Adding a Session
- **How to Add:** Select a case, then click **Add Session** from the case detail view or dashboard quick actions.
- **Fields:**
  - **Session Date:** Pick the date of the interaction.
  - **Session Type:** Choose between `free_play`, `parent_child_interaction`, `structured_assessment`, or `therapy_session`.
  - **Notes:** Optional clinical session notes.

---

## 🎤 4. Audio & Media Upload (Metadata Only)

To begin ASR transcription, therapists can upload an audio recording of the session.

### Secure Upload Behavior
- **Supported Formats:** `.wav`, `.mp3`, `.m4a`, `.mp4`, `.mov`
- **Max File Size:** 250 MB
- **Consent Gate:** Secure backend upload is locked until guardian consent is recorded as `granted`.
- **Data Protection Design:** The app calculates the file size and formats a secure name using unique identifiers (e.g., `CASE-001_SESSION-001_AUDIO-002.wav`). In secure backend mode, the backend creates a private file-object record and returns a short-lived signed upload URL. The frontend never receives the permanent storage key, and upload intent metadata includes retention, encryption, storage provider, and checksum fields when available.
- **Demo Default:** Metadata-only mode still stores no media bytes and is appropriate for classroom demos.
- **State Change:** The session's "feature extraction status" and "ASR status" transition to `pending`.

---

## 📝 5. Mock ASR & CHAT Transcript Workflow

Once the audio metadata is registered, the system prepares a transcript for review.

### Transcript Quality Assurance (QA)
- **File Format:** The prototype strictly consumes and exports standard TalkBank/CHAT format (`.cha`) transcripts.
- **Mock ASR Mode:** Since the browser app does not run Whisper directly, click **Generate mock CHAT** to simulate ASR output based on pre-set script templates.
- **Backend QA Runtime:** In API-backed runtime, the Transcript tab loads `GET /api/sessions/{session_id}/qa` and shows backend CHAT/CLAN readiness flags for feature extraction, Reference Comparison, and CLAN-derived metrics.
- **Mock QA Runtime:** In mock runtime, the browser shows lightweight local QA only. It does not claim to validate CLAN readiness.
- **Structure QA Validation:** Backend QA validates the transcript text for structural and readiness issues:
  - Missing `@Begin`, `@End`, or `@Languages` tags.
  - Missing `@Participants` or `@ID` metadata fields, or participant/ID count mismatch.
  - Missing or unparseable child age and missing `Target_Child` metadata before reference comparison.
  - Short child samples for KIDEVAL-style comparison or VOCD-style metrics.
  - `www` markers without an explanatory `%exp` tier.
  - Thai characters without a `@Languages: ..., tha` tag (flags language tag mismatch).
  - Low confidence scores (simulates instances of high background noise or overlapping talk).
- **QA Indicators:** Warning symbols (e.g., `needs_correction`) appear next to transcripts that fail the structural QA gate.

### Transcript Correction Editor
- Therapists can view and directly edit the text and speaker tiers (e.g., `*CHI`, `*MOT`) in the inline text editor.
- Once corrections are saved, the system automatically runs the QA validator again to update the status.
- Clicking **Mark Reviewed** changes the review status to `reviewed` and allows feature extraction.

---

## 🧠 6. Feature Extraction & AI Decision Support

After the transcript is reviewed and signed off by the therapist, the analysis engine is unlocked.

### Core 14-Feature Schema
Click **Extract Features** to compute 14 speech-language markers:
- **Productivity:** `total_utterances`, `total_words`
- **Complexity:** `mlu` (mean length of utterance in morphemes), `mluw` (mean length of utterance in words)
- **Lexical Diversity:** `ttr` (type-token ratio)
- **ASD Marker Tiers:** `unintelligible_count/ratio`, `zero_vocalization_count`, `nonverbal_vocalization_count`, `echolalia_count/ratio`, `pronoun_reversal_count`
- **Pragmatic:** `question_ratio`

### AI Decision-Support Output
- **Concern Level Gauge:** A graded indicator displaying concern classification:
  - **Low Concern** (sigmoidal concern score < 0.40)
  - **Watchful Review** (sigmoidal concern score between 0.40 and 0.67)
  - **Moderate Concern** (sigmoidal concern score >= 0.67)
- **Top Contributing Features:** Lists which features had the highest influence on the concern score.
- **Evidence Review Panel:** Automatically populates explanation cards describing the clinical relevance of the high-scoring features (e.g., explaining why a high `echolalia_ratio` or low `mlu` contributes to the overall screening priority).

### Reference Comparison & Reference Readiness Index
- **Reference Readiness Index:** The app queries a centralized descriptive metadata index containing the readiness of Reference Cohorts by age band, language, task type, and clinical group. It tracks ready cohorts, low-count caution cohorts, and unavailable cohorts.
- **Resource Library View:** Displays the overall count of ready, low-count, and unavailable descriptive Reference Cohorts. It shows a research-only disclaimer and advises caution when dealing with low-count cells.
- **Transcript Tab Gate:** The Reference Comparison panel appears inside the transcript review workflow and stays blocked until the transcript is reviewed, feature extraction is `completed`, backend QA is available in API runtime, and QA says `reference_comparison_ready`.
- **Low-Count Warning Badge:** If a matched cohort is marked as `low_n`, the UI displays a caution warning badge: `"Caution: low-count context"`. Clinicians should treat these comparisons as research-only and exercise extra caution.
- **Safety Boundary & Restricted Language:** Reference Comparison is descriptive context only. To ensure clinical safety, all user-facing wording strictly avoids diagnostic, benchmark, validation, or normative terminology. It is never presented as a scoring or diagnostic norm system.
- **Backend Runtime:** In local-dev or pilot-backend mode, the panel can load the backend `Reference Comparison` response and display matched age/task cohort context, confidence flags, and available CLAN-Derived Metrics separately from Core 14 feature comparisons.
- **Mock Runtime:** In default mock mode, the panel shows a status-only unavailable message. It does not generate mock percentiles or pretend to provide reference distributions.

---

## 📈 7. Progress Monitoring & Report Generation

The ultimate stage is documenting progress over time and exporting findings.

### Caseload Progress Monitoring
- **Score Timeline:** Displays historical screening scores across chronological sessions.
- **Feature Trends:** Plots individual feature trends (e.g., increasing `mlu` or decreasing `unintelligible_ratio` over successive dates).
- **Radar Charts:** Shows a visual before-and-after comparison of linguistic parameters.
- **Therapist Interpretation:** Click **Add Therapist Note** to append manual observations and clinical interpretations to the record.

### Generating & Exporting Reports
1. Navigate to the Case detail page.
2. Click **Generate Report** or **Export Progress Report**.
3. Choose the export format:
   - **Download Markdown:** Exports a plain-text markdown report containing child case data, goals progress, score timeline, and clinical disclaimers.
   - **Print / Save PDF:** Leverages custom browser printing styles to generate a clean, formatted PDF document containing charts and tables.
