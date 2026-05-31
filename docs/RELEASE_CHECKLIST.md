# Release Checklist

Use this checklist before a therapist-clinician pilot release.

## Preflight

- `npm test` passes in `therapist-clinician-app/`.
- `npm run test:e2e:smoke` passes in `therapist-clinician-app/`.
- `npm run build` passes in `therapist-clinician-app/`.
- `pytest tests -q` passes at the repository root.
- Mock/sample banner is visible in non-production modes.
- Therapist and clinician users cannot view each other's cases.
- Therapist and clinician users cannot read audit logs.
- Privacy export, consent withdrawal, and deletion requests create audit events.

## Production Gate

- `AUTH_MODE`, `DATA_MODE`, `PROCESSING_MODE`, and `FILE_STORAGE_MODE` are set to production values.
- HTTPS is enforced.
- Database backups and restore test are complete.
- Private storage bucket encryption and retention rules are configured.
- Monitoring alerts are configured for auth, storage, processing, API errors, and privacy queue age.
- Incident contact and rollback owner are named.

## Rollback

1. Revert the Pages/API deployment to the previous known-good artifact.
2. Pause backend processing workers if storage or transcript generation is affected.
3. Keep database migrations reversible or apply a documented forward fix.
4. Preserve audit logs and privacy operation records.
5. Confirm login, case ownership, upload blocking, and report export behavior after rollback.
