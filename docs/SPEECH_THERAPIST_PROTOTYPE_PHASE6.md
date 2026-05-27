# Speech Therapist / Clinician Prototype Phase 6

Phase 6 adds progress monitoring and report generation for the standalone
Speech Therapist / Clinician App. It stays in `MOCK_MODE=True` and remains
separate from the Pastel dashboard and public screening app.

## What Phase 6 Adds

- Score timeline by visible owned sessions.
- Feature trends over sessions using the shared 14-feature schema subset used
  by existing therapist reports.
- Therapy goal progress summaries for active, paused, and completed goals.
- Before/After Radar comparison for selected first-vs-latest feature values.
- Printable/exportable Markdown progress report generation.
- Mock `Report` records in `src/clinical_workflow/`.
- `report_exported` audit events.

## Safety Boundary

Reports are descriptive clinical decision-support artifacts. They do not
diagnose ASD and do not replace qualified clinical judgment. A therapist or
clinician must review transcript QA, session context, feature summaries,
therapy notes, and the child’s broader clinical picture before sharing or
acting on any report.

## Mock Mode Limits

- No real PDF backend is connected in Phase 6.
- Markdown export is generated in the browser only.
- No real database is used.
- No real audio/video files are stored.
- The existing `therapist_report.py` metric direction and safe-report wording
  are reused as the prototype boundary, but mock clinical records remain
  separate from TalkBank/ASDBank child labels.

## Repository Contract

`MockClinicalRepository` now supports:

- `list_goals_for_case_for_user(...)`
- `progress_summary_for_case(...)`
- `generate_progress_report_for_case(...)`
- `list_reports_for_case_for_user(...)`

Clinical users can only summarize and generate reports for owned child cases.
Admins can view across cases for demo/testing.

## UI Contract

The Progress Tracking / Reports views show:

- `Score Timeline`
- `Feature Trends Over Sessions`
- `Therapy Goal Progress`
- `Before/After Radar`
- `Printable / Exportable Progress Report`
- `Download Markdown`
- `Print / Save PDF`

## Recommended Checks

```bash
python -m pytest tests/test_clinical_workflow.py tests/test_therapist_clinician_app.py tests/test_therapist_report.py -q
node --check therapist-clinician-app/src/app.js
```
