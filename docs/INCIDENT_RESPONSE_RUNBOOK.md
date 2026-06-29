# Incident Response Runbook

This runbook defines production-launch stop criteria and first-response actions
for lingualens. It applies to pilot, staging with restored production
data, and production environments. It does not make the current prototype
clinical-ready.

## Stop rollout criteria

Stop rollout immediately when any of these events is suspected:

- cross-tenant exposure: any user, worker, operator, export, log, or report can
  see another organization's clinical data;
- consent bypass: upload, ASR, feature extraction, report generation, export, or
  access continues after consent withdrawal or without granted consent;
- audit loss: audit events, transcript attestations, report sign-offs, signed
  snapshots, export hashes, or incident evidence are missing, mutable, or
  corrupted;
- fabricated ASR output: provider failure, retry, timeout, mock fallback, or
  region fallback creates transcript text that did not come from approved ASR
  output or therapist review.

## First response

1. Stop rollout and pause onboarding of new organizations.
2. Disable affected deploys, workers, queues, provider credentials, or storage
   access paths without deleting evidence.
3. Preserve audit logs, sign-off evidence, job attempts, deployment metadata,
   and relevant operational logs.
4. Rotate exposed credentials through the managed secret store when credential
   exposure is suspected.
5. Keep notifications generic: no child identifiers, transcript text, audio
   content, storage keys, or report excerpts in incident tickets, emails, or chat.
6. Assign an incident commander, clinical/privacy owner, security owner, and
   platform operator.
7. Record the incident timeline, affected organization IDs, data classes, region,
   detection source, containment action, and rollback decision.

## Clinical and privacy safeguards

- Do not delete audit/sign-off evidence automatically, even when privacy deletion
  workflows are active.
- Do not resume ASR or AI drafting after provider errors until fabricated output
  risk is reviewed.
- Do not grant platform operators clinical content access unless audited
  break-glass access is explicitly approved and time-limited.
- Do not expand country or organization rollout while root cause is unknown.

## Recovery and rollback

1. Patch or disable the failing path.
2. Run relevant tests and smoke checks, including tenant isolation, consent gates,
   audit preservation, and migration smoke where database state changed.
3. If data integrity is uncertain, follow `docs/BACKUP_RESTORE_RUNBOOK.md` and
   restore into staging first.
4. Validate that no cross-tenant data, consent-bypassed job, audit loss, or
   fabricated ASR output remains.
5. Re-enable traffic gradually, starting with internal or synthetic-data users.
6. Record final impact, evidence reviewed, corrective actions, owner sign-off,
   and follow-up tasks.

## Drill cadence

Run incident-response drills before the first design-partner clinic, after any
major auth/storage/ASR/report change, and at least once per quarter during pilot.
Each drill must include one stop rollout scenario and prove that the team can
preserve audit evidence without copying clinical content into operational tools.
