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

## Monitoring

Track auth failures, 403/404 access-denial spikes, upload-intent failures,
processing-job failures, storage errors, report export volume, and privacy
operation queue age.

## Log Retention

Use `LOG_RETENTION_DAYS` for application logs and a clinic-approved retention
period for audit logs. Privacy deletion requests must be reviewed against
retention obligations before any destructive action.

## Incident Response

1. Disable affected API credentials, storage keys, or auth provider clients.
2. Pause new uploads and backend processing jobs.
3. Preserve audit logs and relevant operational logs.
4. Identify affected `case_id`, `session_id`, and `file_object_id` records.
5. Notify the responsible project owner and clinic/privacy contact.
6. Patch, redeploy, and record the incident outcome before re-enabling uploads.
