# Backup and Restore Runbook

This runbook covers lingualens production-readiness expectations for the
active FastAPI API and Postgres/Supabase database. It is a launch gate, not a
claim that the current local prototype is production-ready.

## Recovery objectives

- RPO: 15 minutes
- RTO: 4 hours

Production deployments must use managed Postgres backups with point-in-time
recovery enabled in the same approved deployment region as the clinical data.
Backup configuration, restore permissions, and credential rotation must live in
the deployment platform or managed secret store, not in committed files.

## Pre-deployment migration smoke

Run the migration smoke check before promoting API code:

```bash
PYTHONPATH=apps/api:src python scripts/check_api_migrations.py
```

The check creates a fresh temporary database, applies Alembic migrations to
`head`, verifies the stored Alembic revision, and confirms required clinical and
audit tables exist. It does not use real clinical data.

## Restore drill

Run a restore drill before any pilot using real data and repeat it at least once
per quarter:

1. Start from a managed backup or point-in-time restore target.
2. Restore into an isolated staging project in the same approved region.
3. Rotate database, Redis, storage, and provider credentials before application
   access.
4. Run Alembic migration compatibility checks against the restored database.
5. Verify that cases, sessions, transcripts, reports, signed snapshots, and
   audit evidence are readable by authorized test users only.
6. Confirm privacy controls still hold: consent-withdrawn records stay blocked,
   audit/sign-off evidence is preserved, and no transcript/audio content appears
   in logs.
7. Record restore start/end timestamps, achieved RPO/RTO, operator, backup
   source, verification evidence, and any corrective actions.

## Failure handling

- If the restore misses the RPO: 15 minutes target, pause rollout and review
  backup frequency, replication lag, and provider retention settings.
- If recovery exceeds the RTO: 4 hours target, pause rollout and review restore
  automation, credential rotation, migration compatibility, and operator access.
- If audit evidence is missing or corrupted, do not resume production traffic
  until the privacy/security owner has reviewed the incident.
- If any cross-tenant data is visible after restore, treat it as a critical
  incident and stop rollout.

## Evidence to keep

Keep restore drill records outside the clinical database in the incident or
operations workspace:

- date/time and deployment region;
- backup or PITR source;
- migration smoke output;
- RPO/RTO result;
- screenshots or logs without child identifiers, transcript text, audio keys, or
  clinical content;
- sign-off from the platform/security owner before production promotion.
