# Persist immutable ML review results

Therapist-facing ML review support will be stored as backend-authoritative,
immutable provider output linked to the exact transcript, feature set, schema,
provider configuration, and input hash. Therapist acknowledgement or dismissal
is stored separately as audited review state; browser-generated results and
automatic report inclusion are excluded so provenance remains reproducible,
consent withdrawal can remove derived child data, and research classifiers
cannot silently become clinical workflow outputs.
