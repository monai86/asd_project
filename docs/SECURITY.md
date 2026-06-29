# Security Operations

This project is a research/demo prototype. Production clinical use requires a
separate security review before any real child data or audio is entered.

## Required Controls

- Enforce provider-backed authentication and role claims. Disable mock accounts.
- Filter every clinical query by `owner_user_id` unless the verified user role is `admin`.
- Keep audio/video objects in private encrypted storage.
- Return only short-lived signed URLs to the browser; never expose permanent storage keys.
- Require granted consent before secure upload or backend audio processing.
- Keep audit-log reads admin-only through a backend/service-role path.
- Log workflow events without transcript text, audio bytes, direct identifiers, or storage keys.
- Log request paths as route templates or sanitized paths only. Disable
  access-style dependency logs that emit raw URLs at INFO level.
- Configure CORS allowed origins explicitly per environment. Production must
  reject wildcard or empty origin lists, and unsafe HTTP methods must reject
  untrusted browser origins with a generic 403 response.
- Store production database, Redis, storage, provider, and signing credentials in
  a managed secret store. Production startup must fail closed when demo/default
  database or Redis URLs, local repositories, local storage, or in-memory queues
  are configured, when the secret-store provider is not approved, or when no
  credential rotation runbook is configured.
- Enable managed database backups and point-in-time recovery before real data.
  Restore drills must meet the RPO/RTO in `docs/BACKUP_RESTORE_RUNBOOK.md` and
  preserve audit/sign-off evidence.
- Route case export, consent withdrawal, and deletion-review requests through
  privacy operations. Deletion-review records must keep retention days,
  eligible-for-deletion timestamps, legal-hold state, and retained-evidence
  summaries. Legal hold blocks completion, and audit/sign-off evidence must not
  be automatically deleted.
- Stop rollout immediately for cross-tenant exposure, consent bypass, audit
  loss, or fabricated ASR output. Follow `docs/INCIDENT_RESPONSE_RUNBOOK.md` and
  keep child identifiers, transcript text, audio content, storage keys, and
  report excerpts out of incident tools.
- Keep in-app notifications and email generic. Use the API notification safety
  validator before sending messages, and never include child identifiers,
  transcript text, audio content, storage keys, raw filenames, report excerpts,
  or clinical content.
- Audit events must include actor, action, target, outcome, timestamp, and
  correlation ID. Use the API audit safety validator before persisting events,
  and keep clinical content out of audit messages.
- Production observability must use an approved provider such as Sentry,
  CloudWatch, or OTLP and a configured critical alert route. Telemetry tags,
  measurements, and details must stay operational-only and pass the API
  observability safety validator before export.
- Run repository consistency and secret scanning before test/deploy jobs.
- Run dependency audits for Python and the maintained Therapist frontend before
  production release. Current CI records dependency audit failures as report-only
  while known Next.js advisories are being resolved; public production must treat
  unresolved critical/high findings as blocking.
- Follow `docs/SECRET_ROTATION_RUNBOOK.md` for credential rotation and drills.
  Never copy secret values or clinical content into tickets, logs, chat, or
  repository files.

## Local Security Checks

```bash
python scripts/security_scan.py
pip-audit -r requirements.txt -r apps/api/requirements.txt
cd apps/lingualens-app && npm audit --audit-level=high
```

The secret scanner reports only file path, line number, and finding category. It
does not print matched secret values.

## Monitoring

Track auth failures, 403/404 access-denial spikes, upload-intent failures,
processing-job failures, storage errors, report export volume, and privacy
operation queue age. Production startup fails closed when observability is
disabled, the provider is not approved, or no critical alert route is configured.
Do not send child identifiers, transcript text, audio content, storage keys, raw
filenames, report excerpts, or clinical content to error/metrics providers.

## Log Retention

Use `LOG_RETENTION_DAYS` for application logs and a clinic-approved retention
period for audit logs. Privacy deletion requests must be reviewed against
retention obligations before any destructive action. A completed deletion review
records evidence retained for audit and signed reports; it does not erase those
records automatically.

## Incident Response

1. Disable affected API credentials, storage keys, or auth provider clients.
2. Pause new uploads and backend processing jobs.
3. Preserve audit logs and relevant operational logs.
4. Identify affected `case_id`, `session_id`, and `file_object_id` records.
5. Notify the responsible project owner and clinic/privacy contact.
6. Patch, redeploy, and record the incident outcome before re-enabling uploads.

See `docs/INCIDENT_RESPONSE_RUNBOOK.md` for stop-rollout criteria and drill
requirements.
