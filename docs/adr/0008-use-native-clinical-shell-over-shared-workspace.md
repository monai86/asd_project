# Use Native Clinical Shell over shared workspace

The iOS app will use a Native Clinical Shell around the existing Capacitor web workspace rather than rewriting clinical workflows in SwiftUI. This preserves one source of truth for child cases, transcript review, reports, consent, and non-diagnostic safety boundaries while still allowing iOS-native launch, safe-area, offline, and system-status behavior.

## Considered Options

- Full SwiftUI clinical workflow rewrite.
- Native dashboard plus web-only deep workflows.
- Native Clinical Shell over the shared clinical workspace.

## Consequences

Native code may report shell and network state to the web app, but it must not pass child case, session, transcript, report, or clinical media payloads across the shell bridge. Clinical offline storage remains out of scope until an encrypted offline-storage decision is made.
