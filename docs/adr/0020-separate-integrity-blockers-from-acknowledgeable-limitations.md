# Separate integrity blockers from therapist-acknowledgeable limitations

LinguaLens v1.7.0 removes the normal workflow's generic QA-failure override:
typed integrity failures must be remediated, while structurally safe
limitations may be acknowledged only through version-bound audited records
that remain visible downstream. Explicit escalation rules promote a limitation
to a blocker when reliable source representation is no longer possible, and
debug overrides remain isolated test/development artifacts that can never
become attested, report-eligible, signable, or clinically exportable.
