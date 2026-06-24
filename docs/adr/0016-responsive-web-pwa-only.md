# Responsive web and PWA only for Therapist App v2

## Status

Accepted

## Context

The repository previously explored Vite, Capacitor, and native-shell paths for a
therapist application. The maintained product surface has since converged on the
Next.js Therapist App v2 in `apps/therapist-app-v2/`, backed by the FastAPI
boundary in `apps/api/`.

Production work now needs focus on tenant isolation, authentication, private
audio processing, report governance, operations, deployment, and controlled
rollout. Maintaining a native shell in parallel would split test coverage and
increase clinical safety review scope.

## Decision

Therapist App v2 will be delivered as responsive web/PWA only.

The canonical frontend remains:

- `apps/therapist-app-v2/`

The canonical backend remains:

- `apps/api/`

Do not recreate the removed `therapist-clinician-app/` Vite/Capacitor app. Do
not add a new native shell or product frontend unless a future ADR explicitly
reopens the platform decision with security, clinical safety, deployment, and
maintenance evidence.

## Consequences

- Frontend production work belongs in the Next.js app.
- Mobile support is achieved through responsive layouts and PWA capabilities.
- Clinical workflow behavior, auth state, tenant context, upload intent, report
  finalization, and privacy operations must stay consistent across desktop and
  mobile browsers.
- Legacy Vite/Capacitor documentation is historical context only where it
  conflicts with this ADR.
