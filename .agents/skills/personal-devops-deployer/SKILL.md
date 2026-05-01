---
name: personal-devops-deployer
description: Prepare, deploy, operate, monitor, and troubleshoot applications across Vercel, Netlify, Cloudflare, Render, Docker, CI/CD, servers, databases, environment variables, domains, SSL, logs, migrations, and production release workflows. Use when shipping an app, fixing deployment failures, configuring infrastructure, creating release checklists, or making local apps production-ready.
---

# Personal DevOps Deployer

## Purpose

Ship applications safely and make production understandable. Prefer minimal reliable deployment over overbuilt infrastructure. Verify build, environment, runtime, database, and rollback before calling a release done.

## Workflow

1. Inspect app stack, package manager, build/start commands, runtime version, ports, env vars, database, and deploy target.
2. Identify deployment model: static site, server-rendered app, API server, worker, container, background job, cron, or database-backed app.
3. Prepare config: build command, output directory, start command, env vars, secrets, migrations, domains, and runtime limits.
4. Run local verification: install, lint/typecheck/tests where available, build, and smoke test.
5. Deploy or produce exact deploy steps depending on available credentials.
6. Verify production: health route, logs, key user flow, database connectivity, assets, redirects, and error pages.
7. Document rollback and follow-up monitoring.

## Platform Guidance

For Vercel/Netlify:

- Confirm framework detection, build command, output directory, serverless limits, redirects, and env vars.
- Check preview vs production environment differences.

For Cloudflare:

- Confirm Workers/Pages/D1/KV/R2 bindings, compatibility date, secrets, routes, and edge runtime limits.

For Docker:

- Use small reproducible images.
- Keep secrets out of images.
- Add health checks when possible.
- Separate build-time and runtime env vars.

For databases:

- Run migrations intentionally.
- Back up important data before destructive changes.
- Confirm connection pooling/serverless compatibility.

## Release Checklist

- Build passes.
- Required env vars are known.
- Database migrations are planned.
- Public routes and protected routes behave correctly.
- Logs are accessible.
- Rollback path is clear.
- Domain/SSL is configured if needed.

## Failure Triage

When deploy fails:

1. Read the first real error, not the last cascade.
2. Compare local vs deployment environment.
3. Check Node/runtime versions, missing env vars, path case sensitivity, package manager lockfiles, and build output.
4. Fix one cause at a time and rerun.

## Quality Checks

Before final delivery, include:

- What was deployed or configured.
- Verification performed.
- Remaining env vars or credentials the user must provide.
- Production URL or next deploy command when available.
