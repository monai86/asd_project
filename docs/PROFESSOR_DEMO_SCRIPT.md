# Professor Demo Script

Audience: advisor/professor review of the Therapist App v2 local MVP.

Clinical boundary: this is a research and education prototype. It supports therapist review, report drafting, and workflow demonstration only. It does not diagnose ASD, does not show ASD probability, and does not replace clinician judgment.

## Exact Demo Command Sequence

From the repository root:

```bash
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd apps/therapist-app-v2
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

Open:

```text
http://localhost:3000/login
```

Optional verification before the live walkthrough:

```bash
cd apps/api
PYTHONPATH=. pytest -q
```

```bash
cd apps/therapist-app-v2
npm run typecheck
npm run lint
npm test
npm run build
```

## Click-by-Click Walkthrough

1. Open `/login`.
2. Leave role as `Therapist`.
3. Click `Enter workspace`.
4. On `Today / Work Queue`, point out the `Local demo data` label.
5. Click `Open cases`.
6. On `Cases`, point out consent status, latest session, report status, and review priority. State that review priority is scheduling support, not a diagnosis.
7. Click case `C-1024`.
8. On the case detail page, point out consent status, session timeline, therapy goal progress, before/after comparison, and the local demo data label.
9. Click `Create new session`.
10. On `Session Workspace`, point out the seven-step workflow: Intake, Transcript, Review & Attestation, Feature Extraction, AI Review, Report Draft, Therapist Sign-off.
11. Point out the source material intake buttons are labeled as local demo UI states.
12. Click `Run demo workflow`.
13. Wait for the workflow cards to update.
14. Confirm the case/session card shows a generated `C-DEMO-*` case and a session id.
15. Confirm QA status is `PASS` or a warning state that still requires therapist review.
16. Confirm feature count and feature summary values are visible.
17. Confirm AI-assisted review status appears as decision support and remains therapist-reviewable.
18. Confirm report edit and export show `Edited Demo Session Review Report` and a Markdown export filename.
19. Scroll to the exported CHA textarea and show the generated `@Begin`, `*CHI`, and `@End` structure.
20. State that this path exercised FastAPI endpoints for case creation, session creation, CHA upload, QA, attestation, feature extraction, AI-assisted review, report draft, report edit, sign-off, report export, and CHA export.
21. Open `/reports`.
22. Point out that seeded report cards are labeled local demo data and exports are blocked until sign-off.
23. Open `/settings?scope=admin`.
24. Point out admin-scoped runtime controls, privacy operation queue, audit review, and experimental audio settings.

## What To Say During The Demo

- "The stable MVP path is manual-first: a therapist uploads or enters a reviewed transcript, runs QA, attests quality, extracts language-sample features, reviews AI-assisted support, edits the report, signs off, and then exports."
- "AI text is decision support. It must be edited, accepted, or rejected by the therapist before report use."
- "This prototype does not diagnose ASD and does not show ASD probability."
- "Audio, ASR, ML baselines, storage, and production auth are present as boundaries or experimental scaffolds, not as validated clinical capabilities."

## Fallback If A Dev Server Is Already Running

If port `8000` is busy, use another API port:

```bash
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8001
```

Then start the frontend with the matching API base:

```bash
cd apps/therapist-app-v2
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001/api/v1 npm run dev
```
