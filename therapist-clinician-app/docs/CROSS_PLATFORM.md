# Cross-Platform Clinical App

The therapist app remains a Vite SPA and is packaged for iOS through Capacitor. This keeps the web and iOS surfaces aligned with the same clinical decision-support, sample-data, consent, ownership, and signed-upload boundaries.

## PWA

- `vite-plugin-pwa` generates the web manifest and service worker.
- The service worker caches static app shell assets only.
- Clinical records, transcripts, audio files, reports, and API responses must not be cached offline in v1.

## iOS

- Capacitor uses `dist/` as the native web bundle.
- Secure media upload still follows the backend Signed Upload Intent flow.
- Native/iOS media handling is a platform surface for choosing and uploading media, not a bypass around guardian consent or private storage rules.

## Commands

```bash
npm run build
npm run cap:sync
npm run cap:open:ios
```
