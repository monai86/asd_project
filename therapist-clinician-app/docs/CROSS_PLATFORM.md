# Cross-Platform Clinical App

The therapist app remains a Vite SPA and is packaged for iOS through Capacitor. This keeps the web and iOS surfaces aligned with the same clinical decision-support, sample-data, consent, ownership, and signed-upload boundaries.

## PWA

- `vite-plugin-pwa` generates the web manifest and service worker.
- The service worker caches static app shell assets only.
- Clinical records, transcripts, audio files, reports, and API responses must not be cached offline in v1.
- The app manifest uses the same product identity as the clinician workspace and points to `app-icon.svg` for install surfaces.

## iOS

- Capacitor uses `dist/` as the native web bundle.
- The native iOS layer is a Native Clinical Shell: launch, safe-area, offline, and system-status presentation around the shared web workspace.
- The native shell may send platform and network status events to the web app, but it must not pass child case, session, transcript, report, or clinical media payloads across the bridge.
- Secure media upload still follows the backend Signed Upload Intent flow.
- Native/iOS media handling is a platform surface for choosing and uploading media, not a bypass around guardian consent or private storage rules.
- Camera, microphone, and photo-library permission strings must stay specific to consent-gated clinical media review.

## Safety Invariants

- Web and iOS must show the same non-diagnostic decision-support boundaries.
- Private media uploads must stay consent-gated in `secure_backend` and `supabase_storage` modes.
- Upload metadata must remain redacted and auditable.
- Offline support is limited to static shell availability until encrypted clinical offline storage is designed and reviewed.
- Native shell offline messaging must say that clinical records, uploads, and reports require network access.

## Commands

```bash
npm run build
npm run cap:sync
npm run cap:open:ios
```

## Verification

```bash
npm run test
npm run build
npm run cap:sync
npm audit --omit=dev
```

Native build verification requires a full Xcode installation:

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

If `xcodebuild` reports `/Library/Developer/CommandLineTools`, install/open Xcode and switch the developer directory before running iOS simulator builds.
