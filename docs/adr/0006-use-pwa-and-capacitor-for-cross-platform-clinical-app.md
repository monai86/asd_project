# Use PWA and Capacitor for the cross-platform clinical app

We will keep the therapist/clinician application as the shared Vite web app and add PWA installability plus a Capacitor iOS shell instead of rewriting the product in React Native or SwiftUI. This preserves the existing clinical workflow, safety wording, Supabase-first backend boundary, and test coverage while still allowing iOS-specific secure media upload behavior where the web platform needs native help.
