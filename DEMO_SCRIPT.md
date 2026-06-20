# Therapist App Usability Demo

Use anonymized sample content only. Recording and ASR are experimental.

## Before the demo

Start the backend:

```bash
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Start the frontend in a second terminal:

```bash
cd apps/therapist-app-v2
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

Open `http://localhost:3000`.

## Demo steps

1. **Open app**
   - Confirm the local/demo and decision-support-only labels.
   - Select **Start Recording**.

2. **Start recording**
   - Allow browser microphone permission.
   - Select **Start recording**.
   - Point out the **Experimental** recording/ASR label.

3. **Stop recording**
   - Select **Stop recording**.
   - Confirm playback appears.
   - Select **Upload for transcription**.
   - Show queued, processing, and completed status.

4. **Analyze**
   - Explain that feature extraction is still locked.
   - The generated text is a draft, not a final transcript.

5. **Review transcript**
   - Correct wording and speaker labels.
   - Save the transcript, run QA, and attest it.
   - Select **Extract language-sample features**.

6. **Generate report**
   - Open `/results`.
   - Review language-sample cues.
   - Select **Generate Report**.
   - Edit therapist notes, goals, and report wording.

7. **Finalize report**
   - Confirm the report has been therapist-reviewed.
   - Select **Finalize Report**.
   - Show that the finalized report is read-only.

## Recovery

- If microphone permission fails, use **Paste transcript** from Quick Start.
- If the backend is unavailable, the primary workflow uses local fallback
  state where supported and displays an error message.
- Refreshing clears unsaved audio. Record again or use transcript input.
