# Release Checklist

Use this checklist before a therapist-clinician pilot release.

## Preflight

- `npm test` passes in `therapist-clinician-app/`.
- `npm run test:e2e:smoke` passes in `therapist-clinician-app/`.
- `npm run build` passes in `therapist-clinician-app/`.
- PWA output includes `manifest.webmanifest` and `sw.js`.
- Service worker config caches static app-shell assets only; no clinical records, audio, transcripts, reports, or API responses are cached offline.
- `npm run cap:sync` passes in `therapist-clinician-app/` after every PWA or native shell change.
- iOS uses `NativeClinicalShellViewController` around the shared Capacitor workspace, not a separate clinical workflow.
- Native shell bridge events contain platform, network, and safe-area status only; no child case, session, transcript, report, or media payloads cross the shell bridge.
- Offline messaging states that clinical records, uploads, and reports require network access.
- iOS permission strings in `therapist-clinician-app/ios/App/App/Info.plist` explain camera, microphone, and photo-library access in consent/private-storage terms.
- iOS release verification uses a full Xcode developer directory, not `/Library/Developer/CommandLineTools`.
- Supabase pilot mode is tested with `VITE_DATA_MODE=supabase`, `VITE_AUTH_MODE=supabase`, `VITE_FILE_STORAGE_MODE=supabase_storage`, and anonymized-only child codes.
- Supabase RLS policies are applied and tested for owner isolation, admin visibility, anonymous denial, and no direct browser access to `audit_logs`.
- Supabase Storage uses the private `clinical-media` bucket and owner-scoped `private/{owner_user_id}/...` object paths.
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
- Signed upload intent expiry, object redaction, and audit event retention are confirmed for native and web upload paths.
- Admin bootstrap uses a service role or trusted backend path; the browser must not be able to self-assign the `admin` role.
- Monitoring alerts are configured for auth, storage, processing, API errors, and privacy queue age.
- Incident contact and rollback owner are named.

## Rollback

1. Revert the Pages/API deployment to the previous known-good artifact.
2. Pause backend processing workers if storage or transcript generation is affected.
3. Keep database migrations reversible or apply a documented forward fix.
4. Preserve audit logs and privacy operation records.
5. Confirm login, case ownership, upload blocking, and report export behavior after rollback.
