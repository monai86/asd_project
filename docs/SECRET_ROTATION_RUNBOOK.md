# Secret Rotation Runbook

This runbook is for production readiness only. Do not paste real secrets,
tokens, child identifiers, audio object keys, transcript text, or clinical
content into tickets, logs, chat, or this repository.

## Production gate

Production startup must fail closed unless:

- secrets are supplied by a managed secret store such as AWS Secrets Manager,
  Azure Key Vault, Google Secret Manager, Doppler, Infisical, or Vault;
- `THERAPIST_APP_V2_SECRET_STORE_PROVIDER` names the approved provider;
- `THERAPIST_APP_V2_CREDENTIAL_ROTATION_RUNBOOK` points to this runbook or an
  approved operator runbook;
- database, Redis, storage, auth, ASR, AI provider, signing, and observability
  credentials are not committed or read from local demo defaults.

## Rotation cadence

- Rotate service credentials at least every 90 days.
- Rotate immediately after staff offboarding, suspected exposure, provider
  incident, failed secret scan, or environment compromise.
- Run one staging drill before enabling a new production region or clinic.

## Standard rotation flow

1. Open an operations ticket without secret values or clinical content.
2. Create the replacement credential in the managed secret store.
3. Grant least-privilege access to the service identity only.
4. Deploy staging with both old and new credentials if the provider supports a
   dual-key window.
5. Run smoke tests for auth, database, Redis/job queue, storage signed URLs,
   ASR, report signing/export, observability, and audit writes.
6. Promote the new credential to production through the deployment platform.
7. Re-run production smoke checks.
8. Revoke the old credential after the dual-key window.
9. Record credential name, provider, rotation timestamp, operator, verification
   result, and rollback window in the operations ticket.

## Rollback

If smoke tests fail, restore the previous credential version from the managed
secret store, redeploy the affected service, and preserve audit and operational
logs. Do not copy clinical content into the incident record.

## Evidence to retain

- operation ticket ID;
- managed secret store credential name or alias, not the secret value;
- service/environment affected;
- rotation timestamp and operator;
- verification commands and result;
- old credential revocation timestamp.
