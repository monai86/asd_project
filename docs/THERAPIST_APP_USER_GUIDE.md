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
4. **Data Privacy Guardrails:** No audio file bytes or raw speech recordings are persisted in this version. The app operates on a metadata-only basis.

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

### Metadata-only Upload Behavior
- **Supported Formats:** `.wav`, `.mp3`, `.m4a`, `.mp4`, `.mov`
- **Max File Size:** 250 MB
- **Data Protection Design:** When a file is uploaded, the app calculates the file size and formats a secure name using unique identifiers (e.g., `CASE-001_SESSION-001_AUDIO-002.wav`). **No actual media files or raw bytes are uploaded or saved to the server** to guarantee child voice privacy.
- **State Change:** The session's "feature extraction status" and "ASR status" transition to `pending`.

---

## 📝 5. Mock ASR & CHAT Transcript Workflow

Once the audio metadata is registered, the system prepares a transcript for review.

### Transcript Quality Assurance (QA)
- **File Format:** The prototype strictly consumes and exports standard TalkBank/CHAT format (`.cha`) transcripts.
- **Mock ASR Mode:** Since the browser app does not run Whisper directly, click **Generate mock CHAT** to simulate ASR output based on pre-set script templates.
- **Structure QA Validation:** The system auto-validates the transcript text for structural issues:
  - Missing `@Begin` or `@End` tags.
  - Missing `@Participants` or `@ID` metadata fields.
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
