# Render Backend Staging Runbook

Date: 2026-07-01

Use this runbook to deploy the maintained FastAPI backend in `apps/api/` to
Render for the staging environment.

Canonical deployment references:

- [docs/PRODUCTION_DEPLOYMENT.md](/Users/porschecaa/lingualens/docs/PRODUCTION_DEPLOYMENT.md)
- [docs/STAGING_EXECUTION_RUNBOOK.md](/Users/porschecaa/lingualens/docs/STAGING_EXECUTION_RUNBOOK.md)
- [docs/STAGING_SUPABASE_ENV_WIRING_CHECKLIST.md](/Users/porschecaa/lingualens/docs/STAGING_SUPABASE_ENV_WIRING_CHECKLIST.md)

## Before You Start

- The backend service in this repository is `apps/api/`.
- Render should use `apps/api` as the root directory for this service.
- The backend should run in production-like staging mode:
  - `LINGUALENS_MOCK_MODE=false`
  - `LINGUALENS_AUTH_MODE=supabase`
  - `LINGUALENS_REPOSITORY_MODE=sql`
- Alembic migrations must run before the deployed app serves staging traffic.

## Required Render Resources

Create these three staging resources in the same Render region:

1. Render Postgres
2. Render Key Value
3. Render Web Service for `apps/api`

Using the same region minimizes latency and lets the web service use internal
connection URLs for Postgres and Key Value.

## Step 1. Create Render Postgres

In Render Dashboard:

1. Click `New`.
2. Click `Postgres`.
3. Set a clear name such as `lingualens-staging-db`.
4. Choose the same region you plan to use for the API service.
5. Choose an instance type.
6. Click `Create Database`.

After creation:

1. Open the database page.
2. Open the `Connect` menu.
3. Copy the internal connection URL.
4. Convert the scheme to `postgresql+psycopg://` for this app if Render gives
   you a plain `postgres://` or `postgresql://` URL.

Save it as:

```text
LINGUALENS_DATABASE_URL=postgresql+psycopg://...
```

## Step 2. Create Render Key Value

In Render Dashboard:

1. Click `New`.
2. Click `Key Value`.
3. Set a clear name such as `lingualens-staging-redis`.
4. Choose the same region as the API and Postgres.
5. Choose an instance type.
6. Click `Create Key Value`.

After creation:

1. Open the Key Value page.
2. Open the `Connect` menu.
3. Copy the internal URL.

Save it as:

```text
REDIS_URL=redis://...
```

## Step 3. Create The Render Web Service

In Render Dashboard:

1. Click `New`.
2. Click `Web Service`.
3. Connect the GitHub repository for this project.
4. Select the repository.
5. Configure these fields:

```text
Name: lingualens-api-staging
Language: Python 3
Root Directory: apps/api
Build Command: pip install -r requirements.txt
Pre-Deploy Command: PYTHONPATH=. alembic upgrade head
Start Command: PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Recommended:

- Enable auto deploy from your staging branch if you want every push to redeploy.
- Set the health check path to `/health` after the service is created.

## Step 4. Add Backend Environment Variables

Open the service:

1. Click `Environment`.
2. Click `Add from .env` for bulk paste, or add variables one by one.

Minimum staging backend env:

```text
LINGUALENS_MOCK_MODE=false
LINGUALENS_AUTH_MODE=supabase

LINGUALENS_SUPABASE_JWT_VERIFICATION_MODE=jwks_url
LINGUALENS_SUPABASE_JWT_JWKS_URL=https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1/.well-known/jwks.json
LINGUALENS_SUPABASE_JWT_JWKS_CACHE_TTL_SECONDS=300
LINGUALENS_SUPABASE_JWT_ISSUER=https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1
LINGUALENS_SUPABASE_JWT_AUDIENCE=authenticated
LINGUALENS_SUPABASE_REQUIRE_MFA=true
LINGUALENS_SUPABASE_REQUIRE_INVITATION=true

LINGUALENS_REPOSITORY_MODE=sql
LINGUALENS_DATABASE_URL=postgresql+psycopg://...
LINGUALENS_SQL_CREATE_SCHEMA=false

LINGUALENS_JOB_QUEUE_MODE=redis
REDIS_URL=redis://...

LINGUALENS_STORAGE_MODE=supabase_private

LINGUALENS_SECRET_STORE_PROVIDER=<doppler|infisical|vault|aws_secrets_manager|gcp_secret_manager|azure_key_vault>
LINGUALENS_CREDENTIAL_ROTATION_RUNBOOK=docs/SECRET_ROTATION_RUNBOOK.md

LINGUALENS_OBSERVABILITY_ENABLED=true
LINGUALENS_OBSERVABILITY_PROVIDER=<sentry|cloudwatch|otlp>
LINGUALENS_CRITICAL_ALERT_ROUTE=<real alert destination>

LINGUALENS_CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
LINGUALENS_CSRF_ORIGIN_GUARD_ENABLED=true
```

Notes:

- Replace the temporary localhost CORS origins with the real staging frontend
  URL as soon as the frontend is deployed.
- Do not use `localhost` database or Redis URLs.
- Do not leave `LINGUALENS_SQL_CREATE_SCHEMA=true` in staging.

## Step 5. Save And Deploy

After entering env vars:

1. Click `Save, rebuild, and deploy`.
2. Wait for the deploy logs to finish.

If the deploy succeeds, Render assigns an `onrender.com` URL to the service.

Record:

```text
staging api url = https://<your-render-service>.onrender.com/api/v1
```

## Step 6. Configure Health Check

In the web service:

1. Open `Settings`.
2. Scroll to `Health Checks`.
3. Click `Edit`.
4. Set:

```text
/health
```

5. Save changes.

## Step 7. Verify The Backend

Check these endpoints:

```text
https://<your-render-service>.onrender.com/health
https://<your-render-service>.onrender.com/api/v1/settings
```

Expected:

- `/health` returns HTTP `200`
- `/api/v1/settings` returns HTTP `200`
- `/api/v1/settings` shows:
  - `auth_mode: "supabase"`
  - `mock_mode: false`
  - `required_app_aal: "aal2"`

## Current Repository Notes

- `apps/api/requirements.txt` now includes `psycopg[binary]` and `redis`, which
  are required for Render Postgres and Render Key Value connections.
- The `supabase_private` storage adapter is still an external-configuration
  boundary in the current codebase. Backend boot and auth/settings verification
  can proceed, but upload/storage workflows still need the next integration step
  before full staging proof can close.

## What To Send Back After Backend Deploy

When the backend is live, send:

```text
backend host/provider = Render
database provider = Render Postgres
redis provider = Render Key Value
secret store provider = <your chosen provider>
staging api url = https://<your-render-service>.onrender.com/api/v1
```
