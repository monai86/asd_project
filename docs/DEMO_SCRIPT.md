# Speech Therapist App Walkthrough & Demo Script

This script outlines a step-by-step presentation flow of the clinical workflow prototype for advisors and stakeholders.

---

### Step 1: Therapist Login
1. Open the Therapist app in your browser (default local URL: `http://localhost:5173`).
2. Point out the **Mock Mode Banner** and **Safety Disclaimer** at the bottom of the screen.
3. Enter the mock therapist email: `therapist@example.test`.
4. Enter the password: `demo-password` and click **Log In**.

---

### Step 2: Open Dashboard & Caseload Review
1. Once logged in, show the **Therapist Dashboard**.
2. Point out the summary metrics:
   - *Active Cases:* `2`
   - *Sessions Awaiting Transcript Review:* `1`
   - *Uploaded Files:* `1`
3. Point out the **High Review-Priority Cases** queue and **Recent Cases** list.

---

### Step 3: Create a Case
1. Click the **Create case** quick-action button on the dashboard.
2. Fill out the mock form details:
   - **Anonymized Child Code:** `CHI-A03`
   - **Age:** `42` months
   - **Sex:** `not_specified`
   - **Primary Concerns:** "Limited expressive speech, occasional repetitive words."
   - **Consent Status:** `granted`
   - **Anonymization Status:** `anonymized`
   - **External Clinical Status:** `under_evaluation`
3. Click **Create Case**. The dashboard updates and audit logs log the creation event.

---

### Step 4: Add a Session
1. Select the newly created case `CHI-A03` from your list.
2. Click **Add session** from the case detail view.
3. Select today's date and choose `therapy_session` as the session type.
4. Click **Create Session**.

---

### Step 5: Upload Mock Audio Metadata
1. Within the new session detail page, go to the **Upload Audio File** section.
2. Select any local mock media file (e.g. `recording.wav` or `sample.mp3`).
3. Click **Upload**.
4. Show that the file is registered as `CASE-004_SESSION-004_AUDIO-002.wav` (anonymized format).
5. Point out the **Data Privacy Guardrail**: explain to the audience that the application is operating in a privacy-compliant metadata-only mode, and no raw child audio bytes are stored on the server.

---

### Step 6: Generate/Review Transcript
1. Click **Generate mock CHAT** to simulate Whisper transcription for the session.
2. Once generated, show the transcript text loaded into the **CHAT Transcript Viewer**.
3. Point out the **Transcript QA Results** block showing a warning (e.g., `LANG_TAG_MISMATCH` or `LOW_ASR_CONFIDENCE`) to demonstrate that the human-in-the-loop review checks are working.
4. Make a small edit in the text area (e.g., correct a word tier from `*CHI: hello` to `*CHI: hello play .`) and click **Save Changes**.
5. Once satisfied, click the **Mark Reviewed** button to transition the transcript status to `reviewed`.

---

### Step 7: Feature Extraction
1. With the transcript status marked as `reviewed`, click **Extract Features**.
2. Point out that the system has successfully calculated the **Core 14-feature schema** (such as `mlu`, `ttr`, `unintelligible_ratio`, `echolalia_ratio`, and `pronoun_reversal_count`).

---

### Step 8: Inspect AI Decision Support & Evidence Flags
1. Click **Generate AI Support**.
2. Present the **AI Decision-Support Output**:
   - Show the **Concern Level** estimation (e.g., `watchful_review`).
   - Review the **Top contributing features** list.
   - Point out the **Evidence Review Panel** cards, highlighting how each contributing feature maps directly to established clinical guidelines (e.g., how the child's `ttr` lexical diversity relates to expressive language delay).
   - Point out that all terminology refers to "screening support" or "concern level", avoiding diagnostic phrases.

---

### Step 9: Add Therapist Interpretation
1. Scroll to the **Therapist Notes** section at the bottom of the session detail view.
2. Enter your clinical note: "Observed child using repetitive phrases during free play. Lexical diversity is moderate. Recommending continued language tracking."
3. Click **Add Note**. Show that the note is added to the session log.

---

### Step 10: View Case Progress Trends
1. Navigate back to the Case detail page for `CHI-A01` (since it has multiple historical sessions to show progress).
2. Point out the progress charts:
   - **Score Trend Over Sessions:** showing the trajectory of concern levels.
   - **Feature Trends:** displaying metrics like MLU growth and decrease in unintelligible utterances over successive dates.
   - **Therapy Goal Progress:** tracking the success of active target behaviors (e.g., "Increase spontaneous two-word utterances").

---

### Step 11: Export Progress Report
1. On the Case detail page, click **Export Progress Report**.
2. Click **Print / Save PDF** to open the print layout preview. Show how CSS media print styles clean up the dashboard UI elements for a professional clinical printout.
3. Click **Download Markdown** to save a local textual record of the progress timeline.

---

## Manual QA Verification Checklist

### Checklist 1: Test Backend On (Normal Mode)
- [ ] Start backend API and therapist app frontend.
- [ ] Navigate to `/login`, choose Therapist, click `Enter workspace`.
- [ ] Run the workspace demo workflow.
- [ ] Verify that saving drafts, running QA, attesting transcripts, feature extraction, and report generation complete successfully with success status alerts.

### Checklist 2: Test Backend Off (Offline Mode)
- [ ] Terminate the backend API process.
- [ ] Refresh the workspace or review pages.
- [ ] Verify banner "Backend unavailable — local workspace mode" is visible.
- [ ] Verify success status messages (like "Saved" or "Attestation complete") are hidden.
- [ ] Verify that the clinical-final buttons are disabled and labeled `(Online only)`.

### Checklist 3: Test API Restart Persistence
- [ ] Start the backend API with `JsonFileRepository` mode.
- [ ] Perform a full workflow: create a case/session, review a transcript, extract features, and draft a report.
- [ ] Shut down the backend API.
- [ ] Start the backend API again.
- [ ] Refresh the page on the frontend and verify all edited transcript texts, attestation states, and draft report inputs reload intact.

### Checklist 4: Test Export .cha
- [ ] Save and attest a transcript.
- [ ] Click "Export reviewed .cha" in the transcript review workspace.
- [ ] Verify that a `.cha` file downloads containing correct CHAT headers (`@Begin`, `@Languages`, `@Participants`, etc.) and matching speaker utterances.

### Checklist 5: Test Finalized Report Reload
- [ ] Generate a report, edit notes/goals, and click "Finalize Report".
- [ ] Verify the report text areas and inputs display as read-only.
- [ ] Verify the "Save draft", "Generate draft", and "Finalize" buttons are disabled.
- [ ] Refresh the page and confirm the report loads as "Finalized" and is strictly read-only.
