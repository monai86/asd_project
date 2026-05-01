---
name: personal-code-quality
description: Review, debug, refactor, test, document, or harden code across frontend, backend, APIs, databases, scripts, and fullstack projects. Use for code review, bug triage, test generation, architecture cleanup, performance fixes, security review, API documentation, database schema review, CI issues, and improving maintainability.
---

# Personal Code Quality

## Purpose

Improve software with senior-engineer discipline: understand the existing system first, make focused changes, prove behavior with tests or runtime checks, and explain the risk clearly.

## Workflow

1. Inspect the repo structure, package manager, framework, tests, lint/typecheck commands, and recent changes.
2. Reproduce or understand the issue before editing when possible.
3. Find the smallest maintainable change that fits existing patterns.
4. Add or update tests when behavior changes or risk is nontrivial.
5. Run relevant verification: typecheck, lint, unit tests, integration tests, browser checks, or build.
6. Review the diff for unintended churn, security issues, and broken contracts.
7. Final response should summarize changes and verification results.

## Code Review Mode

When asked for a review, lead with findings ordered by severity. Include file and line references. Prioritize:

- Incorrect behavior
- Security vulnerabilities
- Data loss or migration risk
- Race conditions and concurrency bugs
- Broken auth/authorization
- Missing validation
- Performance regressions
- Missing or weak tests

Avoid spending review space on style unless it creates real risk.

## Refactor Rules

- Preserve public behavior unless the task explicitly changes it.
- Keep refactors scoped.
- Prefer local clarity over broad abstractions.
- Do not introduce a new framework or dependency without a strong reason.
- Update names and types only where they reduce confusion.

## Testing Rules

- Test observable behavior, not implementation details.
- Add regression tests for bugs.
- Cover failure paths for auth, payments, destructive actions, and data writes.
- For frontend, test user-visible flows and accessibility basics.
- For backend, test validation, permissions, and persistence.

## Security Rules

Check trust boundaries:

- User input
- Auth/session
- Authorization
- Redirects
- Database queries
- File uploads
- Secrets/env vars
- Third-party webhooks

Do not log secrets, tokens, passwords, payment data, or sensitive personal data.
