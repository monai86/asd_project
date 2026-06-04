# Use direct Supabase RLS with signed media intents

We will let the therapist app read and write anonymized clinical workflow records through Supabase Auth and Row Level Security for the Supabase pilot, while keeping clinical media uploads behind a signed upload intent. Direct RLS keeps the pilot app simpler and closer to the production data platform, but media remains consent-gated because storage keys, retention metadata, and audit boundaries are easy to weaken if the browser uploads directly to arbitrary private paths.
